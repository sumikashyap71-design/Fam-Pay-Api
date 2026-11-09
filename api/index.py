from http.server import BaseHTTPRequestHandler
import urllib.parse
import json
import imaplib
import email
import re
from datetime import datetime, timedelta
import os

# ========== CONFIG ==========
GMAIL_USER = os.getenv("GMAIL_USER", "sumiikashyap16@gmail.com")
GMAIL_PASS = os.getenv("GMAIL_PASS", "amwdiintzotwusvo")
API_KEY = os.getenv("API_KEY", "FAMAPPAPI")
# ============================

def check_fampay(amount, utr_input):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select('"[Gmail]/All Mail"')
        
        date = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{date}")')

        if status != "OK" or not messages[0]:
            mail.logout()
            return False, "No recent emails found"

        for num in reversed(messages[0].split()):
            status, data = mail.fetch(num, "(RFC822)")
            if status != "OK": continue

            msg = email.message_from_bytes(data[0][1])
            subject = str(msg.get("Subject", "")).lower()
            sender = str(msg.get("From", "")).lower()

            if "famapp" in sender or "fam" in sender:
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(errors="ignore") + "\n"
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                # Amount check
                amount_str = str(float(amount)).replace(".0", "")
                amount_pattern = rf'(?:₹|Rs\.?|INR)?\s*{re.escape(amount_str)}(?:\.0+)?\b'

                if re.search(amount_pattern, body, re.IGNORECASE):
                    if str(utr_input) in body:
                        mail.logout()
                        return True, "Payment verified"
        
        mail.logout()
        return False, "Payment not found or amount mismatch"
    except Exception as e:
        return False, str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)

        # CORS Headers (Har jagah se access ke liye)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        if parsed_path.path != '/api':
            self.wfile.write(json.dumps({"error": "Use /api route"}).encode())
            return

        api_key = query.get('api_key', [None])[0]
        utr = query.get('utr', [None])[0]
        amount = query.get('amount', [None])[0]

        if api_key != API_KEY:
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid API Key"}).encode())
            return

        if not utr or not amount:
            self.wfile.write(json.dumps({"status": "error", "message": "UTR and Amount required"}).encode())
            return

        success, message = check_fampay(float(amount), utr)

        if success:
            self.wfile.write(json.dumps({
                "status": "success",
                "message": "Payment verified",
                "utr": utr,
                "amount": amount
            }).encode())
        else:
            self.wfile.write(json.dumps({
                "status": "error",
                "message": message
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
