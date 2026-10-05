import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()
        
        # Test 1: google.co.in with query
        url1 = "https://www.google.co.in/search?tbm=shop&q=best+office+chair+under+%E2%82%B925%2C000&gl=in&hl=en"
        print(f"Navigating to {url1}...")
        resp = await page.goto(url1, wait_until="domcontentloaded")
        print("Final URL:", page.url)
        print("Status:", resp.status if resp else "None")
        print("Title:", await page.title())
        content = await page.content()
        print("Content length:", len(content))
        print("Is sorry in url?", "sorry" in page.url)
        print("Content snippet (first 500 chars):", content[:500])
        
        # Check if consent or captcha or results
        cards = await page.locator("div.sh-dgr__grid-result, div.sh-dgr__content, div.pla-unit, div.mnr-c").count()
        print("Cards found with existing selectors:", cards)

        # What are the search results containers on page?
        body_text = await page.inner_text("body")
        print("Body text snippet (first 500 chars):", body_text[:500])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
