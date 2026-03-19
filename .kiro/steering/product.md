# Product Summary

Web scraper that logs into LG U+ Life Care (lguplus.lglifecare.com), collects product names and prices from a target category page, takes a full-page screenshot, and sends the results to a Telegram chat via bot.

The tool is designed for periodic price monitoring of LG-grade products on the Life Care platform.

## Key Workflow
1. Authenticate with LG U+ Life Care using stored credentials
2. Navigate to a configured product category URL
3. Extract product name/price pairs from the listing
4. Capture a full-page screenshot
5. Send formatted product list + screenshot to Telegram
