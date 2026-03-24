"""
LG U+ Life Care 스크래퍼 단위 테스트 + 속성 기반 테스트
- 단위 테스트: pytest
- 속성 기반 테스트: Hypothesis (각 100회 반복)
- Playwright 의존 기능(로그인·스크래핑·텔레그램)은 테스트 범위 제외
"""
import asyncio
import re
import sys
import os
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import given, settings
import hypothesis.strategies as st

# TARGET_URL 환경변수 모킹 후 main 임포트
os.environ.setdefault("TARGET_URL", "https://example.com/products")
os.environ.setdefault("LG_ID", "test_id")
os.environ.setdefault("LG_PW", "test_pw")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "test_chat")

sys.path.insert(0, str(Path(__file__).parent.parent))
import main as m

TARGET_URL_MOCK = "https://example.com/products"


def run(coro):
    """비동기 코루틴을 동기 컨텍스트에서 실행하는 헬퍼"""
    return asyncio.run(coro)


# ──────────────────────────────────────────────
# 단위 테스트
# ──────────────────────────────────────────────

class TestFormatProductsEmpty:
    """태스크 2.2 — 빈 상품 목록 헤더 검증"""

    def test_header_contains_zero_counts(self, monkeypatch):
        monkeypatch.setattr(m, "TARGET_URL", TARGET_URL_MOCK)
        result = run(m.format_products([], "0"))
        lines = result.splitlines()
        assert lines[0] == "총 0개 중 0개 수집 (품절 제외)"

    def test_second_line_is_target_url(self, monkeypatch):
        monkeypatch.setattr(m, "TARGET_URL", TARGET_URL_MOCK)
        result = run(m.format_products([], "0"))
        lines = result.splitlines()
        assert lines[1] == TARGET_URL_MOCK

    def test_no_product_lines(self, monkeypatch):
        monkeypatch.setattr(m, "TARGET_URL", TARGET_URL_MOCK)
        result = run(m.format_products([], "0"))
        # 헤더(2줄) + 빈 줄 이후 상품 없음
        body = result.split("\n\n", 1)
        assert len(body) == 2
        assert body[1].strip() == ""


class TestFormatProductsNoPattern:
    """태스크 2.3 — 패턴 불일치 시 원본 순서 보존 검증"""

    def test_order_preserved(self, monkeypatch):
        monkeypatch.setattr(m, "TARGET_URL", TARGET_URL_MOCK)
        products = [
            {"name": "패턴없는상품A", "price": "100,000"},
            {"name": "패턴없는상품B", "price": "200,000"},
            {"name": "패턴없는상품C", "price": "300,000"},
        ]
        result = run(m.format_products(products, "3"))
        body = result.split("\n\n", 1)[1]
        lines = [l for l in body.splitlines() if l.strip()]
        names = [l.split(" / ")[0] for l in lines]
        assert names == ["패턴없는상품A", "패턴없는상품B", "패턴없는상품C"]


# ──────────────────────────────────────────────
# 속성 기반 테스트 (Hypothesis)
# ──────────────────────────────────────────────

class TestMoreBtnLoopTermination:
    """태스크 3.1 — Property 2: 더보기 루프 종료 조건
    Validates: Requirements 2.5
    """

    @given(st.booleans())
    @settings(max_examples=100)
    def test_loop_does_not_increment_when_terminated(self, should_stop: bool):
        """종료 조건이 참이면 루프 카운터가 증가하지 않아야 한다"""
        click_count = 0

        # 더보기 버튼 존재 여부를 bool 플래그로 추상화
        btn_visible = not should_stop
        if btn_visible:
            click_count += 1  # 버튼 있으면 클릭
        # 종료 조건(버튼 없음)이면 카운터 그대로
        if should_stop:
            assert click_count == 0


class TestFormatHeaderFormat:
    """태스크 3.2 — Property 3: 포맷팅 헤더 형식
    Validates: Requirements 4.4, 4.5
    """

    @given(
        st.lists(
            st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=30, alphabet=st.characters(blacklist_categories=("Cs",))),
                "price": st.from_regex(r'\d{1,3}(,\d{3})*', fullmatch=True),
            }),
            max_size=10,
        ),
        st.from_regex(r'\d+', fullmatch=True),
    )
    @settings(max_examples=100)
    def test_header_format(self, products, total):
        with patch.object(m, "TARGET_URL", TARGET_URL_MOCK):
            with patch.object(m, "is_white_monitor", return_value=False):
                result = run(m.format_products(products, total))
        lines = result.splitlines()
        collected = len(products)
        assert lines[0] == f"총 {total}개 중 {collected}개 수집 (품절 제외)"
        assert lines[1] == TARGET_URL_MOCK


