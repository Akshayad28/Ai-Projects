import asyncio
from playwright.async_api import async_playwright
from app.providers.amazon.parser import parse_amazon_search_page
from app.providers.flipkart.parser import parse_flipkart_search_page

async def test_amazon_and_flipkart():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        
        # Test Amazon with raw query
        page = await context.new_page()
        q1 = "best office chair under ₹25,000"
        url_amz = f"https://www.amazon.in/s?k={q1}"
        print(f"Navigating to Amazon: {url_amz}")
        resp = await page.goto(url_amz, wait_until="domcontentloaded")
        print("Amazon URL:", page.url, "Status:", resp.status if resp else None, "Title:", await page.title())
        html_amz = await page.content()
        cards_amz = parse_amazon_search_page(html_amz)
        print("Amazon parsed with raw query:", len(cards_amz))

        # Test Amazon with cleaned query: "office chair"
        q_clean = "office chair"
        url_amz2 = f"https://www.amazon.in/s?k={q_clean}"
        print(f"Navigating to Amazon with clean query: {url_amz2}")
        resp = await page.goto(url_amz2, wait_until="domcontentloaded")
        html_amz2 = await page.content()
        cards_amz2 = parse_amazon_search_page(html_amz2)
        print("Amazon parsed with clean query:", len(cards_amz2))
        if cards_amz2:
            print("First item:", cards_amz2[0])

        # Test Flipkart with raw query
        url_fk = f"https://www.flipkart.com/search?q={q1}"
        print(f"\nNavigating to Flipkart: {url_fk}")
        resp = await page.goto(url_fk, wait_until="domcontentloaded")
        print("Flipkart URL:", page.url, "Status:", resp.status if resp else None, "Title:", await page.title())
        html_fk = await page.content()
        cards_fk = parse_flipkart_search_page(html_fk)
        print("Flipkart parsed with raw query:", len(cards_fk))

        # Test Flipkart with clean query
        url_fk2 = f"https://www.flipkart.com/search?q={q_clean}"
        print(f"Navigating to Flipkart with clean query: {url_fk2}")
        resp = await page.goto(url_fk2, wait_until="domcontentloaded")
        html_fk2 = await page.content()
        cards_fk2 = parse_flipkart_search_page(html_fk2)
        print("Flipkart parsed with clean query:", len(cards_fk2))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_amazon_and_flipkart())
