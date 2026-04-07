"""
Standalone worker entry point — runs the email pipeline and exits.

Local:      python -m app.worker
Docker:     docker run --rm <IMAGE> python -m app.worker
Cron:       0 7,12,17,20 * * 1-5  docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
"""
from app.config import get_settings
from app.db.database import SessionLocal, engine
from app.db import models
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.email_repo import EmailRepository
from app.llm.base import LLMClassifier
from app.services.email_service import EmailProcessor


def _build_classifier() -> LLMClassifier:
    settings = get_settings()
    if settings.llm_provider == "groq":
        from app.llm.groq_adapter import GroqAdapter
        return GroqAdapter()
    from app.llm.ollama_adapter import OllamaAdapter
    return OllamaAdapter()


def run() -> None:
    print("=== Job Application Email Pipeline ===")
    settings = get_settings()

    models.Base.metadata.create_all(bind=engine)

    classifier = _build_classifier()
    processor = EmailProcessor(classifier)
    processor.fetch_emails(settings.email_limit)
    processor.analyze_emails()

    application_emails = processor.application_emails
    if not application_emails:
        print("No application emails found in this run")
        return

    saved = 0
    session = SessionLocal()
    try:
        email_repo = EmailRepository(session)
        company_repo = CompanyRepository(session)
        app_repo = ApplicationRepository(session)

        for email_data in application_emails:
            if email_repo.find_by_message_id(email_data.message_id):
                print(
                    "Duplicate Message-ID — skipping email: "
                    f"{email_data.message_id}"
                )
                continue

            email_record = email_repo.create_from_email_data(email_data)

            if (
                email_data.confidence in ("high", "medium")
                and email_data.company
                and email_data.position
            ):
                company = company_repo.find_or_create(email_data.company)
                application = app_repo.find_or_create(company.id, email_data.position)
                email_repo.link_to_application(email_record, application.id)
                app_repo.update_stage(application, email_data.stage, email_data.date)

            session.commit()
            saved += 1
    finally:
        session.close()

    print("\n=== Summary ===")
    print(f"Fetched:       {len(processor.email_list)}")
    print(f"Applications:  {len(application_emails)}")
    print(f"Saved:         {saved}")
    print(f"High conf:     {len(processor.get_high_confidence())}")
    print(f"Needs review:  {len(processor.get_needs_review())}")


if __name__ == "__main__":
    run()