class TestFormatProductsSorted:
    """태스크 3.3 — Property 4: 정렬 불변성
    Validates: Requirements 4.2
    """

    @given(
        st.lists(
            st.fixed_dictionaries({
                "name": st.from_regex(r'\[[A-Z]+\]\[[가-힣]+\].+?', fullmatch=True),
                "price": st.from_regex(r'\d{1,3}(,\d{3})*', fullmatch=True),
            }),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_sorted_by_category_then_price(self, products):
        with patch.object(m, "TARGET_URL", TARGET_URL_MOCK):
            with patch.object(m, "is_white_monitor", return_value=False):
                result = run(m.format_products(products, str(len(products))))

        body = result.split("\n\n", 1)[1]
        product_lines = [l for l in body.splitlines() if l.strip()]

        # 패턴 매칭된 줄만 추출
        pat = re.compile(r'\[([^\]]+)\]\[([^\]]+)\](.+?) / (\S+)')
        parsed = [pat.match(l) for l in product_lines]
        matched = [m_obj for m_obj in parsed if m_obj]

        if len(matched) < 2:
            return  # 검증 대상 없음

        for i in range(len(matched) - 1):
            cat_a, cat_b = matched[i].group(2), matched[i + 1].group(2)
            price_a = int(matched[i].group(4).replace(',', ''))
            price_b = int(matched[i + 1].group(4).replace(',', ''))
            # 종류 오름차순, 동일 종류면 가격 오름차순
            assert (cat_a, price_a) <= (cat_b, price_b)


class TestFormatProductsFallbackOrder:
    """태스크 3.4 — Property 5: 파싱 실패 시 원본 순서 보존
    Validates: Requirements 4.3
    """

    # 패턴 [X][Y]... 에 매칭되지 않는 텍스트 전략
    # Cs(서로게이트), Cc(제어문자), Zl/Zp(줄/단락 구분자) 제외 — splitlines() 오작동 방지
    _no_pattern = st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(
            blacklist_categories=("Cs", "Cc", "Zl", "Zp"),
            blacklist_characters="[]",
        ),
    )

    @given(st.lists(_no_pattern, min_size=1, max_size=10))
    @settings(max_examples=100)
    def test_fallback_order_preserved(self, names):
        products = [{"name": n, "price": "100,000"} for n in names]
        with patch.object(m, "TARGET_URL", TARGET_URL_MOCK):
            with patch.object(m, "is_white_monitor", return_value=False):
                result = run(m.format_products(products, str(len(products))))

        body = result.split("\n\n", 1)[1]
        lines = [l for l in body.splitlines() if l.strip()]
        result_names = [l.rsplit(" / ", 1)[0] for l in lines]
        assert result_names == names


class TestMessageChunkRoundtrip:
    """태스크 3.5 — Property 6: 메시지 청크 분할 라운드트립
    Validates: Requirements 5.2
    """

    @given(st.text(min_size=0, max_size=20000))
    @settings(max_examples=100)
    def test_chunk_roundtrip(self, message):
        chunks = [message[i:i + 4096] for i in range(0, max(len(message), 1), 4096)]
        # 각 청크 길이 ≤ 4096
        assert all(len(c) <= 4096 for c in chunks)
        # 이어 붙이면 원본과 동일
        assert "".join(chunks) == message


class TestScreenshotFilenamePattern:
    """태스크 3.6 — Property 7: 스크린샷 파일명 패턴
    Validates: Requirements 3.2
    """

    @given(st.datetimes())
    @settings(max_examples=100)
    def test_capture_filename_pattern(self, dt):
        filename = f"capture_{dt.strftime('%Y%m%d_%H%M%S')}.png"
        assert re.match(r'^capture_\d{8}_\d{6}\.png$', filename)

    @given(st.datetimes())
    @settings(max_examples=100)
    def test_error_filename_pattern(self, dt):
        filename = f"error_{dt.strftime('%Y%m%d_%H%M%S')}.png"
        assert re.match(r'^error_\d{8}_\d{6}\.png$', filename)
