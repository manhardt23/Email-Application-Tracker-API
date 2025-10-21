import imaplib
import email
from config import EMAIL_USER, EMAIL_PASS, IMAP_SERVER

def connect_to_inbox():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")
    return mail

def fetch_recent_emails(limit=20):
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
                emails.append({
                    "uid": uid.decode(),
                    "message": msg
                })
    return emails