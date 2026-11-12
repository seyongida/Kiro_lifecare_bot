"""
LG U+ Life Care 스크래퍼 단위 테스트 + 속성 기반 테스트
- 단위 테스트: pytest
- 속성 기반 테스트: Hypothesis
- 실제 사이트 접속이 필요한 로그인·스크래핑은 가짜(Fake) 객체로 흐름만 검증
"""
import asyncio
import re
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

import main as m

TARGET_URL = "https://example.com/products"


def run(coro):
    return asyncio.run(coro)


def fmt(products, total="0", **kwargs):
    """외부 조회(다나와)는 기본적으로 비화이트로 모킹한 format_products 호출"""
    with patch.object(m, "is_white_monitor", return_value=False):
        return run(m.format_products(products, total, TARGET_URL, **kwargs))


def body_lines(result):
    body = result.split("\n\n", 1)[1]
    return [line for line in body.splitlines() if line.strip()]


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

class TestConfig:
    ENV = {
        "LG_ID": "id", "LG_PW": "pw", "TARGET_URL": TARGET_URL,
        "TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat",
    }

    def _set(self, monkeypatch, **overrides):
        for k, v in {**self.ENV, **overrides}.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)

    def test_loads_all_values(self, monkeypatch):
        self._set(monkeypatch)
        monkeypatch.delenv("SSL_VERIFY", raising=False)
        cfg = m.Config.from_env()
        assert cfg.lg_id == "id" and cfg.target_url == TARGET_URL
        assert cfg.ssl_verify is True

    def test_missing_values_are_listed(self, monkeypatch):
        self._set(monkeypatch, LG_PW=None, TELEGRAM_CHAT_ID="  ")
        with pytest.raises(m.ConfigError, match="LG_PW, TELEGRAM_CHAT_ID"):
            m.Config.from_env()

    @pytest.mark.parametrize("raw, expected", [
        ("false", False), ("0", False), ("no", False), ("OFF", False),
        ("true", True), ("1", True), ("", True),
    ])
    def test_ssl_verify_flag(self, monkeypatch, raw, expected):
        self._set(monkeypatch, SSL_VERIFY=raw)
        assert m.Config.from_env().ssl_verify is expected


# ──────────────────────────────────────────────
# format_products
# ──────────────────────────────────────────────

