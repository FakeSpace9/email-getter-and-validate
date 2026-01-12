from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import re
import smtplib
import dns.resolver
import socket

def validate_email_smtp(email):
    """
    Returns:
    - True:  Email exists OR we couldn't check (Soft Pass).
    - False: Email definitely does not exist (Hard Bounce).
    """
    if not email or "@" not in email:
        return False

    domain = email.split('@')[1]
    
    try:
        # 1. DNS Check (Does the website/domain exist?)
        # If this fails, the email is definitely fake.
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)
        
        # 2. Try SMTP Connection
        server = smtplib.SMTP(timeout=3) # Short timeout
        server.set_debuglevel(0) 
        
        # Use local hostname for politeness
        local_host = socket.gethostname()
        
        # Try to connect
        server.connect(mx_record)
        server.helo(local_host)
        server.mail(f"verify@{domain}")
        code, message = server.rcpt(email)
        server.quit()

        # 250 = OK (User exists)
        if code == 250:
            return True
        # 550 = User Unknown (The ONLY time we should say False)
        elif code == 550:
            print(f"    [x] Hard Bounce (550): User unknown")
            return False
        else:
            # Any other code (greylisting, etc) -> Assume Valid
            return True

    except (socket.timeout, socket.error, smtplib.SMTPServerDisconnected):
        # This is where your ISP block lands.
        # We couldn't reach the server, so we give it the benefit of the doubt.
        print(f"    [!] Connection Blocked/Timeout (ISP limitation). Assuming Valid.")
        return True
        
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        # Domain doesn't exist at all -> Fake
        print(f"    [x] Domain '{domain}' does not exist.")
        return False
        
    except Exception as e:
        # Any other weird error -> Keep the email just in case
        print(f"    [!] Unknown error: {e}. Assuming Valid.")
        return True
# --- Scraper Function ---
def scrape_yellowpages(url, output_file, valid_email_file):
    print(f"Starting scraper for {url}...")
    
    with sync_playwright() as p:
        # Launch Browser
        browser = p.chromium.launch(
            headless=False, 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        try:
            print(f"Navigating to listing page...")
            page.goto(url, timeout=90000)

            # Wait for content
            try:
                page.wait_for_selector('app-expended-normal-listing', timeout=20000)
                print(" -> Page loaded successfully!")
            except:
                print(" -> Timeout. Cloudflare might have blocked us.")
                return

            # Scroll
            for _ in range(3):
                page.mouse.wheel(0, 1000)
                time.sleep(1)

            # Extract Listings
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            listings = soup.find_all('app-expended-normal-listing')

            if not listings:
                print("No listings found on main page.")
                return

            items_to_process = []
            for item in listings:
                name_tag = item.select_one('.title')
                name = name_tag.text.strip() if name_tag else "N/A"
                
                href = name_tag.get('href') if name_tag else None
                if href and not href.startswith('http'):
                    href = "https://www.yellowpages.my" + href

                address_tag = item.select_one('.company_location')
                address = address_tag.text.strip().replace('\n', ' ') if address_tag else "N/A"

                phone_tag = item.select_one('.phone-number a')
                phone = phone_tag.get('href').replace('tel:', '') if phone_tag else "N/A"

                items_to_process.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "url": href
                })

            print(f"Found {len(items_to_process)} listings. Processing details...", flush=True)

            # Open Main Output File
            with open(output_file, 'a', encoding='utf-8') as f:
                # Open Valid Email File
                with open(valid_email_file, 'a', encoding='utf-8') as f_valid:
                    
                    for idx, item in enumerate(items_to_process):
                        email = "Not listed"
                        validation_status = "Skipped"

                        if item['url']:
                            try:
                                print(f"[{idx+1}/{len(items_to_process)}] Checking {item['name']}...", flush=True)
                                page.goto(item['url'], timeout=60000)
                                time.sleep(2) 

                                detail_content = page.content()
                                
                                # Regex Search
                                emails_found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', detail_content)
                                valid_emails_list = [e for e in emails_found if 'yellowpages.my' not in e and 'w3.org' not in e and '.png' not in e]
                                
                                if valid_emails_list:
                                    email = valid_emails_list[0]
                                    print(f"  -> Found: {email}")
                                    
                                    # --- VALIDATION STEP ---
                                    print("  -> Validating SMTP...")
                                    if validate_email_smtp(email):
                                        validation_status = "VALID"
                                        print("  -> Result: REACHABLE ✅")
                                        
                                        # Save to the special "Reachable" file
                                        f_valid.write(f"{email}\n")
                                        f_valid.flush()
                                    else:
                                        validation_status = "INVALID/UNREACHABLE"
                                        print("  -> Result: Unreachable ❌")
                                else:
                                    print("  -> No email.")

                            except Exception as e:
                                print(f"  -> Error: {e}")
                        
                        # Write to main file
                        f.write(f"Name: {item['name']}\nAddress: {item['address']}\nPhone: {item['phone']}\nEmail: {email}\nStatus: {validation_status}\n" + "-"*30 + "\n")
                        f.flush()

            print(f"Done! Saved to {output_file}")

        except Exception as e:
            print(f"Critical Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # Define Files
    main_file = "business_info.txt"
    valid_file = "reachable_emails.txt"

    # Clear valid file at start (Optional - comment out if you want to keep history)
    with open(valid_file, 'a', encoding='utf-8') as vf:
        vf.write("--- Valid Reachable Emails ---\n")

    base_url = "https://www.yellowpages.my/services/l?where=Kuala%20Lumpur&page="
    target_urls = [f"{base_url}{i}" for i in range(2, 6)] # Test with pages 2 to 5 first

    for url in target_urls:
        scrape_yellowpages(url, main_file, valid_file)
        time.sleep(3) # Rest between pages