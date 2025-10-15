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
    status, data = mail.search(None, "ALL")
    mail_ids = data[0].split()
    recent_ids = mail_ids[-limit:]

    emails = []
    for i in recent_ids:
        status, msg_data = mail.fetch(i, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                emails.append(msg)
    return emails