from email_client import fetch_recent_emails
from tracker import build_application_log

def main():
    emails = fetch_recent_emails()
    log = build_application_log(emails)

    print("Job Application Tracker:")
    for entry in log:
        print(f"- From: {entry['from']}")
        print(f"  Subject: {entry['subject']}")
        print(f"  Status: {entry['status']}")
        print("")

if __name__ == "__main__":
    main()
