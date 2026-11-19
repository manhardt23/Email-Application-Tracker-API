"""Shared classification prompt for the Groq and Ollama adapters."""

CLASSIFICATION_PROMPT = """\
Analyze this email to determine if it's about a job application
that the recipient has ALREADY SUBMITTED or that was submitted for them
(including Easy Apply and "your application was sent").

Classify as an application (is_application true) when the email is any of these:
- A confirmation: "thank you for applying", "thanks for applying",
  "thank you for your application", "we have received your application",
  "your application was sent", "you applied to", "application received"
- A rejection, even without the word "application": "not moving forward",
  "other candidates", "not selected", "regret to inform you",
  "position has been filled", "no longer considered",
  "thank you for your interest" followed by a rejection
- An interview: invitation, scheduling, phone screen, onsite, a confirmed time
- An assessment, coding challenge, or take-home tied to a role
- An offer or offer letter
- A direct next step on an application already in progress
  (background check, references, "update on your application")

Set stage to exactly one of: applied, rejected, interview, assessment, offer.
Use applied for a confirmation or "under review".
Use rejected for any "not moving forward" / not selected / other candidates outcome.
Rejection language outranks a thank-you in the same email.
Use null for stage only when it is an application but the step is unclear.

DO NOT classify as an application if the email:
- Is a job alert, digest, "new jobs for you", "jobs you might like",
  "recommended jobs", or "similar positions"
- Invites the user to apply to a role they have not applied to,
  including cold recruiter sourcing
- Is a newsletter, marketing, a discount, or a "special offer" / "limited time offer"
- Is a news or podcast piece ("interview with our CEO")
A footer that says "we're hiring" or "apply now" does not cancel a real
confirmation, rejection, interview, assessment, or offer above.

Email:
From: {sender}
Subject: {subject}
Body: {body}

Return ONLY valid JSON with no explanation:
{{
    "is_application": boolean,
    "stage": "applied|rejected|interview|offer|assessment|other or null",
    "company": "string or null",
    "position": "string or null",
    "confidence": "high|medium|low"
}}
"""
