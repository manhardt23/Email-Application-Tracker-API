import ollama
import re
import json
from quick_filter import quick_filter

model_name = "llama3"

def analyze_email_with_llama3(sender, subject, email_content):
    #check with quick filter first to save time
    if not quick_filter(subject, email_content):
        return 

    # Construct your structured prompt
    prompt = f"""
    Analyze this email and determine:
    1. Is this related to a job application? (yes/no)
    2. If yes, what stage? (applied/rejected/interview/offer/assessment/other)
    3. Company name (if identifiable)
    4. Position title (if mentioned)

    Email:
    From: {sender}
    Subject: {subject}
    Body: {email_content[:2000]}

    Respond in JSON format:
    {{
        "is_application": boolean,
        "stage": "string or null",
        "company": "string or null",
        "position": "string or null",
        "confidence": "high/medium/low"
    }}
    """


    # Send to Ollama
    response = ollama.chat(
    model=model_name,
    messages=[{"role": "user", "content": prompt}])

    content = response['message']['content']



    # Use regex to safely find the JSON block
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
            analysis = json.loads(match.group(0))
    else:
        print("No JSON found. Raw content:\n", content)
    #print(content)
    return analysis


if __name__ == "__main__":
    # Example test
    sample_email = """
    Dear Jacob ,                          

We have reviewed your qualifications for the Student Technical position. We were very fortunate to have a strong group of applicants to consider for this role, and we wanted to let you know we’ve decided to move forward with other candidates. If you applied for multiple positions, your other applications may still be moving forward. You can check your application status at any time via the Candidate Home where you applied.

Your resume will be retained in our database as per our data retention policy in compliance with applicable laws. If there is interest in your skillset for other positions within Unisys, we may contact you for further consideration. Please also feel free to check the Unisys Career Site, or connect with us on LinkedIn for the latest career opportunities. Thank you again for considering Unisys, and we hope to be in touch soon!

Sincerely,
Unisys Talent Acquisition Team

Please note that if you wish to permanently remove your data from our system, you can do so by logging in to your account and navigating to Account Settings -> Delete My Information.

Additionally, direct replies to this message are undeliverable and will not reach the Talent Acquisition Team. Please do not reply to this message.
    """
    analysis = analyze_email_with_llama3(
        sender="unisys@myworkday.com",
        subject="Your Job Application to Unisys - Student Technical",
        email_content=sample_email
    )
    print(json.dumps(analysis, indent=4))
