import imaplib
import email
import re
from bs4 import BeautifulSoup
from email.header import decode_header
from email.utils import parsedate_to_datetime

from bleach import clean
from config import EMAIL_USER, EMAIL_PASS, IMAP_SERVER

def connect_to_inbox():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    return mail



def fetch_recent_emails(limit=5):
    mail = connect_to_inbox()
    status, data = mail.uid('search', None, "ALL")
    mail_uids = data[0].split()
    recent_uids = mail_uids[-limit:]

    emails = []
    for uid in recent_uids:
        status, msg_data = mail.uid('fetch', uid, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                # --- Extract Sender ---
                sender = msg.get("From", "")
                # --- Extract Date ---
                date_str = msg["Date"]
                email_date = None
                if date_str:
                    email_date = parsedate_to_datetime(date_str)

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

                # --- Limit to preview length ---
                preview = body[:500] + ("..." if len(body) > 500 else "")
                emails.append({
                    "uid": uid.decode(),
                    "sender": sender,
                    "subject": subject,
                    "body": body,
                    "date" : email_date
                })
    return emails