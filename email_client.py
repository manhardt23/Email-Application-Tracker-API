import imaplib
import email
import re
from bs4 import BeautifulSoup
from email.header import decode_header
from email.utils import parsedate_to_datetime
from config import EMAIL_USER, EMAIL_PASS, IMAP_SERVER

def connect_to_inbox():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    return mail



def fetch_recent_emails(limit):
    mail = None
    try:
        mail = connect_to_inbox()
        status, data = mail.uid('search', None, "ALL")
        if status != 'OK':
            raise Exception(f"Failed to search emails: {status}")
        
        if not data or not data[0]:
            print("No emails found in inbox")
            return []
        
        mail_uids = data[0].split()
        recent_uids = mail_uids[-limit:] if len(mail_uids) > limit else mail_uids

        emails = []
        for uid in recent_uids:
            try:
                status, msg_data = mail.uid('fetch', uid, "(RFC822)")
                if status != 'OK':
                    print(f"Warning: Failed to fetch email {uid.decode()}")
                    continue
                    
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        # --- Extract Sender ---
                        sender = msg.get("From", "")
                        # --- Extract Date ---
                        date_str = msg["Date"]
                        email_date = None
                        if date_str:
                            try:
                                email_date = parsedate_to_datetime(date_str)
                            except Exception as e:
                                print(f"Warning: Failed to parse date for email {uid.decode()}: {e}")

                        # --- Extract Subject (decode if encoded) ---
                        raw_subject = msg.get("Subject", "")
                        subject, encoding = decode_header(raw_subject)[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8", errors="ignore")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                if ctype in ["text/plain", "text/html"]:
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        text = payload.decode("utf-8", errors="ignore")
                                        body += text
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                body = payload.decode("utf-8", errors="ignore")

                        # --- Convert HTML → text (remove markup) ---
                        body = BeautifulSoup(body, "html.parser").get_text()

                        # --- Clean up unwanted junk ---
                        body = re.sub(r"http\S+", "", body)           # remove links
                        body = re.sub(r"www\.\S+", "", body)          # remove www links
                        body = re.sub(r"\s+", " ", body)              # normalize whitespace
                        body = re.sub(r"(--|__|==).*", "", body)      # cut off signatures
                        body = re.sub(r"(?i)unsubscribe.*", "", body) # remove unsubscribe lines
                        body = body.strip()

                        
                        emails.append({
                            "uid": uid.decode(),
                            "sender": sender,
                            "subject": subject,
                            "body": body,
                            "date" : email_date
                        })
            except Exception as e:
                print(f"Error processing email {uid.decode() if isinstance(uid, bytes) else uid}: {e}")
                continue
        return emails
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception as e:
                print(f"Warning: Error closing IMAP connection: {e}")