import re


# Common job-related terms (application-focused)
JOB_KEYWORDS = [
    "application", "applied", "interview", "offer", "assessment",
    "candidate", "resume", "cv", "thank you for applying",
    "thank you for apply", "we received your application", "next steps", "your application"
]

# Known job board domains (emails from these should be filtered out unless they're application confirmations)
JOB_BOARD_DOMAINS = [
    "indeed.com", "indeedmail.com", "indeedapply.com",
    "linkedin.com", "linkedinmail.com",
    "glassdoor.com", "glassdoormail.com",
    "ziprecruiter.com", "ziprecruiteremail.com",
    "monster.com", "monsteremail.com",
    "careerbuilder.com", "cbmail.com",
    "dice.com", "dicemail.com",
    "simplyhired.com", "simplyhiredmail.com",
    "snagajob.com", "snagajobmail.com",
    "jobvite.com", "jobvitemail.com",
    "greenhouse.io", "greenhouseemail.com",
    "lever.co", "levermail.com",
    "workday.com", "myworkday.com",  # Workday is often used by companies, but also sends job alerts
    "naukri.com", "naukrimail.com",
    "shine.com", "shinemail.com"
]

# Patterns that indicate job postings (should be filtered out early)
JOB_POSTING_PATTERNS = [
    r"new job.*opening",
    r"job.*alert",
    r"new.*position.*available",
    r"we're hiring",
    r"join our team",
    r"career.*opportunity",
    r"apply now",
    r"job.*posting",
    r"new.*role",
    r"open.*position",
    r"we have.*opening",
    r"looking for.*engineer",
    r"hiring.*engineer",
    r"job.*opportunity",
    r"new.*opportunities",
    r"new.*jobs",
    r"job.*recommendations",
    r"jobs.*you.*might.*like",
    r"similar.*positions"
]

def extract_domain_from_sender(sender):
    """Extract domain from sender email address"""
    if not sender:
        return None
    # Handle formats like "Name <email@domain.com>" or just "email@domain.com"
    match = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', sender)
    if match:
        return match.group(1).lower()
    return None

def quick_filter(sender, subject, email_content):
    """
    Fast check to decide whether an email is *likely* about an existing application.
    Returns True if it's worth sending to LLaMA, False otherwise.
    Filters out obvious job postings and job board emails early.
    """
    text = f"{subject} {email_content}".lower()
    sender_domain = extract_domain_from_sender(sender)

    # Check if email is from a known job board
    if sender_domain:
        for job_board_domain in JOB_BOARD_DOMAINS:
            if job_board_domain in sender_domain:
                # Allow through ONLY if it contains strong application confirmation language
                # This handles cases where job boards forward application confirmations
                application_indicators = [
                    r"thank you for (applying|apply)",
                    r"we received your application",
                    r"your application (has been|was) (received|submitted)",
                    r"application (status|update)",
                    r"next steps.*application",
                    r"interview.*invitation",
                    r"assessment.*application"
                ]
                has_application_indicator = any(re.search(pattern, text) for pattern in application_indicators)
                
                if not has_application_indicator:
                    # From job board but no application confirmation language = job posting/alert
                    print(f"Filtered out: Job board email from {sender_domain} without application confirmation")
                    return False
                # If it has application indicators, let it through to LLM for final decision
                break

    # Check if it's clearly a job posting (exclude these)
    for pattern in JOB_POSTING_PATTERNS:
        if re.search(pattern, text):
            # But allow through if it also mentions user's application status
            application_status_patterns = [
                r"your application",
                r"application status",
                r"we received",
                r"thank you for (applying|apply)",
                r"application (has been|was) (received|submitted)"
            ]
            if any(re.search(p, text) for p in application_status_patterns):
                break  # Might be both, let LLM decide
            return False  # Clearly a job posting, not an application update
    
    # Check for application-related keywords
    score = sum(1 for kw in JOB_KEYWORDS if kw in text)
    
    if score >= 2:
        return True
    
    # Strong indicators of application status emails (including variations)
    application_confirmation_patterns = [
        r"thank you for (applying|apply)",
        r"we received your application",
        r"next steps",
        r"your application",
        r"application status",
        r"application (has been|was) (received|submitted)"
    ]
    
    if any(re.search(pattern, text) for pattern in application_confirmation_patterns):
        return True

    return False

if __name__ == '__main__':
    emails = [
        {
            "sender": "hr@acmecorp.com",
            "subject": "Assessment for Software Engineer Position",
            "body": "Hi Jacob, please complete the assessment for your Software Engineer application at Acme Corp..."
        },
        {
            "sender": "noreply@store.com",
            "subject": "50% off sale this weekend!",
            "body": "Don't miss out on our huge discounts..."
        },
        {
            "sender": "recruiting@techwave.com",
            "subject": "Interview Invitation - Backend Developer",
            "body": "We are pleased to invite you to interview for the Backend Developer role at TechWave."
        },
        {
            "sender": "newsletter@company.com",
            "subject": "Welcome to our newsletter!",
            "body": "Stay tuned for updates about your favorite products."
        },
        {
            "sender": "noreply@indeed.com",
            "subject": "New Job Opening - Software Engineer",
            "body": "We have a new position available for a Software Engineer. Apply now to join our team!"
        },
        {
            "sender": "jobs@linkedin.com",
            "subject": "Job Alert: Backend Developer Position Available",
            "body": "Check out this new opportunity for a Backend Developer role. We're hiring!"
        },
        {
            "sender": "hr@company.com",
            "subject": "Thank you for your application",
            "body": "We received your application for the Software Engineer position. We'll review it and get back to you."
        },
        {
            "sender": "noreply@indeed.com",
            "subject": "Thank you for applying to Software Engineer at Acme Corp",
            "body": "Thank you for applying to the Software Engineer position at Acme Corp. We have received your application."
        },
        {
            "sender": "noreply@indeed.com",
            "subject": "Thank you for apply to Data Scientist at TechCorp",
            "body": "Thank you for apply to the Data Scientist position. Your application has been received."
        }
    ]

    print("Testing quick_filter function:\n")
    for email in emails:
        print(f"From: {email.get('sender', 'unknown')}")
        print(f"Subject: {email['subject']}")
        sender = email.get('sender', 'test@example.com')
        result = quick_filter(sender, email['subject'], email['body'])
        print(f"Should process (PASS filter): {result}")
        print("-" * 60)