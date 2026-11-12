# Tech Stack

- Language: Python 3.9+ (async)
- Browser automation: Playwright (async API, Chromium headless)
- Messaging: python-telegram-bot
- HTTP: requests (다나와 검색)
- Config: python-dotenv (.env file)
- Dependency management: uv (pyproject.toml + uv.lock)
- Tests: pytest + Hypothesis
- Scheduling: GitHub Actions (`.github/workflows/scrape.yml` + `scripts/schedule_gate.py`)

## Common Commands

```bash
# 의존성 설치 (dev 포함)
uv sync

# Chromium 설치 (최초 1회)
uv run playwright install chromium

# 실행
uv run python main.py

# 테스트
uv run pytest
```

## Environment Variables (.env)
- `LG_ID` / `LG_PW` — Login credentials
- `TARGET_URL` — Product category page to scrape
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — Telegram delivery config
- `SSL_VERIFY` (optional) — `false` only on networks with self-signed certificates

## Notes
- Entry point: `asyncio.run(main())`; exit code 0=sent, 3=failure alert sent, other=nothing delivered
- Playwright runs Chromium headless with a 1280x720 viewport
- Telegram messages are split at 4096 characters on line boundaries
- GitHub `schedule` is best-effort and can be delayed for hours — never rely on a single cron for timing
