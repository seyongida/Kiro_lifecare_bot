# Project Structure

```
.
├── main.py                     # 크롤러 본체 — 실행 로직은 여기에 둔다
├── scripts/schedule_gate.py    # GitHub Actions 정시 실행 게이트 (stdlib only)
├── tests/                      # pytest + Hypothesis
├── .github/workflows/          # scrape.yml(매일), test.yml(CI), keepalive.yml(매월)
├── pyproject.toml / uv.lock    # 의존성 (uv)
├── requirements.txt            # pip 사용자용 — pyproject와 동일하게 유지
├── .env / .env.example         # 설정 (.env는 커밋 금지)
└── screenshots/                # 런타임 자동 생성 (gitignore)
```

## main.py 구성

- `Config.from_env()` — 환경변수 로드 + 필수값 검증
- `login(page, config)` — Life Care 사번 로그인
- `scrape_products(page, target_url)` — 더보기 반복 클릭 후 상품명/가격 수집 (로딩 오버레이 대기 포함)
- `is_white_monitor()` / `check_projector_ust()` — 모델 부가 정보 판별
- `format_products()` — 태깅 + 종류/가격 정렬 텍스트 생성
- `build_telegram_messages()` / `send_telegram()` — 4096자 분할 + 재시도 전송
- `run_once()` / `main()` — 전체 흐름, 재시도, 실패 알림, 종료 코드

## Conventions
- 실행 로직은 `main.py`에 유지 (프로젝트가 커지면 모듈 분리)
- 비밀값은 `.env`(로컬) / Repository secrets(Actions)
- 주석과 로그 메시지는 한국어
