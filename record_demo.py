import asyncio
import os
import shutil
from playwright.async_api import async_playwright

FRONTEND_URL = "https://banking-assistant-frontend-643886936720.us-east1.run.app"
ARTIFACT_DIR = "/config/.gemini/antigravity/brain/d61ce36e-44c5-4b48-8067-cc11848867bc"
OUTPUT_VIDEO_PATH = os.path.join(ARTIFACT_DIR, "demo_video.webm")
TEMP_VIDEO_DIR = "/tmp/playwright_videos"

async def record_demo():
    if os.path.exists(TEMP_VIDEO_DIR):
        shutil.rmtree(TEMP_VIDEO_DIR)
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=TEMP_VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print(f"Navigating to {FRONTEND_URL}...")
        await page.goto(FRONTEND_URL)
        await page.wait_for_timeout(2000)

        # Scenario 1: Show available Home Loan products
        print("Scenario 1: Show available Home Loan products")
        input_selector = "input#input"
        await page.fill(input_selector, "Show available Home Loan products")
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")

        # Wait for agent reply
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 1 && !document.querySelectorAll('.msg.agent')[0].textContent.includes('…')", timeout=45000)
        await page.wait_for_timeout(3000)

        # Scenario 2: Calculate EMI for ₹20 lakh at 8.5% for 20 years
        print("Scenario 2: Calculate EMI for ₹20 lakh at 8.5% for 20 years")
        await page.fill(input_selector, "Calculate EMI for ₹20 lakh at 8.5% for 20 years")
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")

        # Wait for agent reply
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 2 && !document.querySelectorAll('.msg.agent')[1].textContent.includes('…')", timeout=45000)
        await page.wait_for_timeout(3000)

        # Scenario 3: Generate a Home Loan promotional banner
        print("Scenario 3: Generate a Home Loan promotional banner")
        await page.fill(input_selector, "Generate a Home Loan promotional banner")
        await page.wait_for_timeout(1000)
        await page.click("button[type='submit']")

        # Wait for agent reply (image generation tool)
        await page.wait_for_function("document.querySelectorAll('.msg.agent').length >= 3 && !document.querySelectorAll('.msg.agent')[2].textContent.includes('…')", timeout=60000)
        await page.wait_for_timeout(5000)

        video = page.video
        await context.close()
        await browser.close()

        if video:
            video_path = await video.path()
            print(f"Recorded video saved to temp path: {video_path}")
            shutil.copy(video_path, OUTPUT_VIDEO_PATH)
            print(f"Copied demo video to: {OUTPUT_VIDEO_PATH}")

if __name__ == "__main__":
    asyncio.run(record_demo())
