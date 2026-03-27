import asyncio
import re
import smtplib
import socket
import time
import dns.resolver
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
START_PAGE = 551
END_PAGE = 600
VALID_FILE = "valid_emails.txt"
INVALID_FILE = "invalid_emails.txt"
UNCHECKED_FILE = "collected_emails.txt"

# --- VALIDATOR ---
def validate_smtp(email):
    if not email or "@" not in email: return False, "Bad Format"
    domain = email.split('@')[1]
    try:
        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_record = str(records[0].exchange)
        except:
            return False, "No MX Record"

        server = smtplib.SMTP(timeout=7) # Increased timeout slightly
        server.set_debuglevel(0)
        try:
            server.connect(mx_record)
        except:
            return False, "Connect Timeout"

        server.helo(socket.gethostname())
        server.mail("verify@test.com")
        code, message = server.rcpt(email)
        server.quit()

        if code == 250: return True, "OK"
        elif code == 550: return False, "User Unknown"
        else: return True, f"Server Uncertain ({code})"
    except Exception as e:
        return False, f"Error: {str(e)[:20]}"

# --- HELPER ---
IGNORE_PATHS = [
    "/services", "/buysell", "/jobs", "/hireme", "/education", "/home",
    "/login", "/register", "/about", "/contact", "/privacy", "/terms",
    "/faq", "/financing", "/useful-hotlines", "/articles", "/pages"
]

def is_valid_business_link(url):
    if not url or "yellowpages.my" not in url or "page=" in url:
        return False
    try:
        path = urlparse(url).path.lower()
        if not path or path == "/": return False
        for bad in IGNORE_PATHS:
            if path.startswith(bad): return False
        if len(path) < 4: return False
        return True
    except:
        return False

# --- MAIN AUTOMATION ---
async def scrape_and_validate():
    async with async_playwright() as p:
        print("🔗 Connecting to Chrome...")
        try:
            # Note: Ensure Chrome is open with --remote-debugging-port=9222
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            main_page = context.pages[0]
        except Exception as e:
            print(f"❌ Connection Failed! Make sure Chrome is running in debug mode. Error: {e}")
            return

        print(f"✅ Connected! Processing pages {START_PAGE} to {END_PAGE}...")

        # Load history
        processed_emails = set()
        try:
            with open(UNCHECKED_FILE, "r") as f:
                processed_emails = set(line.strip() for line in f)
        except FileNotFoundError:
            pass

        for i in range(START_PAGE, END_PAGE + 1):
            url = f"https://www.yellowpages.my/services/l?page={i}"
            print(f"\n" + "="*50)
            print(f"🔎 STEP 1: Processing Page {i}")
            print("="*50)

            try:
                await main_page.goto(url, wait_until="networkidle", timeout=60000)
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                await asyncio.sleep(2)
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"   ⚠️ Timeout or error loading list page: {e}")
                continue

            raw_links = await main_page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
            business_links = list(set([link for link in raw_links if is_valid_business_link(link)]))
            print(f"   Found {len(business_links)} businesses. Scraping details...")

            emails_to_validate = set()

            for link in business_links:
                page = None
                try:
                    page = await context.new_page()
                    # We use networkidle to ensure dynamic email sections load
                    response = await page.goto(link, wait_until="networkidle", timeout=20000)

                    if response.status != 200:
                        print(f"!", end="", flush=True) # Indicate a non-200 status
                        await page.close()
                        continue

                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

                    content = await page.content()

                    # Method 1: Mailto links
                    mailto = await page.evaluate("""() => Array.from(document.querySelectorAll('a[href^="mailto:"]')).map(a => a.getAttribute('href'))""")
                    found = set()
                    for m in mailto:
                        if m: found.add(m.replace("mailto:", "").split("?")[0].strip().lower())

                    # Method 2: Regex on full content
                    raw_extracted = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                    for email in raw_extracted:
                        clean_email = email.lower()
                        if not clean_email.endswith(('png','jpg','gif','js','css','svg','webp','jpeg')):
                            found.add(clean_email)

                    for email in found:
                        if email not in processed_emails:
                            emails_to_validate.add(email)

                    print(f".", end="", flush=True)
                    await page.close()
                except:
                    if page: await page.close()
                    print(f"x", end="", flush=True)
                    continue

            print(f"\n   -> Scrape Complete. Found {len(emails_to_validate)} NEW emails.")

            # --- PART C: VALIDATION ---
            if emails_to_validate:
                print(f"   ⚙️ Validating batch...")
                for email in emails_to_validate:
                    # Immediately add to processed so we don't try again next run
                    processed_emails.add(email)
                    with open(UNCHECKED_FILE, "a") as f: f.write(email + "\n")

                    is_valid, reason = validate_smtp(email)
                    if is_valid:
                        print(f"      ✅ {email}")
                        with open(VALID_FILE, "a") as f: f.write(email + "\n")
                    else:
                        print(f"      ❌ {email} ({reason})")
                        with open(INVALID_FILE, "a") as f: f.write(f"{email} | {reason}\n")

                    await asyncio.sleep(0.5)
            else:
                print("   ⚠️ No new emails found on this page (or all already processed).")

if __name__ == "__main__":
    try:
        asyncio.run(scrape_and_validate())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")