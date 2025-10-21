from email_client import fetch_recent_emails
from tracker import build_application_log

def main():
    emails = fetch_recent_emails()
    log = build_application_log(emails)

    print("Job Application Tracker:")
    print(f"{log[0]}")

if __name__ == "__main__":
    main()
