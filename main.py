"""LG U+ Life Care 상품 크롤러.

로그인 → 상품 목록 수집(품절 제외) → 모델별 부가 정보 태깅(화이트 모니터, 초단초점 프로젝터)
→ 종류/가격 정렬 → 텔레그램 전송까지 한 번에 수행한다.

종료 코드 (GitHub Actions 워크플로가 중복 발송 방지 판단에 사용)
  0: 정상 전송 완료
  3: 크롤링 실패, 실패 알림은 텔레그램으로 전송됨
  그 외(1, 2 등): 아무것도 전달되지 못함 → 다음 스케줄에서 재시도
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

import requests
from dotenv import load_dotenv

log = logging.getLogger("lifecare")

LOGIN_URL = "https://lguplus.lglifecare.com/auth/login"
SCREENSHOT_DIR = Path("screenshots")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

TELEGRAM_LIMIT = 4096
SCRAPE_ATTEMPTS = 3          # 로딩 오버레이 등 일시적 오류 대비 전체 재시도 횟수
MAX_MORE_CLICKS = 200        # 더보기 무한 루프 방지

EXIT_OK = 0
EXIT_FAILED_SILENT = 2
EXIT_FAILED_NOTIFIED = 3

# [등급][종류]모델명 / 가격 — 모델명에 공백이 포함될 수 있으므로 .+? 사용
PRODUCT_PATTERN = re.compile(r"\[([^\]]+)\]\[([^\]]+)\](.+?) / (\S+)$")

T = TypeVar("T")


# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

class ConfigError(RuntimeError):
    """필수 환경변수 누락"""


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() not in ("0", "false", "no", "off")


@dataclass(frozen=True)
class Config:
    lg_id: str
    lg_pw: str
    target_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    # 사내망 self-signed 인증서 환경에서는 .env에 SSL_VERIFY=false 지정
    ssl_verify: bool = True

    REQUIRED = ("LG_ID", "LG_PW", "TARGET_URL", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")

    @classmethod
    def from_env(cls) -> "Config":
        values = {name: (os.getenv(name) or "").strip() for name in cls.REQUIRED}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ConfigError(f"필수 환경변수 누락: {', '.join(missing)}")
        return cls(
            lg_id=values["LG_ID"],
            lg_pw=values["LG_PW"],
            target_url=values["TARGET_URL"],
            telegram_bot_token=values["TELEGRAM_BOT_TOKEN"],
            telegram_chat_id=values["TELEGRAM_CHAT_ID"],
            ssl_verify=_env_flag("SSL_VERIFY", True),
        )


# ──────────────────────────────────────────────
# Playwright 헬퍼
# ──────────────────────────────────────────────

# 화면에 보이는 .loading 오버레이가 하나도 없으면 true
_NO_VISIBLE_LOADING_JS = """
() => !Array.from(document.querySelectorAll('.loading')).some(el => {
    const style = getComputedStyle(el);
    return el.getClientRects().length > 0
        && style.visibility !== 'hidden'
        && style.display !== 'none';
})
"""


async def wait_for_loading_overlay(page, timeout: int = 15000) -> None:
    """사이트 공통 로딩 오버레이(.loading)가 사라질 때까지 대기.

    오버레이가 떠 있는 동안 클릭하면 클릭이 가로채져 30초 타임아웃으로 실패한다
    (2026-10 실패 런들의 원인). 타임아웃 시에는 경고만 남기고 진행한다.
    """
    try:
        await page.wait_for_function(_NO_VISIBLE_LOADING_JS, timeout=timeout)
    except Exception:
        log.warning("로딩 오버레이가 %dms 내에 사라지지 않음 — 계속 진행", timeout)


async def login(page, config: Config) -> None:
    """LG U+ Life Care 사번 로그인"""
    await page.goto(LOGIN_URL, timeout=30000)
    # networkidle 대신 domcontentloaded 사용 (회사 네트워크에서 networkidle 타임아웃 방지)
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    await page.fill('input#id[name="id"]', config.lg_id)
    await page.fill('input[name="password"]', config.lg_pw)

    # 사번 로그인 버튼 (btn_bg_gradient)
    await page.click("button.again-btn_bg_gradient")
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    # 로그인 후 팝업 닫기
    try:
        popup_btn = page.locator(".todayClosePop")
        await popup_btn.wait_for(state="visible", timeout=5000)
        await popup_btn.click()
        log.info("팝업 닫기 완료")
    except Exception:
        log.info("팝업 없음")

    log.info("로그인 완료")


async def _click_more(page, more_btn, attempts: int = 3) -> None:
    """더보기 클릭. 로딩 오버레이가 클릭을 가로채면 사라질 때까지 기다렸다 재시도"""
    for attempt in range(1, attempts + 1):
        await wait_for_loading_overlay(page)
        try:
            await more_btn.click(timeout=10000)
            return
        except Exception:
            if attempt == attempts:
                raise
            log.warning("더보기 클릭 실패 (%d/%d) — 재시도", attempt, attempts)


# 품절 제외 상품의 상품명/가격 추출. innerHTML 대신 textContent를 사용해
# &amp; 같은 HTML 엔티티나 내부 태그가 메시지에 섞이지 않도록 한다.
_EXTRACT_PRODUCTS_JS = """
() => {
    const text = el => el ? el.textContent.replace(/\\s+/g, ' ').trim() : '';
    return Array.from(document.querySelectorAll('.nhm-item'))
        .filter(item => !item.querySelector('.sold_txt'))
        .map(item => ({
            name: text(item.querySelector('.tit_cpn.ga-prd-click')),
            price: text(item.querySelector('.num-disPrice span')),
        }))
        .filter(p => p.name);
}
"""


async def scrape_products(page, target_url: str) -> tuple[list[dict], str]:
    """더보기 버튼 클릭으로 전체 상품 로드 후 수집 (품절 제외)"""
    await page.goto(target_url, timeout=30000)
    await page.wait_for_load_state("domcontentloaded", timeout=30000)

    # 첫 상품 렌더링 + 로딩 오버레이 해제까지 대기 (고정 대기만으로는 총 상품 수가 0으로 읽히기도 함)
    try:
        await page.locator(".nhm-item").first.wait_for(state="attached", timeout=15000)
    except Exception:
        log.warning("상품 목록이 15초 내에 렌더링되지 않음")
    await wait_for_loading_overlay(page)

    try:
        total = (await page.locator(".txt_mb .num").inner_text(timeout=5000)).strip()
        log.info("총 상품 수: %s", total)
    except Exception:
        total = "?"

    # 더보기 버튼이 사라질 때까지 클릭하여 전체 상품 DOM에 로드
    more_btn = page.locator("button.btn_more_down")
    for click_count in range(1, MAX_MORE_CLICKS + 1):
        if await more_btn.count() == 0 or not await more_btn.first.is_visible():
            break

        prev_count = await page.locator(".nhm-item").count()
        await _click_more(page, more_btn.first)

        try:
            await page.wait_for_function(
                "n => document.querySelectorAll('.nhm-item').length > n",
                arg=prev_count,
                timeout=10000,
            )
        except Exception:
            log.info("더보기 후 신규 상품 없음 — 로드 종료")
            break

        current_count = await page.locator(".nhm-item").count()
        log.info("더보기 %d회 클릭: %d개 로드됨", click_count, current_count)
    else:
        log.warning("더보기 최대 클릭 횟수(%d) 도달", MAX_MORE_CLICKS)

    products = await page.evaluate(_EXTRACT_PRODUCTS_JS)
    log.info("전체 %d개 수집 완료 (품절 제외)", len(products))
    return products, total


def screenshot_filename(prefix: str, when: datetime) -> str:
    return f"{prefix}_{when.strftime('%Y%m%d_%H%M%S')}.png"


async def take_screenshot(page, prefix: str = "capture", full_page: bool = False) -> Path:
    """현재 화면 스크린샷 저장"""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    filepath = SCREENSHOT_DIR / screenshot_filename(prefix, datetime.now())
    await page.screenshot(path=str(filepath), full_page=full_page)
    log.info("스크린샷 저장: %s", filepath)
    return filepath


# ──────────────────────────────────────────────
# 부가 정보 태깅
# ──────────────────────────────────────────────

def strip_kr_suffix(model_name: str) -> str:
    """한국 유통 suffix 제거: 27SR75U.AKRG → 27SR75U"""
    return re.sub(r"\.[A-Z]+$", "", model_name).strip()


def is_white_monitor(model_name: str, verify: bool = True) -> bool:
    """다나와 화이트 모니터 필터 검색으로 화이트 색상 여부 판별 (등급모니터 전용)

    한국 유통 suffix(.AKRG 등) 제거 후 base 모델명으로
    다나와 LG 화이트 모니터 필터 검색 결과에 해당 모델이 있으면 화이트로 판정
    """
    base = strip_kr_suffix(model_name)

    params = {
        "query": base,
        "maker": "2137",                          # LG전자
        "attribute": "346318-916486-OR",           # 화이트 색상 필터
        "defaultPhysicsCategoryCode": "860|13735|14883|58972",
        "tab": "main",
        "mode": "simple",
    }
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.danawa.com/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        resp = requests.get(
            "https://search.danawa.com/dsearch.php",
            params=params, headers=headers, timeout=10, verify=verify,
        )
        text = resp.text

        if "검색된 상품이 없습니다" in text or "결과가 없습니다" in text:
            log.info("  색상판별 [%s]: 검색결과 없음 → 비화이트", base)
            return False

        # 연관 상품이 함께 노출될 수 있으므로 prod_name 블록 텍스트에 정확한 모델명이 있어야 화이트
        blocks = re.findall(r'class="prod_name">(.*?)</p>', text, re.DOTALL)
        for block in blocks:
            names = re.findall(r">([^<>\n]+)<", block)
            full_name = " ".join(n.strip() for n in names if n.strip())
            if base.lower() in full_name.lower():
                log.info("  색상판별 [%s]: '%s' → 화이트", base, full_name)
                return True

        log.info("  색상판별 [%s]: 정확 매칭 없음 → 비화이트", base)
        return False

    except Exception as e:
        log.warning("  색상판별 [%s]: 오류(%s) → 비화이트", base, e)
        return False


def projector_slug(model_name: str) -> str:
    return model_name.split(".")[0].lower()


async def check_projector_ust(model_name: str, browser_page) -> bool:
    """LG 전자 제품 페이지에서 초단초점 여부 판별 (실패 시 False 반환)

    연관 상품 등 다른 섹션에 '초단초점'이 노출될 수 있으므로
    '투사형' 존재 여부를 우선 확인하여 오판 방지.
    """
    slug = projector_slug(model_name)
    url = f"https://www.lge.co.kr/projectors/{slug}"
    try:
        await browser_page.goto(url, timeout=20000, wait_until="networkidle")
        content = await browser_page.content()
        if "투사형" in content:
            log.info("  UST판별 [%s]: 투사형 확인 → 비초단초점", slug)
            return False
        result = "초단초점" in content
        log.info("  UST판별 [%s]: %s", slug, "초단초점" if result else "투사형")
        return result
    except Exception as e:
        log.warning("  UST판별 [%s]: 오류(%s) → 비초단초점", slug, e)
        return False


# ──────────────────────────────────────────────
# 포맷팅
# ──────────────────────────────────────────────

def parse_price(price: str) -> float:
    """'1,234,000원' → 1234000. 숫자가 없으면 정렬 시 맨 뒤로 가도록 inf"""
    digits = re.sub(r"\D", "", price)
    return int(digits) if digits else float("inf")


async def format_products(
    products: list[dict],
    total: str,
    target_url: str,
    ust_page=None,
    ssl_verify: bool = True,
) -> str:
    """상품 목록을 종류별 그룹 후 가격 오름차순 정렬하여 텍스트 생성"""
    header = f"총 {total}개 중 {len(products)}개 수집 (품절 제외)\n{target_url}"

    # [등급, 종류, 모델명, 가격]
    matched: list[list[str]] = []
    unmatched: list[str] = []
    for p in products:
        line = f"{p['name']} / {p['price']}"
        m = PRODUCT_PATTERN.match(line)
        if m:
            matched.append(list(m.groups()))
        else:
            unmatched.append(line)

    # 등급모니터: 화이트 여부 판별 후 모델명에 (W) 추가 (동일 모델 중복 요청 방지 캐시)
    white_cache: dict[str, bool] = {}
    for item in matched:
        if "등급모니터" in item[1]:
            base = strip_kr_suffix(item[2])
            if base not in white_cache:
                # requests는 블로킹 호출이므로 이벤트 루프를 막지 않도록 스레드에서 실행
                white_cache[base] = await asyncio.to_thread(is_white_monitor, item[2], ssl_verify)
            if white_cache[base]:
                item[2] = f"{item[2]}(W)"
                log.info("  화이트 확정: %s", item[2])

    # 프로젝터: 초단초점 여부 판별 후 모델명에 (UST) 추가 (ust_page 없으면 스킵)
    if ust_page is not None:
        ust_cache: dict[str, bool] = {}
        for item in matched:
            if "프로젝터" in item[1]:
                slug = projector_slug(item[2])
                if slug not in ust_cache:
                    ust_cache[slug] = await check_projector_ust(item[2], ust_page)
                if ust_cache[slug]:
                    item[2] = f"{item[2]} (UST)"
                    log.info("  UST 확정: %s", item[2])

    # 종류 기준 1차 정렬, 가격 기준 2차 오름차순 정렬. 패턴 미매칭 상품은 원본 순서로 뒤에 추가
    matched.sort(key=lambda x: (x[1], parse_price(x[3])))
    sorted_lines = [f"[{g}][{c}]{name} / {price}" for g, c, name, price in matched]

    log.info("포맷 완료: 정렬 %d개, 미매칭 %d개", len(sorted_lines), len(unmatched))
    return f"{header}\n\n" + "\n".join(sorted_lines + unmatched)


def chunk_text(message: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """메시지를 limit 길이 이하 조각으로 분할 (이어 붙이면 원본과 동일).

    가능하면 줄바꿈 직후에서 잘라 상품 한 줄이 두 메시지로 쪼개지지 않게 한다.
    한 줄이 limit보다 길면 그 줄만 강제로 자른다.
    """
    if not message:
        return [message]
    chunks = []
    start = 0
    while len(message) - start > limit:
        end = start + limit
        newline = message.rfind("\n", start, end)
        if newline != -1:
            end = newline + 1
        chunks.append(message[start:end])
        start = end
    chunks.append(message[start:])
    return chunks


def build_telegram_messages(message: str, limit: int = TELEGRAM_LIMIT, index_reserve: int = 24) -> list[str]:
    """텔레그램 전송용 메시지 목록 생성.

    분할이 발생하지 않으면 원본 메시지를 그대로 반환한다.
    분할이 발생하면 각 조각 상단에 "[i/총개수]" 순번 표시와, 상품 총 개수를
    알려주는 원본 헤더(format_products가 만든 "총 N개 중 M개 수집..." 줄)를
    함께 반복해서 붙인다. 원본 헤더는 메시지의 첫 "\\n\\n" 앞부분으로 판단한다.
    """
    if len(message) <= limit:
        return [message]

    if "\n\n" in message:
        header, body = message.split("\n\n", 1)
    else:
        header, body = "", message

    header_block_len = len(header) + 2 if header else 0
    if header and index_reserve + header_block_len >= limit:
        # 헤더 자체가 지나치게 길면 반복하지 않고 순번 표시만 유지한다
        header, header_block_len = "", 0
    chunk_size = max(limit - index_reserve - header_block_len, 1)
    body_chunks = chunk_text(body, chunk_size)
    total = len(body_chunks)

    messages = []
    for i, chunk in enumerate(body_chunks, start=1):
        index_line = f"[{i}/{total}]"
        if header:
            messages.append(f"{index_line}\n{header}\n\n{chunk}")
        else:
            messages.append(f"{index_line}\n{chunk}")
    return messages


# ──────────────────────────────────────────────
# 텔레그램
# ──────────────────────────────────────────────

async def with_retry(
    action: Callable[[], Awaitable[T]],
    attempts: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """텔레그램 일시 오류(RetryAfter, 네트워크 오류) 재시도"""
    from telegram.error import NetworkError, RetryAfter

    for attempt in range(1, attempts + 1):
        try:
            return await action()
        except RetryAfter as e:
            if attempt == attempts:
                raise
            wait = e.retry_after
            wait = wait.total_seconds() if hasattr(wait, "total_seconds") else float(wait)
            log.warning("텔레그램 RetryAfter — %.0f초 후 재시도", wait)
            await sleep(wait + 1)
        except NetworkError as e:
            if attempt == attempts:
                raise
            delay = base_delay * 2 ** (attempt - 1)
            log.warning("텔레그램 네트워크 오류(%s) — %.0f초 후 재시도", e, delay)
            await sleep(delay)
    raise AssertionError("unreachable")


def make_bot(config: Config):
    from telegram import Bot
    from telegram.request import HTTPXRequest

    return Bot(
        token=config.telegram_bot_token,
        request=HTTPXRequest(http_version="1.1", httpx_kwargs={"verify": config.ssl_verify}),
    )


async def send_telegram(bot, chat_id: str, message: str, screenshot_path: Path | None) -> None:
    """텔레그램으로 메시지 + 스크린샷 전송"""
    for text in build_telegram_messages(message):
        await with_retry(lambda text=text: bot.send_message(chat_id=chat_id, text=text))

    if screenshot_path and screenshot_path.exists():
        photo = screenshot_path.read_bytes()
        await with_retry(lambda: bot.send_photo(chat_id=chat_id, photo=photo))

    log.info("텔레그램 전송 완료")


def format_error_alert(error: BaseException, stage: str) -> str:
    detail = str(error).strip().splitlines()[0] if str(error).strip() else ""
    return (
        f"⚠️ LG Life Care {stage} 실패\n"
        f"{type(error).__name__}: {detail[:500]}\n"
        "GitHub Actions 로그와 screenshots artifact를 확인하세요."
    )


# ──────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────

async def run_once(browser, config: Config) -> tuple[str, Path]:
    """로그인부터 메시지 생성까지 1회 수행. 실패 시 에러 스크린샷 저장 후 예외 전파"""
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    # UST 판별용 컨텍스트 (lge.co.kr은 User-Agent 미설정 시 JS 렌더링 안 됨)
    ust_context = await browser.new_context(user_agent=UA)
    page = await context.new_page()
    try:
        await login(page, config)
        products, total = await scrape_products(page, config.target_url)
        screenshot_path = await take_screenshot(page)

        if not products:
            return "오늘은 등록된 상품이 없습니다.", screenshot_path

        ust_page = await ust_context.new_page()
        message = await format_products(
            products, total, config.target_url, ust_page=ust_page, ssl_verify=config.ssl_verify,
        )
        return message, screenshot_path
    except Exception:
        try:
            await take_screenshot(page, prefix="error", full_page=True)
        except Exception as shot_error:
            log.warning("에러 스크린샷 저장 실패: %s", shot_error)
        raise
    finally:
        await ust_context.close()
        await context.close()


async def main() -> int:
    from playwright.async_api import async_playwright

    config = Config.from_env()
    if not config.ssl_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        log.warning("SSL 인증서 검증 비활성화 (SSL_VERIFY=false)")

    bot = make_bot(config)
    last_error: BaseException | None = None
    failed_stage = f"크롤링({SCRAPE_ATTEMPTS}회 시도)"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for attempt in range(1, SCRAPE_ATTEMPTS + 1):
                try:
                    message, screenshot_path = await run_once(browser, config)
                    break
                except Exception as e:
                    last_error = e
                    log.exception("크롤링 실패 (%d/%d)", attempt, SCRAPE_ATTEMPTS)
                    if attempt < SCRAPE_ATTEMPTS:
                        await asyncio.sleep(10 * attempt)
            else:
                message = screenshot_path = None
        finally:
            await browser.close()

    if message is not None:
        try:
            await send_telegram(bot, config.telegram_chat_id, message, screenshot_path)
            return EXIT_OK
        except Exception as e:
            last_error = e
            failed_stage = "텔레그램 전송"
            log.exception("텔레그램 전송 실패")

    # 크롤링 또는 전송 실패 — 조용히 끝나지 않도록 실패 알림 전송
    assert last_error is not None
    error_shots = sorted(SCREENSHOT_DIR.glob("error_*.png"))
    try:
        await send_telegram(
            bot, config.telegram_chat_id,
            format_error_alert(last_error, failed_stage),
            error_shots[-1] if error_shots else None,
        )
        return EXIT_FAILED_NOTIFIED
    except Exception:
        log.exception("실패 알림 전송 실패")
        return EXIT_FAILED_SILENT


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    # httpx 요청 로그에는 봇 토큰이 포함된 URL이 찍히므로 숨긴다
    logging.getLogger("httpx").setLevel(logging.WARNING)


if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    try:
        sys.exit(asyncio.run(main()))
    except ConfigError as e:
        log.error("%s", e)
        sys.exit(EXIT_FAILED_SILENT)
