import os
import re
import asyncio
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright
import httpx
from telegram import Bot
from telegram.request import HTTPXRequest

load_dotenv()

LG_ID = os.getenv("LG_ID")
LG_PW = os.getenv("LG_PW")
TARGET_URL = os.getenv("TARGET_URL")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


async def login(page):
    """LG U+ Life Care 사번 로그인"""
    await page.goto("https://lguplus.lglifecare.com/auth/login", timeout=30000)
    # networkidle 대신 domcontentloaded 사용 (회사 네트워크에서 networkidle 타임아웃 방지)
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    await page.fill('input#id[name="id"]', LG_ID)
    await page.fill('input[name="password"]', LG_PW)

    # 사번 로그인 버튼 (btn_bg_gradient)
    await page.click('button.again-btn_bg_gradient')
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    # 로그인 후 팝업 닫기
    try:
        popup_btn = page.locator('.todayClosePop')
        await popup_btn.wait_for(state="visible", timeout=5000)
        await popup_btn.click()
        print("팝업 닫기 완료")
    except Exception:
        print("팝업 없음")

    print("로그인 완료")


async def scrape_products(page):
    """더보기 버튼 클릭으로 전체 상품 로드 후 수집 (품절 제외)"""
    await page.goto(TARGET_URL, timeout=30000)
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    # 총 상품 수 확인
    try:
        total = await page.locator('.txt_mb .num').inner_text()
        print(f"총 상품 수: {total}")
    except Exception:
        total = "?"

    # 더보기 버튼이 사라질 때까지 클릭하여 전체 상품 DOM에 로드
    click_count = 0
    while True:
        more_btn = page.locator('button.btn_more_down')
        if await more_btn.count() == 0 or not await more_btn.is_visible():
            break

        prev_count = await page.locator('.nhm-item').count()
        await more_btn.click()

        # 새 상품 로드 대기
        try:
            await page.wait_for_function(
                f"document.querySelectorAll('.nhm-item').length > {prev_count}",
                timeout=10000
            )
        except Exception:
            break

        click_count += 1
        current_count = await page.locator('.nhm-item').count()
        print(f"더보기 {click_count}회 클릭: {current_count}개 로드됨")

    # 전체 상품 한 번에 수집
    products = await page.evaluate("""
        () => {
            const items = document.querySelectorAll('.nhm-item');
            return Array.from(items)
                .filter(item => !item.querySelector('.sold_txt'))
                .map(item => {
                    const nameEl = item.querySelector('.tit_cpn.ga-prd-click');
                    const priceEl = item.querySelector('.num-disPrice span');
                    return {
                        name: nameEl ? nameEl.innerHTML.trim() : '',
                        price: priceEl ? priceEl.innerHTML.trim() : ''
                    };
                })
                .filter(p => p.name);
        }
    """)

    print(f"전체 {len(products)}개 수집 완료 (품절 제외)")
    return products, total


async def take_screenshot(page):
    """페이지 전체 스크린샷"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = SCREENSHOT_DIR / f"capture_{timestamp}.png"
    await page.screenshot(path=str(filepath), full_page=True)
    print(f"스크린샷 저장: {filepath}")
    return filepath


def format_products(products, total):
    """상품 목록을 종류별 그룹 후 가격 오름차순 정렬하여 텍스트 생성"""
    collected = len(products)
    lines = [f"{p['name']} / {p['price']}" for p in products]
    product_text = "\n".join(lines)

    # [등급][종류]모델명 / 가격 패턴 파싱 (index: 0=등급, 1=종류, 2=모델명, 3=가격)
    pattern = re.compile(r'\[([^\]]+)\]\[([^\]]+)\](\S+) / (\S+)')
    matches = pattern.findall(product_text)

    header = f"총 {total}개 중 {collected}개 수집 (품절 제외)\n{TARGET_URL}"

    if matches:
        # 종류(1) 기준 1차 정렬, 가격(3) 기준 2차 오름차순 정렬
        sorted_matches = sorted(
            matches,
            key=lambda x: (x[1], int(x[3].replace(',', '')))
        )
        sorted_text = '\n'.join(
            f"[{m[0]}][{m[1]}]{m[2]} / {m[3]}" for m in sorted_matches
        )
        return f"{header}\n\n{sorted_text}"

    # 패턴 매칭 안 되면 원본 그대로
    return f"{header}\n\n{product_text}"


async def send_telegram(message, screenshot_path):
    """텔레그램으로 메시지 + 스크린샷 전송"""
    # 회사 네트워크 self-signed 인증서 우회
    bot = Bot(token=TELEGRAM_BOT_TOKEN, request=HTTPXRequest(
        http_version="1.1",
        httpx_kwargs={"verify": False}
    ))

    for i in range(0, len(message), 4096):
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message[i:i+4096])

    with open(screenshot_path, "rb") as photo:
        await bot.send_photo(chat_id=TELEGRAM_CHAT_ID, photo=photo)

    print("텔레그램 전송 완료")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()

        try:
            await login(page)
            products, total = await scrape_products(page)
            screenshot_path = await take_screenshot(page)

            if products:
                message = format_products(products, total)
                await send_telegram(message, screenshot_path)
            else:
                await send_telegram("오늘은 등록된 상품이 없습니다.", screenshot_path)

        except Exception as e:
            print(f"에러 발생: {e}")
            error_path = SCREENSHOT_DIR / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(error_path), full_page=True)
            raise
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
