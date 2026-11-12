# LG U+ Life Care 상품 크롤러

LG U+ Life Care(lguplus.lglifecare.com)에 사번으로 로그인하여 LG등급 상품의 이름과 가격을 수집하고, 결과를 텔레그램으로 전송하는 스크래퍼입니다. GitHub Actions로 **매일 KST 11:30경** 자동 실행됩니다.

## 동작 흐름

1. 사번/비밀번호로 Life Care 로그인
2. 지정된 카테고리 페이지에서 '더보기'를 끝까지 눌러 전체 상품 수집 (품절 제외)
3. 부가 정보 태깅
   - 등급모니터: 다나와 화이트 필터 검색으로 화이트 모델에 `(W)`
   - 프로젝터: LG전자 제품 페이지로 초단초점 모델에 ` (UST)`
4. 종류별 그룹 → 가격 오름차순 정렬
5. 텔레그램으로 상품 목록(4096자 초과 시 `[i/N]` 분할) + 화면 스크린샷 전송
6. 실패 시 최대 3회 재시도, 그래도 실패하면 **실패 알림 + 에러 스크린샷** 전송

## 프로젝트 구조

```
.
├── main.py                     # 크롤러 본체 (로그인, 수집, 태깅, 포맷, 텔레그램 전송)
├── scripts/schedule_gate.py    # GitHub Actions 정시 실행 게이트
├── tests/                      # pytest + Hypothesis 테스트
├── .github/workflows/
│   ├── scrape.yml              # 매일 크롤링
│   ├── test.yml                # push/PR 시 테스트
│   └── keepalive.yml           # 매월 빈 커밋 (스케줄 자동 중단 방지)
├── pyproject.toml / uv.lock    # 의존성 (uv)
├── requirements.txt            # pip 사용자용 (pyproject와 동일하게 유지)
├── .env.example                # 환경변수 템플릿
└── CHANGELOG.md
```

## 자동 실행 시각 (GitHub Actions)

GitHub의 `schedule` 이벤트는 정시 실행을 보장하지 않습니다. 이 저장소에서도 `KST 11:00` 예약이
3월엔 13시경, 11월엔 17시경에 시작될 만큼 지연이 점점 커졌습니다.

그래서 `scrape.yml`은 다음처럼 동작합니다.

- KST 03:07 ~ 11:07 동안 30분 간격(17회)으로 트리거 (붐비는 정각을 피해 :07/:37)
- 각 실행에서 `scripts/schedule_gate.py`가 판단
  - 오늘 이미 전송했으면 → 즉시 종료 (약 10초)
  - 목표 시각(`RUN_AT`, 기본 11:29) 전 60분 안에 도착 → 11:29까지 대기 후 실행 → **11:30경 알림**
  - 11:29 이후 도착 → 즉시 실행 (지연이 심한 날에도 그날 한 번은 반드시 전송)
  - 그보다 이르면 → 즉시 종료하고 다음 트리거에 맡김
- 중복 전송 방지: 전송(또는 실패 알림)이 완료되면 `actions/cache`에 `lifecare-sent-YYYYMMDD` 마커 저장
- 아무것도 전달하지 못한 경우(텔레그램 장애 등)에는 마커를 남기지 않아 다음 트리거가 재시도

시각을 바꾸려면 `scrape.yml`의 `env.RUN_AT`을 수정하세요 (cron 범위도 함께 앞당기거나 늦추세요).

### 수동 실행

Actions 탭 → `LG Life Care 상품 크롤링` → **Run workflow**.
`force`(기본 체크)면 시간/중복 검사 없이 즉시 실행하며, 이때는 마커를 남기지 않아 그날 정시 알림도 그대로 옵니다.

### (선택) 분 단위로 정확해야 한다면: 외부 cron

GitHub 지연이 8시간을 넘는 극단적인 날까지 대비하려면 [cron-job.org](https://cron-job.org) 같은 외부 cron으로
매일 11:25 KST에 아래 API를 호출하세요. `force=false`라 게이트 규칙(11:29 대기, 중복 방지)이 그대로 적용됩니다.

```bash
curl -X POST \
  -H "Authorization: Bearer <Actions:write 권한 fine-grained PAT>" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/<owner>/<repo>/actions/workflows/scrape.yml/dispatches \
  -d '{"ref":"main","inputs":{"force":"false"}}'
```

## 로컬 실행

### 1. 의존성 설치 ([uv](https://docs.astral.sh/uv/))

```bash
uv sync
```

```bash
uv run playwright install chromium
```

### 2. 텔레그램 봇 준비

1. 텔레그램 [@BotFather](https://t.me/BotFather)에게 `/newbot` 명령으로 봇 생성 후 토큰 복사
2. 봇에게 메시지를 보낸 뒤 `https://api.telegram.org/bot<TOKEN>/getUpdates`에서 `chat_id` 확인

### 3. 환경 변수

`.env.example`을 `.env`로 복사해 값을 채웁니다. GitHub Actions에서는 같은 이름의 **Repository secrets**를 사용합니다.

| 변수 | 설명 |
|---|---|
| `LG_ID` / `LG_PW` | Life Care 사번 / 비밀번호 |
| `TARGET_URL` | 수집할 카테고리 페이지 URL |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | 텔레그램 봇 토큰 / 채팅 ID |
| `SSL_VERIFY` (선택) | 사내망 self-signed 인증서 환경에서만 `false` (기본 `true`) |

### 4. 실행 / 테스트

```bash
uv run python main.py
```

```bash
uv run pytest
```

> `api.telegram.org` 접근이 차단된 네트워크(일부 사내망 등)에서는 텔레그램 전송이 실패합니다. VPN 또는 외부 네트워크에서 실행하세요.

### 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | 정상 전송 |
| 3 | 크롤링/전송 실패, 실패 알림은 전송됨 |
| 2 등 그 외 | 아무것도 전달하지 못함 (설정 누락, 텔레그램 장애 등) |

## 기술 스택

- Python 3.9+ (asyncio), [uv](https://docs.astral.sh/uv/)
- Playwright (Chromium headless)
- python-telegram-bot, requests, python-dotenv
- pytest + Hypothesis
