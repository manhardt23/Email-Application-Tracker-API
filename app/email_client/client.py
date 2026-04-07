import email
import imaplib
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any

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
                    sender = _optional_str(msg.get("From"))
                    message_id = _optional_str(msg.get("Message-ID"))
                    if not message_id:
                        uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                        print(
                            f"Skipping email {uid_str}: missing required Message-ID header"
                        )
                        continue

                    email_date = None
                    date_str = msg.get("Date")
                    if date_str:
                        try:
                            email_date = parsedate_to_datetime(date_str)
                        except Exception as e:
                            print(f"Warning: could not parse date for {uid.decode()}: {e}")

                    raw_subject = msg.get("Subject")
                    subject = _decode_subject(raw_subject)

                    body = _extract_body(msg)
                    raw_headers = dict(msg.items())

                    results.append({
                        "message_id": message_id,
                        "uid": uid.decode(),
                        "sender": sender,
                        "subject": subject,
                        "received_date": email_date,
                        "body_text": _optional_str(body),
                        "raw_headers": raw_headers or None,
                        # Backward-compat aliases; remove after service migration.
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
    """Extract clean text from email content using HTML-first parsing."""
    html_parts: list[str] = []
    plain_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type not in ("text/plain", "text/html"):
                continue
            decoded_payload = _decode_payload(part)
            if not decoded_payload:
                continue
            if content_type == "text/html":
                html_parts.append(decoded_payload)
            else:
                plain_parts.append(decoded_payload)
    else:
        content_type = msg.get_content_type()
        decoded_payload = _decode_payload(msg)
        if decoded_payload:
            if content_type == "text/html":
                html_parts.append(decoded_payload)
            else:
                plain_parts.append(decoded_payload)

    # Prefer HTML rendering when available; fallback to plaintext.
    if html_parts:
        rendered = " ".join(_html_to_text(part) for part in html_parts)
    else:
        rendered = " ".join(plain_parts)

    return _normalize_body_text(rendered)


def _decode_payload(part: Any) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="ignore")
    except (LookupError, UnicodeDecodeError):
        return payload.decode("utf-8", errors="ignore")


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()

    # Use line separators so list/table structures do not collapse into one token.
    return soup.get_text(separator="\n")


def _normalize_body_text(body: str) -> str:
    # Clean up noise
    body = re.sub(r"http\S+", "", body)
    body = re.sub(r"www\.\S+", "", body)
    body = re.sub(r"\s+", " ", body)
    body = re.sub(r"(--|__|==).*", "", body)
    body = re.sub(r"(?i)unsubscribe.*", "", body)
    return body.strip()


def _decode_subject(raw_subject: Any) -> str | None:
    if raw_subject is None:
        return None
    decoded, encoding = decode_header(raw_subject)[0]
    subject = (
        decoded.decode(encoding or "utf-8", errors="ignore")
        if isinstance(decoded, bytes)
        else str(decoded)
    )
    return _optional_str(subject)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
