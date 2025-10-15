import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.comcast.net")

if not EMAIL_USER or not EMAIL_PASS:
    raise ValueError("Missing email credentials. Please set EMAIL_USER and EMAIL_PASS in .env.")
