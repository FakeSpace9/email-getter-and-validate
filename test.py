from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re

def scrape_yellowpages(url, output_file):
    print(f"Starting scraper for {url}...")
    
    with sync_playwright() as p:
        # 1. Launch Browser with manual stealth arguments
        browser = p.chromium.launch(
            headless=False,  # Visible browser is safer for avoiding blocks
            args=[
                "--disable-blink-features=AutomationControlled", # Hides the 'robot' flag
                "--no-sandbox"
            ]
        )
        
        # 2. Configure Context (User Agent + Viewport)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="Asia/Kuala_Lumpur"
        )
        
        # 3. Create Page and Inject Stealth Javascript
        page = context.new_page()
        
        # This script removes the 'navigator.webdriver' property that identifies bots
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        try:
            print(f"Navigating to listing page...")
            page.goto(url, timeout=90000)

            # Wait for content (Logo or Listings)
            try:
                # Wait for the listing container specifically
                page.wait_for_selector('app-expended-normal-listing', timeout=20000)
                print(" -> Page loaded successfully!")
            except:
                print(" -> Timeout waiting for content. Cloudflare might have blocked us.")
                # Save screenshot to debug if needed
                page.screenshot(path="debug_blocked.png") 

            # Lazy load scrolling
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(1)

            # Get Content
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            listings = soup.find_all('app-expended-normal-listing')

            if not listings:
                print("No listings found on main page.")
                return

            items_to_process = []
            for item in listings:
                # Extract Name
                name_tag = item.select_one('.title')
                name = name_tag.text.strip() if name_tag else "N/A"
                
                # Extract URL
                href = name_tag.get('href') if name_tag else None
                if href and not href.startswith('http'):
                    href = "https://www.yellowpages.my" + href

                # Extract Address
                address_tag = item.select_one('.company_location')
                address = address_tag.text.strip().replace('\n', ' ') if address_tag else "N/A"

                # Extract Phone
                phone_tag = item.select_one('.phone-number a')
                phone = phone_tag.get('href').replace('tel:', '') if phone_tag else "N/A"

                items_to_process.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "url": href
                })

            print(f"Found {len(items_to_process)} listings. Processing details...", flush=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                for idx, item in enumerate(items_to_process):
                    email = "Not listed"
                    
                    if item['url']:
                        try:
                            print(f"[{idx+1}/{len(items_to_process)}] Checking {item['name']}...", flush=True)
                            page.goto(item['url'], timeout=60000)
                            
                            # Wait slightly for JS to populate
                            time.sleep(2) 

                            # Get page content for Regex search
                            detail_content = page.content()
                            
                            # 1. Regex Search (Finds hidden emails in scripts/text)
                            emails_found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', detail_content)
                            
                            # Filter junk emails
                            valid_emails = [e for e in emails_found if 'yellowpages.my' not in e and 'w3.org' not in e and '.png' not in e]
                            
                            if valid_emails:
                                email = valid_emails[0]
                                print(f"  -> Found: {email}")
                            else:
                                print("  -> No email.")

                        except Exception as e:
                            print(f"  -> Error: {e}")
                    
                    # Write to file
                    f.write(f"Name: {item['name']}\nAddress: {item['address']}\nPhone: {item['phone']}\nEmail: {email}\n" + "-"*30 + "\n")
                    f.flush()

            print(f"Done! Saved to {output_file}")

        except Exception as e:
            print(f"Critical Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    target_url = "https://www.yellowpages.my/services/l?where=Kuala%20Lumpur"
    scrape_yellowpages(target_url, "business_info.txt")