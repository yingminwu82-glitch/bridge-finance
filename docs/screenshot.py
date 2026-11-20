"""
Batch screenshot script for GBA Bridge Finance application.
Captures all pages and saves as PNG files.
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE_URL = "https://frontend-six-blush-39.vercel.app"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")

# All pages to capture
PAGES = [
    ("01-homepage", "/", 3000),
    ("02-app-dashboard", "/app/dashboard", 5000),
    ("03-documents", "/app/documents", 4000),
    ("04-graph", "/app/graph", 5000),
    ("05-cashflow", "/app/cashflow", 5000),
    ("06-report", "/app/report", 4000),
    ("07-rm-dashboard", "/rm/dashboard", 5000),
    ("08-monitoring", "/monitoring", 4000),
]


async def capture_pages():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
            locale="zh-CN",
        )
        page = await context.new_page()

        for name, path, wait_ms in PAGES:
            url = f"{BASE_URL}{path}"
            print(f"  Capturing: {name} -> {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(wait_ms)
                screenshot_path = os.path.join(OUTPUT_DIR, f"{name}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"    OK: {screenshot_path}")
            except Exception as e:
                print(f"    ERROR: {e}")
                # Try to take screenshot anyway
                try:
                    screenshot_path = os.path.join(OUTPUT_DIR, f"{name}.png")
                    await page.screenshot(path=screenshot_path, full_page=True)
                    print(f"    Partial: {screenshot_path}")
                except:
                    pass

        await browser.close()
        print("\nAll screenshots captured!")


if __name__ == "__main__":
    asyncio.run(capture_pages())
