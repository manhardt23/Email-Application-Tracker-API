import re


# Common job-related terms
JOB_KEYWORDS = [
    "application", "applied", "position", "hiring", "interview",
    "offer", "recruiter", "recruitment", "career", "assessment",
    "candidate", "resume", "cv", "job", "role", "opening",
    "opportunity", "thank you for applying", "software", "engineering", "backend"
]

def quick_filter(subject, email_content):
    """
    Fast check to decide whether an email is *likely* job-related.
    Returns True if it's worth sending to LLaMA, False otherwise.
    """
    text = f"{subject} {email_content}".lower()

    score = sum(1 for kw in JOB_KEYWORDS if kw in text)
    
    if score >= 2:
        return True
    
    if re.search(r"thank you for applying|we received your application|next steps", text):
        return True

    return False

if __name__ == '__main__':
    emails = [
        {
            "subject": "Assessment for Software Engineer Position",
            "body": "Hi Jacob, please complete the assessment for your Software Engineer application at Acme Corp..."
        },
        {
            "subject": "50% off sale this weekend!",
            "body": "Don't miss out on our huge discounts..."
        },
        {
            "subject": "Interview Invitation - Backend Developer",
            "body": "We are pleased to invite you to interview for the Backend Developer role at TechWave."
        },
        {
            "subject": "Welcome to our newsletter!",
            "body": "Stay tuned for updates about your favorite products."
        }
    ]

    for email in emails:
        print(f"Subject: {email['subject']}")
        print("Likely job-related:", quick_filter(email['subject'], email['body']))
        print("-" * 60)