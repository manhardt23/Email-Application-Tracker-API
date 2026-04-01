import email
import imaplib
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from app.config import get_settings


def _connect_to_inbox():
    settings = get_settings()
    mail = imaplib.IMAP4_SSL(settings.imap_server)
    mail.login(settings.email_user, settings.email_pass)
    mail.select("inbox")
    return mail


def fetch_recent_emails(limit: int) -> list[dict]:
    mail = None
    try:
        mail = _connect_to_inbox()
        status, data = mail.uid("search", None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        if not data or not data[0]:
            print("No emails found in inbox")
            return []

        mail_uids = data[0].split()
        recent_uids = mail_uids[-limit:] if len(mail_uids) > limit else mail_uids

        results = []
        for uid in recent_uids:
            try:
                status, msg_data = mail.uid("fetch", uid, "(RFC822)")
                if status != "OK":
                    print(f"Warning: failed to fetch {uid.decode()}")
                    continue

                for part in msg_data:
                    if not isinstance(part, tuple):
                        continue

                    msg = email.message_from_bytes(part[1])
                    sender = msg.get("From", "")
                    message_id = msg.get("Message-ID")

                    email_date = None
                    date_str = msg.get("Date")
                    if date_str:
                        try:
                            email_date = parsedate_to_datetime(date_str)
                        except Exception as e:
                            print(f"Warning: could not parse date for {uid.decode()}: {e}")

                    raw_subject = msg.get("Subject", "")
                    decoded, encoding = decode_header(raw_subject)[0]
                    subject = (
                        decoded.decode(encoding or "utf-8", errors="ignore")
                        if isinstance(decoded, bytes)
                        else decoded
                    )

                    body = _extract_body(msg)

                    results.append({
                        "message_id": message_id,
                        "uid": uid.decode(),
                        "sender": sender,
                        "subject": subject,
                        "body": body,
                        "date": email_date,
                    })
            except Exception as e:
                uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                print(f"Error processing email {uid_str}: {e}")
                continue

        return results
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception as e:
                print(f"Warning: error closing IMAP connection: {e}")


def _extract_body(msg) -> str:
    """Extract and clean plain text from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode("utf-8", errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")

    # Strip HTML markup to plain text
    body = BeautifulSoup(body, "html.parser").get_text()

    # Clean up noise
    body = re.sub(r"http\S+", "", body)
    body = re.sub(r"www\.\S+", "", body)
    body = re.sub(r"\s+", " ", body)
    body = re.sub(r"(--|__|==).*", "", body)
    body = re.sub(r"(?i)unsubscribe.*", "", body)
    return body.strip()
