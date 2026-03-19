# Tech Stack

- Language: Python 3 (async)
- Browser automation: Playwright (async API, Chromium headless)
- Messaging: python-telegram-bot
- Config: python-dotenv (.env file)
- Dependency management: pip with requirements.txt

## Dependencies (requirements.txt)
- playwright==1.49.1
- python-dotenv==1.0.1
- python-telegram-bot==21.9

## Common Commands

```bash
# Install dependencies (using uv)
uv sync --all-groups

# Run the dev server
uvicorn backend.main:app --reload

# Run tests
pytest
```

## Environment Variables (.env)
- `LG_ID` / `LG_PW` — Login credentials
- `TARGET_URL` — Product category page to scrape
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` — Telegram delivery config

## Notes
- All async code uses `asyncio.run()` as the entry point
- Playwright runs Chromium in headless mode with a 1280x720 viewport
- Telegram messages are chunked at 4096 characters to respect API limits
