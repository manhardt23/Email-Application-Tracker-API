import email
import imaplib
import logging
import re
import socket
import time
from datetime import UTC, datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any

from bs4 import BeautifulSoup

from app.config import get_settings

logger = logging.getLogger(__name__)

# Errors that are worth retrying once (network blip, server reset, timeout).
# imaplib.IMAP4.abort is raised on broken connections; OSError/socket.timeout
# cover TCP-level failures. imaplib.IMAP4.error is a permanent protocol error
# (bad credentials, mailbox not found) — do NOT retry those.
_TRANSIENT_IMAP_ERRORS = (imaplib.IMAP4.abort, OSError, socket.timeout, TimeoutError)

# Single retry with a short back-off — keeps cron jobs fast while surviving
# transient server resets (Comcast IMAP is occasionally flaky).
_CONNECT_RETRY_DELAY_SECONDS = 2
_CONNECT_MAX_ATTEMPTS = 2


def _connect_to_inbox(timeout: int | None = None):
    settings = get_settings()
    imap_timeout = timeout if timeout is not None else getattr(settings, "imap_timeout_seconds", 30)
    mail = imaplib.IMAP4_SSL(settings.imap_server, timeout=imap_timeout)
    try:
        mail.login(settings.email_user, settings.email_pass)
        mail.select("inbox")
    except Exception:
        _close_mail(mail)
        raise
    return mail


def fetch_recent_emails(limit: int, since_uid: int = 1) -> list[dict]:
    """Fetch up to *limit* most-recent emails from the inbox.

    Retries the connect+search phase once on transient network errors. Per-message
    fetch errors are logged and skipped without aborting the whole run (no log spam).
    """
    mail = None

    for attempt in range(1, _CONNECT_MAX_ATTEMPTS + 1):
        try:
            mail = _connect_to_inbox()
            start_uid = max(1, since_uid)
            status, data = mail.uid("search", None, f"UID {start_uid}:*")
            if status != "OK":
                _close_mail(mail)
                mail = None
                raise RuntimeError(f"IMAP search failed: {status}")
            break
        except _TRANSIENT_IMAP_ERRORS as exc:
            _close_mail(mail)
            mail = None
            if attempt < _CONNECT_MAX_ATTEMPTS:
                logger.warning(
                    "Transient IMAP error on attempt %d/%d: %s — retrying in %ds",
                    attempt,
                    _CONNECT_MAX_ATTEMPTS,
                    exc,
                    _CONNECT_RETRY_DELAY_SECONDS,
                )
                time.sleep(_CONNECT_RETRY_DELAY_SECONDS)
            else:
                logger.error(
                    "IMAP connection failed after %d attempts: %s", _CONNECT_MAX_ATTEMPTS, exc
                )
                raise
        except imaplib.IMAP4.error as exc:
            # Permanent error (auth failure, bad mailbox) — fail fast, no retry.
            logger.error("Permanent IMAP error: %s", exc)
            _close_mail(mail)
            raise

    try:
        if not data or not data[0]:
            logger.info("No emails found in inbox")
            return []

        mail_uids = data[0].split()
        recent_uids = (
            list(reversed(mail_uids[-limit:]))
            if len(mail_uids) > limit
            else list(reversed(mail_uids))
        )
        logger.debug(
            "IMAP search returned %d UIDs from start_uid=%d; processing %d",
            len(mail_uids),
            start_uid,
            len(recent_uids),
        )

        return _parse_uids(mail, recent_uids)
    finally:
        _close_mail(mail)


