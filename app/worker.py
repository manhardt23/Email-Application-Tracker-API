"""
Standalone worker entry point — runs the email pipeline and exits.

Local:      python -m app.worker
Docker:     docker run --rm <IMAGE> python -m app.worker
Cron:       0 7,12,17,20 * * 1-5
            docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker

Every invocation (cron, manual, or API-triggered) creates or updates a WorkerRun row.
API-triggered runs pass worker_run_id so the pre-created row is reused.
"""
from app.config import get_settings
from app.db import models
from app.db.database import SessionLocal, engine
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.email_repo import EmailRepository
from app.db.repositories.worker_run_repo import WorkerRunRepository
from app.llm.factory import build_classifier
from app.services.email_service import EmailProcessor


def _build_classifier():
    return build_classifier(get_settings())


def run(worker_run_id: int | None = None) -> None:
    print("=== Job Application Email Pipeline ===")
    settings = get_settings()

    models.Base.metadata.create_all(bind=engine)

    classifier = _build_classifier()
    processor = EmailProcessor(classifier)
    processor.fetch_emails(settings.email_limit)
    processor.analyze_emails()

    session = SessionLocal()
    try:
        run_repo = WorkerRunRepository(session)

        # Reuse an existing run row (API-triggered) or create one (cron/manual).
        if worker_run_id is not None:
            worker_run = run_repo.get_by_id(worker_run_id)
        else:
            worker_run = run_repo.create()
            session.commit()

        email_repo = EmailRepository(session)
        company_repo = CompanyRepository(session)
        app_repo = ApplicationRepository(session)
        analysis_repo = AnalysisRepository(session)

        saved = 0
        model_name = getattr(classifier, "model_name", "unknown")

        for email_data in processor.email_list:
            if email_repo.exists(email_data.message_id, email_data.uid):
                print(f"Duplicate email — skipping: {email_data.message_id or email_data.uid}")
                continue

            email_record = email_repo.create(
                message_id=email_data.message_id,
                uid=email_data.uid,
                sender=email_data.sender,
                subject=email_data.subject,
                body=email_data.body,
                received_date=email_data.date,
            )

            # Only create an analysis row if LLM classification ran.
            if email_data.is_application is not None:
                from app.llm.base import EmailClassification
                classification = EmailClassification(
                    is_application=bool(email_data.is_application),
                    company=email_data.company,
                    position=email_data.position,
                    stage=email_data.stage,
                    confidence=email_data.confidence or "low",
                )
                analysis = analysis_repo.create(
                    email_id=email_record.id,
                    classification=classification,
                    model_used=model_name,
                    worker_run_id=worker_run.id,
                )

                if (
                    email_data.is_application
                    and email_data.confidence in ("high", "medium")
                    and email_data.company
                    and email_data.position
                ):
                    company = company_repo.find_or_create(email_data.company)
                    application = app_repo.find_or_create(company.id, email_data.position)
                    analysis_repo.link_to_application(analysis, application.id)
                    app_repo.update_stage(application, email_data.stage, email_data.date)

            session.commit()
            saved += 1

        emails_fetched = len(processor.email_list)
        applications_found = len(processor.application_emails)
        run_repo.complete(worker_run, emails_fetched, applications_found, saved)
        session.commit()

    except Exception as e:
        try:
            run_repo.fail(worker_run, str(e))
            session.commit()
        except Exception:
            pass
        raise
    finally:
        session.close()

    print("\n=== Summary ===")
    print(f"Fetched:       {emails_fetched}")
    print(f"Applications:  {applications_found}")
    print(f"Saved:         {saved}")
    print(f"High conf:     {len(processor.get_high_confidence())}")
    print(f"Needs review:  {len(processor.get_needs_review())}")


if __name__ == "__main__":
    run()
