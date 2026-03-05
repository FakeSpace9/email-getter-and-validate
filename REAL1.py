import asyncio
import re
import smtplib
import socket
import time
import dns.resolver
from urllib.parse import urlparse
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
START_PAGE = 1675
END_PAGE = 1700
VALID_FILE = "valid_emails.txt"      # Good emails
INVALID_FILE = "invalid_emails.txt"  # Bad emails
UNCHECKED_FILE = "collected_emails.txt" # History of all found

# --- VALIDATOR ---
def validate_smtp(email):
    """
    Checks MX records and attempts to connect to the mail server.
    """
    if not email or "@" not in email: return False, "Bad Format"
    domain = email.split('@')[1]
    try:
        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_record = str(records[0].exchange)
        except:
            return False, "No MX Record"

        server = smtplib.SMTP(timeout=5)
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

# --- HELPER (FIXED) ---
IGNORE_PATHS = [
    "/services", "/buysell", "/jobs", "/hireme", "/education", "/home",
    "/login", "/register", "/about", "/contact", "/privacy", "/terms",
    "/faq", "/financing", "/useful-hotlines", "/articles", "/pages"
]

def is_valid_business_link(url):
    """Smarter filter: Excludes menu links but keeps all business slugs."""
    if not url or "yellowpages.my" not in url or "page=" in url:
        return False

    try:
        # Get just the path part of the URL (e.g., /chow-chui-mei)
        path = urlparse(url).path.lower()

        # If path is just "/" or empty, skip
        if not path or path == "/": return False

        # If it's a known menu link, skip
        for bad in IGNORE_PATHS:
            if path.startswith(bad):
                return False

        # If path is extremely short (e.g., /l), skip
        if len(path) < 4:
            return False

        return True
    except:
        return False

# --- MAIN AUTOMATION ---
async def scrape_and_validate():
    async with async_playwright() as p:
        print("🔗 Connecting to Chrome...")
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            main_page = context.pages[0]
        except Exception as e:
            print(f"❌ Connection Failed! Error: {e}")
            return

        print(f"✅ Connected! Processing pages {START_PAGE} to {END_PAGE}...")

        # Load history to skip duplicates across runs
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

            # --- PART A: NAVIGATE & COLLECT LINKS ---
            try:
                if f"page={i}" not in main_page.url:
                    await main_page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # FIX: Scroll down to ensure business cards load completely
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                await asyncio.sleep(2)
                await main_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
            except:
                print(f"   ⚠️ Timeout loading list. Skipping page.")
                continue

            try:
                raw_links = await main_page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
                business_links = list(set([link for link in raw_links if is_valid_business_link(link)]))
                print(f"   Found {len(business_links)} businesses. Collecting emails...")
            except:
                continue

            # --- PART B: SCRAPE ALL BUSINESSES (BATCH COLLECTION) ---
            emails_to_validate = set()

            for index, link in enumerate(business_links):
                try:
                    page = await context.new_page()
                    await page.goto(link, wait_until="domcontentloaded", timeout=10000)

                    # Scroll & Read
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(0.5)

                    content = await page.content()
                    visible_text = await page.inner_text("body")

                    # Extract
                    found = set()
                    mailto = await page.evaluate("""() => Array.from(document.querySelectorAll('a[href^="mailto:"]')).map(a => a.getAttribute('href'))""")
                    for m in mailto:
                        if m: found.add(m.replace("mailto:", "").split("?")[0].strip())

                    for email in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content + visible_text):
                        if not email.lower().endswith(('png','jpg','gif','js','css','svg','webp')):
                            found.add(email)

                    # Add to batch list
                    count_new = 0
                    for email in found:
                        if email not in processed_emails:
                            emails_to_validate.add(email)
                            count_new += 1

                    # Optional: Print progress dots
                    print(f".", end="", flush=True)

                    await page.close()
                except:
                    if not page.is_closed(): await page.close()
                    continue

            print(f"\n   -> Scrape Complete. Found {len(emails_to_validate)} unique new emails.")

            # --- PART C: BATCH VALIDATION ---
            if len(emails_to_validate) > 0:
                print(f"   ⚙️ Validating batch now...")

                for email in emails_to_validate:
                    print(f"      Checking {email}...", end=" ", flush=True)
                    is_valid, reason = validate_smtp(email)

                    # Mark processed
                    processed_emails.add(email)
                    with open(UNCHECKED_FILE, "a") as f: f.write(email + "\n")

                    if is_valid:
                        print(f"✅ VALID")
                        with open(VALID_FILE, "a") as f: f.write(email + "\n")
                    else:
                        print(f"❌ INVALID ({reason})")
                        with open(INVALID_FILE, "a") as f: f.write(f"{email} | {reason}\n")

                    # Tiny sleep to respect SMTP servers
                    time.sleep(0.5)
            else:
                print("   ⚠️ No new emails found on this page.")

            print(f"   ✅ Page {i} Fully Complete. Moving to next...")

if __name__ == "__main__":
    asyncio.run(scrape_and_validate())