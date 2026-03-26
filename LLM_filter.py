import ollama
import re
import json
from quick_filter import quick_filter
class Filter:

    def analyze_email_with_llama3(sender, subject, email_content): #Returns json
        model_name = "llama3"
        #check with quick filter first to save time
        # If quick_filter returns False, it's clearly not an application email, skip LLM
        if not quick_filter(sender, subject, email_content):
            print("Quick filter: Not an application email, skipping LLM analysis")
            return None 

        # Construct your structured prompt
        prompt = f"""
        Analyze this email to determine if it's about a job application that the recipient has ALREADY SUBMITTED.
        
        IMPORTANT: This email should ONLY be classified as an application if it:
        - Confirms receipt of an application the user submitted
        - Provides status updates on an existing application (interview, assessment, offer, rejection)
        - Requests action on an existing application (complete assessment, schedule interview)
        - Is a response to an application the user sent
        
        DO NOT classify as an application if the email:
        - Is a job posting or job alert about new openings
        - Promotes new job opportunities the user hasn't applied to
        - Is a newsletter about available positions
        - Invites the user to apply to a new position they haven't applied to yet
        - Is marketing/promotional content about job openings
        
        Email:
        From: {sender}
        Subject: {subject}
        Body: {email_content[:2000]}

        Return ONLY valid JSON with no explanation:
        {{
            "is_application": boolean (true ONLY if about user's existing application, false for job postings),
            "stage": "string or null" (applied/rejected/interview/offer/assessment/other - only if is_application is true),
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

        print(content)

        # Use regex to safely find the JSON block 
        match = re.search(r'\{.*\}', content, re.DOTALL)
        analysis = None
        if match:
            try:
                analysis = json.loads(match.group(0))
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print("Raw content:\n", content)
        else:
            print("No JSON found. Raw content:\n", content)
        #print(content)
            
        #returns a json
        if isinstance(analysis, dict):
             return analysis
        return None


def main():
    sample_email = """
    Dear Jacob ,                          

We have reviewed your qualifications for the Student Technical position. We were very fortunate to have a strong group of applicants to consider for this role, and we wanted to let you know we’ve decided to move forward with other candidates. If you applied for multiple positions, your other applications may still be moving forward. You can check your application status at any time via the Candidate Home where you applied.

Your resume will be retained in our database as per our data retention policy in compliance with applicable laws. If there is interest in your skillset for other positions within Unisys, we may contact you for further consideration. Please also feel free to check the Unisys Career Site, or connect with us on LinkedIn for the latest career opportunities. Thank you again for considering Unisys, and we hope to be in touch soon!

Sincerely,
Unisys Talent Acquisition Team

Please note that if you wish to permanently remove your data from our system, you can do so by logging in to your account and navigating to Account Settings -> Delete My Information.

Additionally, direct replies to this message are undeliverable and will not reach the Talent Acquisition Team. Please do not reply to this message.
    """
    analysis = Filter.analyze_email_with_llama3(
        sender="unisys@myworkday.com",
        subject="Your Job Application to Unisys - Student Technical",
        email_content=sample_email
    )
    print(json.dumps(analysis, indent=4))


if __name__ == '__main__':
     main()