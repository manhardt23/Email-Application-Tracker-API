from LLM_filter import Filter
from email_client import fetch_recent_emails


class Email_Data:

    def __init__(self, uid, sender, subject, date, body):
        self.uid = uid
        self.sender = sender
        self.subject = subject
        self.date = date
        self.body = body

        #Defined later
        self.company = None
        self.position = None
        self.stage = None
        self.confidence = None

    def analyze_with_LLM(self):
        data = Filter.analyze_email_with_llama3(self.sender, self.subject, self.body)
        
        self.is_application = data.get("is_application", False)
        self.company = data.get("company")
        self.position = data.get("position")
        self.stage = data.get("stage")
        self.confidence = data.get("confidence")

        return self.is_application
    
    def need_review(self):
        return self.confidence == "low"
    
    def to_dict(self):
        return {
            "uid": self.uid,
            "sender": self.sender,
            "subject": self.subject,
            "date": self.date,
            "body": self.body,
            "is_application": self.is_application,
            "company": self.company,
            "position": self.position,
            "stage": self.stage,
            "confidence": self.confidence
        }


class Email_Processor:
    def __init__(self) -> None:
        self.email_list = []
        self.application_emails = []

    def fetch_emails(self):
        raw_emails = fetch_recent_emails()

        for raw_email in raw_emails:
            email = Email_Data(
                uid=raw_email["uid"],
                sender=raw_email["sender"],
                subject=raw_email["subject"],
                date=raw_email["date"]
            )
            self.email_list.append(email)
        return self.email_list
    
    def get_application_emails(self):
        return self.application_emails

    def get_high_confidence_emails(self):
        return [email for email in self.application_emails if email.confidence == "high"]
    
    def get_emails_needing_review(self):
        return [email for email in self.application_emails if email.needs_review()]