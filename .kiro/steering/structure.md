# Project Structure

```
.
├── main.py              # Single-file application — all logic lives here
├── requirements.txt     # Python dependencies
├── .env                 # Credentials and config (not committed)
├── .gitignore
└── screenshots/         # Auto-created at runtime for page captures
```

## Architecture
This is a single-script project. All functions are defined in `main.py`:

- `login(page)` — Authenticates with the Life Care site
- `scrape_products(page)` — Extracts product name/price from the target URL
- `take_screenshot(page)` — Saves a timestamped full-page PNG
- `send_telegram(products, screenshot_path)` — Delivers results via Telegram bot
- `main()` — Orchestrates the full pipeline

## Conventions
- Keep logic in `main.py` unless the project grows to need modules
- Screenshots go to `screenshots/` (gitignored, created at runtime)
- Secrets live in `.env` and are loaded via `python-dotenv`
- Comments and print statements are in Korean (한국어)
