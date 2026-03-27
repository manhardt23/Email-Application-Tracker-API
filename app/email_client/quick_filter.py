import re

# Keyword indicators that an email is about a submitted application
JOB_KEYWORDS = [
    "application", "applied", "interview", "offer", "assessment",
    "candidate", "resume", "cv", "thank you for applying",
    "thank you for apply", "we received your application", "next steps", "your application",
]

# Known job board domains — emails from these need extra confirmation language to pass
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
    "workday.com", "myworkday.com",
    "naukri.com", "naukrimail.com",
    "shine.com", "shinemail.com",
]

# Patterns that strongly indicate a generic job posting (not an application update)
JOB_POSTING_PATTERNS = [
    r"new job.*opening", r"job.*alert", r"new.*position.*available",
    r"we're hiring", r"join our team", r"career.*opportunity",
    r"apply now", r"job.*posting", r"new.*role", r"open.*position",
    r"we have.*opening", r"looking for.*engineer", r"hiring.*engineer",
    r"job.*opportunity", r"new.*opportunities", r"new.*jobs",
    r"job.*recommendations", r"jobs.*you.*might.*like", r"similar.*positions",
]

_APPLICATION_CONFIRMATION_PATTERNS = [
    r"thank you for (applying|apply)",
    r"we received your application",
    r"your application (has been|was) (received|submitted)",
    r"application (status|update)",
    r"next steps.*application",
    r"interview.*invitation",
    r"assessment.*application",
]

_APPLICATION_STATUS_PATTERNS = [
    r"your application",
    r"application status",
    r"we received",
    r"thank you for (applying|apply)",
    r"application (has been|was) (received|submitted)",
]


def _extract_domain(sender: str) -> str | None:
    match = re.search(r"@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", sender)
    return match.group(1).lower() if match else None


def quick_filter(sender: str, subject: str, email_content: str) -> bool:
    """
    Fast pre-screen before sending to LLM.
    Returns True if the email is worth classifying, False if it can be skipped.
    Keeps LLM call count low by catching obvious non-application emails early.
    """
    text = f"{subject} {email_content}".lower()
    sender_domain = _extract_domain(sender)

    # Job board emails: only pass through if they contain application confirmation language
    if sender_domain:
        for domain in JOB_BOARD_DOMAINS:
            if domain in sender_domain:
                has_confirmation = any(
                    re.search(p, text) for p in _APPLICATION_CONFIRMATION_PATTERNS
                )
                if not has_confirmation:
                    print(f"Quick filter: job board email from {sender_domain} without confirmation language")
                    return False
                break

    # Generic job postings: skip unless they also mention the user's application status
    for pattern in JOB_POSTING_PATTERNS:
        if re.search(pattern, text):
            if any(re.search(p, text) for p in _APPLICATION_STATUS_PATTERNS):
                break  # Ambiguous — let LLM decide
            return False

    # Score by application-related keyword hits
    if sum(1 for kw in JOB_KEYWORDS if kw in text) >= 2:
        return True

    # Strong single-pattern match
    if any(re.search(p, text) for p in _APPLICATION_CONFIRMATION_PATTERNS):
        return True

    return False