def fetch_emails_by_date_range(
    limit: int,
    from_date: datetime,
    to_date: datetime | None = None,
) -> list[dict]:
    """Fetch up to *limit* emails in [from_date, to_date], oldest first."""
    mail = None
    end_date = to_date or datetime.now(UTC)
    from_date_utc = _as_utc(from_date)
    to_date_utc = _as_utc(end_date)

    if from_date_utc > to_date_utc:
        raise ValueError("from_date must be <= to_date")

    imap_since = from_date_utc.strftime("%d-%b-%Y")
    # IMAP BEFORE is date-only and exclusive; add 1 day to include the end date.
    imap_before = (to_date_utc + timedelta(days=1)).strftime("%d-%b-%Y")

    for attempt in range(1, _CONNECT_MAX_ATTEMPTS + 1):
        try:
            mail = _connect_to_inbox()
            status, data = mail.uid(
                "search",
                None,
                f'(SINCE "{imap_since}" BEFORE "{imap_before}")',
            )
            if status != "OK":
                _close_mail(mail)
                mail = None
                raise RuntimeError(f"IMAP date-range search failed: {status}")
            break
        except _TRANSIENT_IMAP_ERRORS as exc:
            _close_mail(mail)
            mail = None
            if attempt < _CONNECT_MAX_ATTEMPTS:
                logger.warning(
                    "Transient IMAP error on attempt %d/%d: %s — retrying in %ds",
                    attempt,
                    _CONNECT_MAX_ATTEMPTS,
                    exc,
                    _CONNECT_RETRY_DELAY_SECONDS,
                )
                time.sleep(_CONNECT_RETRY_DELAY_SECONDS)
            else:
                logger.error(
                    "IMAP connection failed after %d attempts: %s",
                    _CONNECT_MAX_ATTEMPTS,
                    exc,
                )
                raise
        except imaplib.IMAP4.error as exc:
            logger.error("Permanent IMAP error: %s", exc)
            _close_mail(mail)
            raise

    try:
        if not data or not data[0]:
            logger.info("No emails found in backfill date range")
            return []

        mail_uids = data[0].split()
        target_uids = mail_uids[:limit]
        parsed = _parse_uids(mail, target_uids)
        filtered: list[dict] = []
        for row in parsed:
            received = row.get("received_date")
            if received is None:
                continue
            received_utc = _as_utc(received)
            if from_date_utc <= received_utc <= to_date_utc:
                filtered.append(row)
        return filtered
    finally:
        _close_mail(mail)


def get_uid_received_date(uid: int, timeout: int | None = None) -> datetime | None:
    """Return the Date header timestamp for a specific UID."""
    mail = _connect_to_inbox(timeout=timeout)
    try:
        status, msg_data = mail.uid("fetch", str(uid), "(BODY.PEEK[HEADER.FIELDS (DATE)])")
        if status != "OK" or not msg_data:
            return None

        for part in msg_data:
            if not isinstance(part, tuple):
                continue
            msg = email.message_from_bytes(part[1])
            date_str = msg.get("Date")
            if not date_str:
                continue
            parsed = parsedate_to_datetime(date_str)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        return None
    finally:
        _close_mail(mail)


def get_latest_uid(timeout: int | None = None) -> int | None:
    """Return the newest UID currently available in the inbox."""
    mail = _connect_to_inbox(timeout=timeout)
    try:
        status, data = mail.uid("search", None, "UID 1:*")
        if status != "OK" or not data or not data[0]:
            return None
        raw_uid = data[0].split()[-1]
        return int(raw_uid.decode() if isinstance(raw_uid, bytes) else raw_uid)
    except ValueError:
        logger.warning("Could not parse latest inbox UID")
        return None
    finally:
        _close_mail(mail)


def _close_mail(mail) -> None:
    if not mail:
        return
    try:
        mail.close()
    except Exception as e:
        logger.warning("IMAP close() failed: %s", e)
    try:
        mail.logout()
    except Exception as e:
        logger.warning("IMAP logout() failed: %s", e)


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


def _parse_uids(mail, uids: list[bytes]) -> list[dict]:
    results = []
    for uid in uids:
        try:
            status, msg_data = mail.uid("fetch", uid, "(RFC822)")
            if status != "OK":
                logger.warning("Failed to fetch uid=%s — IMAP status: %s", uid.decode(), status)
                continue

            for part in msg_data:
                if not isinstance(part, tuple):
                    continue

                msg = email.message_from_bytes(part[1])
                sender = _optional_str(msg.get("From"))
                message_id = _optional_str(msg.get("Message-ID"))
                if not message_id:
                    uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
                    logger.warning(
                        "Skipping uid=%s: missing required Message-ID header",
                        uid_str,
                    )
                    continue

                email_date = None
                date_str = msg.get("Date")
                if date_str:
                    try:
                        email_date = parsedate_to_datetime(date_str)
                    except Exception as e:
                        logger.warning("Could not parse date for uid=%s: %s", uid.decode(), e)

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
            logger.error("Error processing email uid=%s: %s", uid_str, e)
            continue
    return results


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
