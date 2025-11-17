import os
from dotenv import load_dotenv, set_key, find_dotenv

load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.comcast.net")
DEFAULT_EMAIL_LIMIT = int(os.getenv("EMAIL_LIMIT", "10"))

if not EMAIL_USER or not EMAIL_PASS:
    raise ValueError("Missing email credentials. Please set EMAIL_USER and EMAIL_PASS in .env.")

def get_email_limit():
    """Get the current default email limit from environment"""
    load_dotenv()  # Reload to get latest value
    return int(os.getenv("EMAIL_LIMIT", "10"))

def set_email_limit(limit):
    """Set the default email limit and persist to .env file"""
    global DEFAULT_EMAIL_LIMIT
    try:
        limit = int(limit)
        if limit < 1:
            raise ValueError("Limit must be a positive integer")
        
        env_path = find_dotenv()
        if env_path:
            set_key(env_path, "EMAIL_LIMIT", str(limit))
        else:
            # If no .env file exists, create one
            with open(".env", "a") as f:
                f.write(f"\nEMAIL_LIMIT={limit}\n")
        
        DEFAULT_EMAIL_LIMIT = limit
        load_dotenv()  # Reload to update module-level variable
        return limit
    except ValueError as e:
        raise ValueError(f"Invalid limit value: {e}")
