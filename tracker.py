from email.mime import application
from LLM_filter import Filter
from email_client import fetch_recent_emails
from email_tracker.DB import models
from sqlalchemy import func
from datetime import datetime, timezone


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
        if not data:
            print(f"no applications found in my emails")
            return False
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
    
    def __repr__(self):
        return (
            f"Email(uid={self.uid}, sender='{self.sender}', "
            f"subject='{self.subject}', date='{self.date}', "
            f"is_application={getattr(self, 'is_application', None)}, "
            f"company={self.company}, position={self.position}, "
            f"stage={self.stage}, confidence={self.confidence})"
        )



class Email_Processor:
    def __init__(self) -> None:
        self.email_list = []
        self.application_emails = []

    def fetch_emails(self, limit):
        raw_emails = fetch_recent_emails(limit)

        for raw_email in raw_emails:
            email = Email_Data(
                uid=raw_email["uid"],
                sender=raw_email["sender"],
                subject=raw_email["subject"],
                body=raw_email["body"],
                date=raw_email["date"]
            )
            self.email_list.append(email)
        print(self.email_list)
        return self.email_list
    
    def analyze_emails(self):
        for email in self.email_list:
            is_application = email.analyze_with_LLM()

            if is_application:
                self.application_emails.append(email)
            else:
                print(f"Not an application")

        return self.application_emails
    
    def get_application_emails(self):
        return self.application_emails

    def get_high_confidence_emails(self):
        return [email for email in self.application_emails if email.confidence == "high"]
    
    def get_emails_needing_review(self):
        return [email for email in self.application_emails if email.need_review()]
    


class Log_DB:
    def __init__(self) -> None:
       self.session = models.get_session()

    def save_email(self, email_data):

        existing = self.session.query(models.ApplicationEmail).filter(
            models.ApplicationEmail.email_id == email_data.uid
        ).first()

        if existing:
            #already in db skip
            return None
        
        #Create email

        email_record = models.ApplicationEmail(
            email_id=email_data.uid,
            sender=email_data.sender,
            subject=email_data.subject,
            received_date=email_data.date,
            email_body=email_data.body,
            detected_company=email_data.company,
            detected_position=email_data.position,
            detected_stage=email_data.stage,
            is_application=email_data.is_application,
            confidence=email_data.confidence,
            needs_review=email_data.need_review()
        )

        if (email_data.confidence in ["high", "medium"] and email_data.company and email_data.position):
            
            company = self.find_or_create_company(email_data.company)

            application = self.find_or_create_application(company, email_data.position)

            email_record.application_id = application.id

            self.update_application_stage(application,email_data.stage, email_data.date)

            self.session.add(email_record)
            self.session.commit()

            return email_record
        

    def save_multiple_emails(self, email_data_list):
        saved_count = 0
        for email_data in email_data_list:
            if self.save_email(email_data):
                saved_count += 1
        print(f"Saved {saved_count} emails in the DB")


    def find_or_create_company(self, company_name):
        company = self.session.query(models.Company).filter(
            func.lower(models.Company.name) == company_name.lower()
        ).first()

        if not company:
            company = models.Company(name=company_name)
            self.session.add(company)
            self.session.flush()

        return company

    def find_or_create_application(self, company, position):
        application = self.session.query(models.Application).filter(
            models.Application.company_id == company.id,
            func.lower(models.Application.position) == position.lower() 
        ).first()

        if not application:
            application = models.Application(
                company_id=company.id,
                position=position,
                stage="applied"
            )
            self.session.add(application)
            self.session.flush()
        
        return application

    def update_application_stage(self, application, new_stage, date):
        if not new_stage:
            return
        
        # Normalize date to timezone-naive UTC for comparison
        if date.tzinfo is not None:
            # Convert timezone-aware date to UTC and make it naive
            date_naive = date.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            date_naive = date
        
        # Ensure application.last_updated is also naive for comparison
        if application.last_updated.tzinfo is not None:
            last_updated_naive = application.last_updated.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            last_updated_naive = application.last_updated
        
        if date_naive > last_updated_naive:
            application.stage = new_stage
            application.last_updated = date_naive

    def close(self):
        self.session.close()



# main_pipeline.py

def main(limit):
    print("=== Job Application Email Pipeline ===\n")
    
    # Step 0: Ensure database tables exist
    try:
        models.create_tables()
    except Exception as e:
        print(f"Warning: Could not verify/create tables: {e}")
        print("Attempting to continue...")
    
    # Step 1: Fetch and analyze emails
    processor = Email_Processor()
    processor.fetch_emails(limit)
    processor.analyze_emails()
    
    # Step 2: Get application emails
    application_emails = processor.get_application_emails()
    
    if not application_emails:
        print("No application emails found")
        return
    
    # Step 3: Save to database
    db_logger = Log_DB()
    db_logger.save_multiple_emails(application_emails)
    db_logger.close()
    
    # Step 4: Show summary
    print("\n=== Summary ===")
    print(f"Total emails processed: {len(processor.email_list)}")
    print(f"Application emails found: {len(processor.application_emails)}")
    print(f"High confidence: {len(processor.get_high_confidence_emails())}")
    print(f"Needs review: {len(processor.get_emails_needing_review())}")

if __name__ == "__main__":
    import config
    main(config.get_email_limit())