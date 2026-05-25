AUTOMATION SCRIPTS: INTERN HANDOVER GUIDE



Welcome! This folder contains the Python automation scripts used to streamline our business outreach. 

##IMPORTANT BEFORE EVERYTHING, DO NOT TELL RACHEL U USE THIS CODE TO COLLECT EMAIL OR LET RACHEL KNOW U USE THIS WEBSITE

There are two main scripts here:

1\. Email Collection \& Validation (Email.py): Automatically navigates public business listings to gather contact emails and verifies their deliverability via SMTP checks.

2\. WhatsApp Bulk Sender (whatsapp.py): Automates sending promotional images and text sequences to a list of phone numbers via WhatsApp Web.



\----------------------------------------------------------------------

PHASE 1: PREREQUISITES \& INSTALLATION

\----------------------------------------------------------------------

Before running any code, you must set up your environment. These scripts rely on browser automation to work properly.



1\. System Requirements:

&#x20;  - Operating System: Windows (Required for the clipboard integration used in the WhatsApp script).

&#x20;  - Browser: Google Chrome must be installed.

&#x20;  - Python: Python 3.7 or higher installed on your machine.



2\. Install Required Packages:

&#x20;  Open your Command Prompt or PowerShell and run the following commands sequentially to install the necessary libraries and browser binaries:



&#x20;  pip install playwright dnspython



&#x20;  playwright install chromium





\----------------------------------------------------------------------

PHASE 2: STARTING GOOGLE CHROME (CRUCIAL STEP)

\----------------------------------------------------------------------

These scripts do not open a new browser window themselves. Instead, they take control of an \*already running\* Google Chrome window configured in "Remote Debugging" mode. This allows the scripts to run while keeping you logged into necessary web accounts.



You MUST open Windows PowerShell and run the appropriate command below BEFORE running the Python scripts.



To Run Email Collection (Email.py):

Open PowerShell and run this command. It will open a Chrome instance on Port 9222:

\& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\chrome\_debug"



To Run WhatsApp Automation (whatsapp.py):

Open PowerShell and run this command. It will open a Chrome instance on Port 9333:

\& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9333 --user-data-dir="C:\\chrome\_whatsapp"



(Note: Once this specific Chrome window opens, manually navigate to web.whatsapp.com and scan the QR code with a phone to log in before running the script).





\----------------------------------------------------------------------

PHASE 3: RUNNING THE SCRIPTS

\----------------------------------------------------------------------



1\. Email Collection (Email.py)

This script safely extracts business emails from public directories and checks if the inboxes actually exist to prevent bounced emails.



\- Preparation: Ensure Chrome is running on Port 9222.

\- Run: Open Command Prompt/PowerShell in this folder and type:

&#x20; python Email.py



\- Output: The script will automatically generate and update three text files in the folder:

&#x20; \* collected\_emails.txt: A master list of everything found.

&#x20; \* valid\_emails.txt: Safe-to-use emails that passed the server check.

&#x20; \* invalid\_emails.txt: Badly formatted or bounced emails.





2\. WhatsApp Bulk Sender (whatsapp.py)

This script sends a structured sequence (an image followed by a text message) to a list of clients.



\- Preparation: 

&#x20; A) Ensure Chrome is running on Port 9333 and WhatsApp Web is logged in.

&#x20; B) Create a file named contacts.txt in the same folder. Add the target phone numbers (one per line).

&#x20; C) Open whatsapp.py in a code editor (like Notepad or VS Code) and verify that the IMAGE\_PATH variable at the top points to the exact location of the promotional image on your current PC.



\- Run: Open Command Prompt/PowerShell in this folder and type:

&#x20; python whatsapp.py

