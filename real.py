import smtplib
import dns.resolver
import socket
import time

# --- CONFIGURATION ---
INPUT_FILE = "test.txt"          # Your list of emails
OUTPUT_VALID = "reachable.txt"     # Where to save good emails
OUTPUT_INVALID = "unreachable.txt" # Where to save bad emails

# SET TO 'False' if you are getting too many "User Unknown" errors on valid emails
STRICT_CHECK = True

def validate_smtp(email):
    """
    Validates an email using SMTP.
    Returns: (Boolean Is_Valid, String Reason)
    """
    if not email or "@" not in email:
        return False, "Bad Format"

    domain = email.split('@')[1]

    try:
        # 1. DNS Lookup (Get Mail Server)
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(records[0].exchange)

        # If we are in 'Lazy Mode', passing DNS check is enough
        if not STRICT_CHECK:
            return True, "Domain exists (Strict check skipped)"

        # 2. Connect to Server
        server = smtplib.SMTP(timeout=5)
        server.set_debuglevel(0)

        # Connect
        server.connect(mx_record)

        # Identification (Polite behavior)
        local_host = socket.gethostname()
        server.helo(local_host)

        # Sender (Use a generic verification address to look less suspicious)
        server.mail(f"verify@{domain}")

        # 3. Verify Recipient (The crucial check)
        code, message = server.rcpt(email)
        server.quit()

        # Code 250 = User Exists / OK
        if code == 250:
            return True, "OK (250)"

        # Code 550 = User Unknown (Hard Bounce)
        elif code == 550:
            return False, "User Unknown (550)"

        # Code 450/451/452 = Server busy/Greylisting (Assume valid to be safe)
        else:
            return True, f"Server Uncertain ({code}) - Assuming Valid"

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False, "Domain does not exist"
    except (socket.timeout, socket.error):
        # If ISP blocks connection, we assume valid so we don't lose the email
        return True, "Connection Blocked (ISP) - Assuming Valid"
    except Exception as e:
        return True, f"Unknown Error ({str(e)[:20]}) - Assuming Valid"

def process_email_list():
    print(f"Reading from {INPUT_FILE}...")

    # Open files
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f_in, \
                open(OUTPUT_VALID, 'w', encoding='utf-8') as f_out, \
                open(OUTPUT_INVALID, 'w', encoding='utf-8') as f_bad:

            emails = [line.strip() for line in f_in if line.strip()]
            total = len(emails)

            print(f"Found {total} emails. Mode: {'STRICT (User Check)' if STRICT_CHECK else 'LAZY (Domain Check)'}")
            print("-" * 50)

            for i, email in enumerate(emails):
                print(f"[{i+1}/{total}] Checking {email}...", end=" ", flush=True)

                is_valid, reason = validate_smtp(email)

                if is_valid:
                    print(f"VALID ({reason})")
                    f_out.write(f"{email}\n")
                else:
                    print(f"INVALID ({reason})")
                    f_bad.write(f"{email} | {reason}\n")

                # Sleep slightly to avoid looking like a DDOS attack
                time.sleep(1)

        print("-" * 50)
        print("Done!")
        print(f"Valid emails saved to: {OUTPUT_VALID}")
        print(f"Invalid emails saved to: {OUTPUT_INVALID}")

    except FileNotFoundError:
        print(f"Error: Could not find '{INPUT_FILE}'. Please create it first.")

if __name__ == "__main__":
    process_email_list()