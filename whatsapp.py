import asyncio
import os
from playwright.async_api import async_playwright

# --- CONFIG ---
PORT = 9333
IMAGE_PATH = r"C:\Users\Jun\Documents\GitHub\email-getter-and-validate\Whatsapp.jpeg"
NUMBERS_FILE = "contacts.txt"
MESSAGE = "🔥Face to Face Course\n\n**Full Set Account + Tax Course 26-4-26 @Sunday 10am-4pm**\n\n* * 5 months 100 hours*\n* * Learn from ZERO*\n\n*Ablesoft Cheras 012-2350 997*"
SECOND_MESSAGE = "How about your registration ❓"

def copy_image_to_clipboard(path):
    """Uses Windows PowerShell to copy the file to the system clipboard."""
    print("📋 Copying image to Windows clipboard...")
    os.system(f'powershell -command "Set-Clipboard -Path \'{path}\'"')

async def run_automation():
    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Error: Image not found at {IMAGE_PATH}")
        return

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{PORT}")
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("✅ Successfully connected to Chrome!")
        except Exception as e:
            print(f"❌ Connection Failed! Error: {e}")
            return

        if not os.path.exists(NUMBERS_FILE):
            print(f"❌ Error: {NUMBERS_FILE} not found!")
            return

        with open(NUMBERS_FILE, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]

        for num in numbers:
            clean_num = "60" + num[1:] if num.startswith("0") else num
            url = f"https://web.whatsapp.com/send?phone={clean_num}"
            print(f"\n🚀 Processing {clean_num}...")

            try:
                await page.goto(url)

                # Wait for the main chat panel OR the Invalid Number popup
                print("⏳ Waiting for chat to load...")
                await page.wait_for_selector('div#main, div[role="button"]:has-text("OK")', timeout=45000)

                invalid_number_btn = page.locator('div[role="button"]:has-text("OK")')
                if await invalid_number_btn.is_visible():
                    print(f"⏭️ Skipped {clean_num}: Number not registered on WhatsApp.")
                    await invalid_number_btn.click()
                    continue

                await asyncio.sleep(1)

                # Focus the main typing box
                print("⌨️ Focusing the main chat box...")
                main_text_box = page.locator('div#main div[contenteditable="true"][role="textbox"]').first
                await main_text_box.wait_for(state="visible", timeout=10000)
                await main_text_box.focus()
                await asyncio.sleep(0.5)

                # --- STEP 1: PASTE THE FIRST TEXT ---
                print("📝 Pasting first text...")
                # insert_text is instant, just like hitting Ctrl+V with text!
                await page.keyboard.insert_text(MESSAGE)
                await asyncio.sleep(0.5)

                # --- STEP 2: PASTE THE IMAGE ---
                print("📋 Copying image to clipboard right before pasting...")
                # MOVED THIS HERE: Copy the image to clipboard immediately before pressing Ctrl+V
                copy_image_to_clipboard(IMAGE_PATH)
                await asyncio.sleep(0.5) # Give PowerShell a split second to put the image on the clipboard

                print("📋 Pasting image (Ctrl+V)...")
                await page.keyboard.press("Control+V")

                # Wait for the Image Preview Modal to fully open
                print("⏳ Waiting for image preview modal...")
                send_button = page.locator('div[aria-label="Send"], span[data-icon="send"]').first
                await send_button.wait_for(state="visible", timeout=15000)
                await asyncio.sleep(1) # Brief pause to ensure the modal grabs the text as a caption

                # --- STEP 3: SEND (Image + First Text) ---
                print("🚀 Clicking Send for image...")
                await send_button.click()
                print(f"✅ Successfully sent image to {clean_num}")

                # Wait for the image upload to process and the modal to close
                await asyncio.sleep(4)

                # --- STEP 4: PASTE SECOND TEXT ---
                print("💬 Pasting second text message...")
                # Re-target and focus the main chat text box again
                await main_text_box.wait_for(state="visible", timeout=10000)
                await main_text_box.focus()
                await page.keyboard.insert_text(SECOND_MESSAGE)
                await asyncio.sleep(0.5)

                # --- STEP 5: SEND (Second Text) ---
                print("🚀 Pressing Enter to send second message...")
                await page.keyboard.press("Enter")

                print(f"✅ Successfully completed sequence for {clean_num}")

                # Give it a brief moment to dispatch over the network before changing URLs
                await asyncio.sleep(20)

            except Exception as e:
                print(f"⚠️ Failed for {clean_num}. Error details: {e}")
                await page.goto("about:blank")

        print("\n🏁 Automation complete!")

if __name__ == "__main__":
    asyncio.run(run_automation())