class TestFormatProducts:
    def test_empty_header(self):
        result = fmt([], "0")
        lines = result.splitlines()
        assert lines[0] == "총 0개 중 0개 수집 (품절 제외)"
        assert lines[1] == TARGET_URL
        assert result.split("\n\n", 1)[1] == ""

    def test_unmatched_order_preserved(self):
        products = [{"name": f"패턴없는상품{c}", "price": "100,000"} for c in "ABC"]
        names = [line.split(" / ")[0] for line in body_lines(fmt(products, "3"))]
        assert names == ["패턴없는상품A", "패턴없는상품B", "패턴없는상품C"]

    def test_sorted_by_category_then_price_and_unmatched_last(self):
        products = [
            {"name": "[A][모니터]M2", "price": "300,000"},
            {"name": "기타상품", "price": "1,000"},
            {"name": "[A][TV]T1", "price": "1,200,000"},
            {"name": "[B][모니터]M1", "price": "90,000"},
            {"name": "[A][TV]T2", "price": "800,000"},
        ]
        assert body_lines(fmt(products, "5")) == [
            "[A][TV]T2 / 800,000",
            "[A][TV]T1 / 1,200,000",
            "[B][모니터]M1 / 90,000",
            "[A][모니터]M2 / 300,000",
            "기타상품 / 1,000",
        ]

    def test_non_numeric_price_does_not_crash_and_sorts_last(self):
        """과거엔 int('가격문의')에서 ValueError로 전체 실행이 실패했음"""
        products = [
            {"name": "[A][TV]문의상품", "price": "가격문의"},
            {"name": "[A][TV]T1", "price": "500,000원"},
        ]
        assert body_lines(fmt(products, "2")) == [
            "[A][TV]T1 / 500,000원",
            "[A][TV]문의상품 / 가격문의",
        ]

    def test_white_monitor_tagged_and_cached_per_model(self):
        products = [
            {"name": "[A][등급모니터]27SR75U.AKRG", "price": "300,000"},
            {"name": "[B][등급모니터]27SR75U.AKRG", "price": "250,000"},
            {"name": "[A][등급모니터]27BR400.AKRG", "price": "200,000"},
        ]
        with patch.object(m, "is_white_monitor", side_effect=lambda name, verify: name.startswith("27SR75U")) as checker:
            result = run(m.format_products(products, "3", TARGET_URL, ssl_verify=False))
        assert body_lines(result) == [
            "[A][등급모니터]27BR400.AKRG / 200,000",
            "[B][등급모니터]27SR75U.AKRG(W) / 250,000",
            "[A][등급모니터]27SR75U.AKRG(W) / 300,000",
        ]
        # 같은 모델은 한 번만 조회, ssl_verify 설정 전달
        assert checker.call_count == 2
        assert all(call.args[1] is False for call in checker.call_args_list)

    def test_projector_ust_tagged_and_cached_per_slug(self):
        products = [
            {"name": "[A][프로젝터]PU615U.BKR", "price": "1,000,000"},
            {"name": "[B][프로젝터]PU615U.BKR", "price": "900,000"},
            {"name": "[A][프로젝터]BF60RG", "price": "500,000"},
        ]
        fake_check = AsyncMock(side_effect=lambda name, page: name.startswith("PU615U"))
        with patch.object(m, "check_projector_ust", fake_check):
            result = fmt(products, "3", ust_page=object())
        assert body_lines(result) == [
            "[A][프로젝터]BF60RG / 500,000",
            "[B][프로젝터]PU615U.BKR (UST) / 900,000",
            "[A][프로젝터]PU615U.BKR (UST) / 1,000,000",
        ]
        assert fake_check.await_count == 2

    def test_projector_check_skipped_without_page(self):
        fake_check = AsyncMock(return_value=True)
        with patch.object(m, "check_projector_ust", fake_check):
            fmt([{"name": "[A][프로젝터]PU615U", "price": "1"}], "1")
        fake_check.assert_not_awaited()

    @given(
        st.lists(
            st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_categories=("Cs",))),
                "price": st.from_regex(r"\d{1,3}(,\d{3})*", fullmatch=True),
            }),
            max_size=10,
        ),
        st.from_regex(r"\d+", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_header_format_property(self, products, total):
        lines = fmt(products, total).splitlines()
        assert lines[0] == f"총 {total}개 중 {len(products)}개 수집 (품절 제외)"
        assert lines[1] == TARGET_URL

    @given(
        st.lists(
            st.fixed_dictionaries({
                "name": st.from_regex(r"\[[A-Z]+\]\[[가-힣]+\][A-Z0-9]{1,10}", fullmatch=True),
                "price": st.from_regex(r"\d{1,3}(,\d{3})*", fullmatch=True),
            }),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_sorted_property(self, products):
        pat = re.compile(r"\[([^\]]+)\]\[([^\]]+)\](.+?) / (\S+)")
        parsed = [pat.match(line) for line in body_lines(fmt(products, str(len(products))))]
        keys = [(p.group(2), m.parse_price(p.group(4))) for p in parsed]
        assert keys == sorted(keys)
        assert len(parsed) == len(products)

    _no_pattern = st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(blacklist_categories=("Cs", "Cc", "Zl", "Zp"), blacklist_characters="[]"),
    )

    @given(st.lists(_no_pattern, min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_fallback_order_property(self, names):
        products = [{"name": n, "price": "100,000"} for n in names]
        result_names = [line.rsplit(" / ", 1)[0] for line in body_lines(fmt(products, str(len(products))))]
        assert result_names == names


class TestParsePrice:
    @pytest.mark.parametrize("raw, expected", [
        ("1,234,000", 1234000), ("500,000원", 500000), ("0", 0),
    ])
    def test_numbers(self, raw, expected):
        assert m.parse_price(raw) == expected

    def test_no_digits_is_infinite(self):
        assert m.parse_price("가격문의") == float("inf")


# ──────────────────────────────────────────────
# 메시지 분할
# ──────────────────────────────────────────────

class TestMessageChunking:
    @given(st.text(min_size=0, max_size=20000))
    @settings(max_examples=100)
    def test_chunk_roundtrip(self, message):
        chunks = m.chunk_text(message, 4096)
        assert all(len(c) <= 4096 for c in chunks)
        assert "".join(chunks) == message

    def test_chunk_splits_on_line_boundary(self):
        lines = [f"[A][TV]모델{i:04d} / 1,000,000" for i in range(600)]
        message = "\n".join(lines)
        chunks = m.chunk_text(message, 4096)
        assert len(chunks) > 1
        # 마지막 조각을 제외한 모든 조각이 줄 끝에서 끝나야 상품 줄이 쪼개지지 않음
        assert all(c.endswith("\n") for c in chunks[:-1])
        assert "".join(chunks) == message

    def test_chunk_hard_splits_overlong_line(self):
        chunks = m.chunk_text("가" * 9000, 4096)
        assert [len(c) for c in chunks] == [4096, 4096, 808]

    @given(st.text(min_size=1, max_size=20000))
    @settings(max_examples=100)
    def test_telegram_messages_within_limit(self, message):
        assert all(len(t) <= 4096 for t in m.build_telegram_messages(message, limit=4096))

    def test_no_split_returns_original(self):
        assert m.build_telegram_messages("짧은 메시지") == ["짧은 메시지"]

    def test_split_has_index_on_every_message(self):
        texts = m.build_telegram_messages("가" * 9000, limit=4096)
        total = len(texts)
        assert total > 1
        for i, text in enumerate(texts, start=1):
            assert text.startswith(f"[{i}/{total}]\n")

    def test_split_messages_reconstruct_original_body(self):
        message = "나" * 9000
        texts = m.build_telegram_messages(message, limit=4096)
        assert "".join(t.split("\n", 1)[1] for t in texts) == message

    def test_split_repeats_product_count_header(self):
        header = f"총 100개 중 80개 수집 (품절 제외)\n{TARGET_URL}"
        body = "\n".join(f"상품{i} / 10,000원" for i in range(2000))
        texts = m.build_telegram_messages(f"{header}\n\n{body}", limit=4096)
        total = len(texts)
        assert total > 1
        for i, text in enumerate(texts, start=1):
            assert text.startswith(f"[{i}/{total}]\n{header}\n\n")
            assert len(text) <= 4096
        # 헤더 제거 후 본문을 이어 붙이면 원본과 동일
        assert "".join(t.split("\n\n", 1)[1] for t in texts) == body

    def test_pathological_header_does_not_exceed_limit(self):
        texts = m.build_telegram_messages(("x" * 5000) + "\n\n" + ("y" * 5000), limit=4096)
        assert all(len(t) <= 4096 for t in texts)


# ──────────────────────────────────────────────
# 기타 헬퍼
# ──────────────────────────────────────────────

class TestHelpers:
    @given(st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2999, 12, 31)))
    @settings(max_examples=50)
    def test_screenshot_filename_pattern(self, dt):
        assert re.fullmatch(r"capture_\d{8}_\d{6}\.png", m.screenshot_filename("capture", dt))
        assert re.fullmatch(r"error_\d{8}_\d{6}\.png", m.screenshot_filename("error", dt))

    @pytest.mark.parametrize("raw, expected", [
        ("27SR75U.AKRG", "27SR75U"), ("27SR75U", "27SR75U"), ("PU615U.BKR", "PU615U"),
    ])
    def test_strip_kr_suffix(self, raw, expected):
        assert m.strip_kr_suffix(raw) == expected

    def test_projector_slug(self):
        assert m.projector_slug("PU615U.BKR") == "pu615u"

    def test_error_alert_uses_first_line_and_truncates(self):
        err = TimeoutError("Locator.click: Timeout 30000ms exceeded.\nCall log:\n...")
        alert = m.format_error_alert(err, "크롤링(3회 시도)")
        assert "크롤링(3회 시도) 실패" in alert
        assert "TimeoutError: Locator.click: Timeout 30000ms exceeded." in alert
        assert "Call log" not in alert
        assert len(m.format_error_alert(RuntimeError("x" * 5000), "s")) < 700


# ──────────────────────────────────────────────
# 텔레그램 재시도
# ──────────────────────────────────────────────

class TestWithRetry:
    def test_retries_network_error_then_succeeds(self):
        from telegram.error import NetworkError

        calls = []
        sleeps = []

        async def action():
            calls.append(1)
            if len(calls) < 3:
                raise NetworkError("boom")
            return "ok"

        async def fake_sleep(s):
            sleeps.append(s)

        assert run(m.with_retry(action, attempts=3, base_delay=2, sleep=fake_sleep)) == "ok"
        assert sleeps == [2, 4]

    def test_respects_retry_after(self):
        from telegram.error import RetryAfter

        sleeps = []
        state = {"n": 0}

        async def action():
            state["n"] += 1
            if state["n"] == 1:
                raise RetryAfter(5)
            return "ok"

        async def fake_sleep(s):
            sleeps.append(s)

        assert run(m.with_retry(action, sleep=fake_sleep)) == "ok"
        assert sleeps == [6]

    def test_gives_up_after_attempts(self):
        from telegram.error import NetworkError

        async def action():
            raise NetworkError("down")

        async def fake_sleep(s):
            pass

        with pytest.raises(NetworkError):
            run(m.with_retry(action, attempts=2, sleep=fake_sleep))

    def test_non_retryable_error_propagates_immediately(self):
        calls = []

        async def action():
            calls.append(1)
            raise ValueError("bad")

        with pytest.raises(ValueError):
            run(m.with_retry(action))
        assert len(calls) == 1


class TestSendTelegram:
    def test_sends_all_chunks_then_photo(self, tmp_path):
        shot = tmp_path / "s.png"
        shot.write_bytes(b"png")
        bot = AsyncMock()
        message = "헤더\n\n" + "\n".join(f"줄{i}" for i in range(3000))
        run(m.send_telegram(bot, "chat", message, shot))
        assert bot.send_message.await_count == len(m.build_telegram_messages(message))
        bot.send_photo.assert_awaited_once_with(chat_id="chat", photo=b"png")

    def test_missing_screenshot_is_skipped(self, tmp_path):
        bot = AsyncMock()
        run(m.send_telegram(bot, "chat", "hi", tmp_path / "none.png"))
        bot.send_photo.assert_not_awaited()


# ──────────────────────────────────────────────
# 더보기 클릭 재시도 (로딩 오버레이 대응)
# ──────────────────────────────────────────────

class TestClickMore:
    def test_retries_when_overlay_intercepts(self):
        page = AsyncMock()
        btn = AsyncMock()
        btn.click.side_effect = [TimeoutError("intercepts pointer events"), None]
        run(m._click_more(page, btn, attempts=3))
        assert btn.click.await_count == 2
        # 클릭 전마다 오버레이 해제 대기
        assert page.wait_for_function.await_count == 2

    def test_raises_after_attempts(self):
        page = AsyncMock()
        btn = AsyncMock()
        btn.click.side_effect = TimeoutError("intercepts pointer events")
        with pytest.raises(TimeoutError):
            run(m._click_more(page, btn, attempts=2))

    def test_overlay_wait_timeout_is_not_fatal(self):
        page = AsyncMock()
        page.wait_for_function.side_effect = TimeoutError("still loading")
        run(m.wait_for_loading_overlay(page, timeout=1))


# ──────────────────────────────────────────────
# main() 종료 코드 — 워크플로의 중복 발송 방지 판단 기준
# ──────────────────────────────────────────────

class _FakePlaywright:
    def __init__(self):
        self.browser = AsyncMock()
        self.chromium = AsyncMock()
        self.chromium.launch.return_value = self.browser

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def main_env(monkeypatch, tmp_path):
    for k, v in TestConfig.ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(m, "make_bot", lambda config: AsyncMock())
    monkeypatch.setattr(m.asyncio, "sleep", AsyncMock())
    fake = _FakePlaywright()
    with patch("playwright.async_api.async_playwright", return_value=fake):
        yield fake


class TestMainExitCodes:
    def test_success(self, main_env, monkeypatch):
        monkeypatch.setattr(m, "run_once", AsyncMock(return_value=("msg", Path("x.png"))))
        send = AsyncMock()
        monkeypatch.setattr(m, "send_telegram", send)
        assert run(m.main()) == m.EXIT_OK
        assert send.await_args.args[2] == "msg"
        main_env.browser.close.assert_awaited_once()

    def test_transient_failure_is_retried(self, main_env, monkeypatch):
        run_once = AsyncMock(side_effect=[TimeoutError("overlay"), ("msg", Path("x.png"))])
        monkeypatch.setattr(m, "run_once", run_once)
        monkeypatch.setattr(m, "send_telegram", AsyncMock())
        assert run(m.main()) == m.EXIT_OK
        assert run_once.await_count == 2

    def test_persistent_failure_sends_alert(self, main_env, monkeypatch):
        run_once = AsyncMock(side_effect=TimeoutError("overlay"))
        monkeypatch.setattr(m, "run_once", run_once)
        send = AsyncMock()
        monkeypatch.setattr(m, "send_telegram", send)
        assert run(m.main()) == m.EXIT_FAILED_NOTIFIED
        assert run_once.await_count == m.SCRAPE_ATTEMPTS
        assert "크롤링" in send.await_args.args[2] and "실패" in send.await_args.args[2]

    def test_telegram_failure_then_alert_failure_is_silent(self, main_env, monkeypatch):
        monkeypatch.setattr(m, "run_once", AsyncMock(return_value=("msg", None)))
        monkeypatch.setattr(m, "send_telegram", AsyncMock(side_effect=RuntimeError("telegram down")))
        assert run(m.main()) == m.EXIT_FAILED_SILENT

    def test_telegram_failure_falls_back_to_alert(self, main_env, monkeypatch):
        monkeypatch.setattr(m, "run_once", AsyncMock(return_value=("msg", None)))
        send = AsyncMock(side_effect=[RuntimeError("message too long"), None])
        monkeypatch.setattr(m, "send_telegram", send)
        assert run(m.main()) == m.EXIT_FAILED_NOTIFIED
        assert "텔레그램 전송 실패" in send.await_args.args[2]
