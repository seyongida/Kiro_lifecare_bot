# LG U+ Life Care 상품 크롤러

LG U+ Life Care(lguplus.lglifecare.com)에 사번으로 로그인하여 LG등급 상품의 이름과 가격을 수집하고, 결과를 텔레그램으로 전송하는 스크래퍼입니다.

## 동작 흐름

1. 사번/비밀번호로 Life Care 로그인
2. 지정된 카테고리 페이지에서 상품 정보 수집 (품절 제외)
3. 등급/가격 기준으로 정렬
4. 전체 페이지 스크린샷 캡처
5. 텔레그램 봇으로 상품 목록 + 스크린샷 전송

## 프로젝트 구조

```
.
├── main.py              # 전체 로직 (로그인, 크롤링, 텔레그램 전송)
├── requirements.txt     # Python 의존성
├── .env                 # 인증 정보 및 설정 (git 미추적)
├── .gitignore
├── CHANGELOG.md
└── screenshots/         # 런타임 시 자동 생성
```

## 사전 환경 구성

### 1. uv 설치

이 프로젝트는 `uv`로 Python 환경과 의존성을 관리합니다.

```bash
# pip으로 설치
pip install uv

# 또는 공식 설치 스크립트 (권장)
# https://docs.astral.sh/uv/getting-started/installation/
```

### 2. 의존성 설치

```bash
uv sync
```

### 3. Playwright Chromium 브라우저 설치 (최초 1회)

```bash
.venv\Scripts\python.exe -m playwright install chromium
```

### 4. 텔레그램 봇 준비

텔레그램 봇이 없다면:
1. 텔레그램에서 [@BotFather](https://t.me/BotFather)에게 `/newbot` 명령으로 봇 생성
2. 발급된 `BOT_TOKEN` 복사
3. 봇에게 메시지를 보낸 뒤 `https://api.telegram.org/bot<TOKEN>/getUpdates`에서 `chat_id` 확인

## 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
LG_ID=사번
LG_PW=비밀번호
TARGET_URL=https://lguplus.lglifecare.com/products?displayCategoryNo=364503&depth=2&displayCategoryName=LG%EB%93%B1%EA%B8%89&upperDisplayCategoryNo=364344
TELEGRAM_BOT_TOKEN=텔레그램_봇_토큰
TELEGRAM_CHAT_ID=텔레그램_채팅_ID
```

## 실행

```bash
.venv\Scripts\python.exe main.py
```

> `api.telegram.org` 접근이 차단된 네트워크(일부 사내망 등)에서는 텔레그램 전송이 실패합니다. VPN 또는 외부 네트워크 환경에서 실행하세요.

## 기술 스택

- Python 3 (async)
- [uv](https://docs.astral.sh/uv/) — 패키지 및 환경 관리
- Playwright (Chromium headless)
- python-telegram-bot
- python-dotenv
