import os
import re
import asyncio
from datetime import datetime
from pathlib import Path

import requests
import urllib3
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from telegram import Bot
from telegram.request import HTTPXRequest

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    await page.screenshot(path=str(filepath), full_page=False)
    print(f"스크린샷 저장: {filepath}")
    return filepath


def is_white_monitor(model_name: str) -> bool:
    """다나와 화이트 모니터 필터 검색으로 화이트 색상 여부 판별 (등급모니터 전용)
    
    한국 유통 suffix(.AKRG 등) 제거 후 base 모델명으로
    다나와 LG 화이트 모니터 필터 검색 결과에 해당 모델이 있으면 화이트로 판정
    """
    # 한국 유통 suffix 제거: 27SR75U.AKRG → 27SR75U
    base = re.sub(r'\.[A-Z]+$', '', model_name).strip()

    params = {
        "query": base,
        "maker": "2137",                          # LG전자
        "attribute": "346318-916486-OR",           # 화이트 색상 필터
        "defaultPhysicsCategoryCode": "860|13735|14883|58972",
        "tab": "main",
        "mode": "simple",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.danawa.com/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        resp = requests.get(
            "https://search.danawa.com/dsearch.php",
            params=params, headers=headers, timeout=10, verify=False
        )
        text = resp.text

        # 검색 결과 없으면 비화이트
        if "검색된 상품이 없습니다" in text or "결과가 없습니다" in text:
            print(f"  색상판별 [{base}]: 검색결과 없음 → 비화이트")
            return False

        # prod_name 블록 내 텍스트에 base 모델명이 포함되는지 확인
        # 연관 상품이 함께 노출될 수 있으므로 정확한 모델명 매칭 필요
        blocks = re.findall(r'class="prod_name">(.*?)</p>', text, re.DOTALL)
        for block in blocks:
            names = re.findall(r'>([^<>\n]+)<', block)
            full_name = ' '.join(n.strip() for n in names if n.strip())
            if base.lower() in full_name.lower():
                print(f"  색상판별 [{base}]: '{full_name}' → 화이트")
                return True

        print(f"  색상판별 [{base}]: 정확 매칭 없음 → 비화이트")
        return False

    except Exception as e:
        print(f"  색상판별 [{base}]: 오류({e}) → 비화이트")
        return False


async def format_products(products, total):
    """상품 목록을 종류별 그룹 후 가격 오름차순 정렬하여 텍스트 생성"""
    collected = len(products)
    header = f"총 {total}개 중 {collected}개 수집 (품절 제외)\n{TARGET_URL}"

    # [등급][종류]모델명 / 가격 패턴 파싱 (index: 0=등급, 1=종류, 2=모델명, 3=가격)
    # 모델명에 공백이 포함될 수 있으므로 .+? 사용
    pattern = re.compile(r'\[([^\]]+)\]\[([^\]]+)\](.+?) / (\S+)$')

    matched = []
    unmatched = []

    for p in products:
        line = f"{p['name']} / {p['price']}"
        m = pattern.match(line)
        if m:
            matched.append(list(m.groups()))
        else:
            unmatched.append(line)

    # 등급모니터 상품에 한해 화이트 여부 판별 후 모델명에 (W) 추가
    for item in matched:
        if '등급모니터' in item[1]:
            if is_white_monitor(item[2]):
                item[2] = f"{item[2]}(W)"
                print(f"  화이트 확정: {item[2]}")

    # 패턴 매칭된 상품: 종류(1) 기준 1차 정렬, 가격(3) 기준 2차 오름차순 정렬
    sorted_matched = sorted(
        matched,
        key=lambda x: (x[1], int(x[3].replace(',', '')))
    )
    sorted_lines = [f"[{m[0]}][{m[1]}]{m[2]} / {m[3]}" for m in sorted_matched]

    # 패턴 미매칭 상품은 뒤에 그대로 추가
    all_lines = sorted_lines + unmatched

    print(f"포맷 완료: 정렬 {len(sorted_lines)}개, 미매칭 {len(unmatched)}개")
    return f"{header}\n\n" + "\n".join(all_lines)


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
                message = await format_products(products, total)
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
