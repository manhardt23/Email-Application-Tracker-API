"""
Standalone worker entry point — runs the email pipeline and exits.

Usage
-----
Local:      python -m app.worker
Docker:     docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker
Cron:       0 7,12,17,20 * * 1-5
            docker run --rm --env-file /etc/tracker.env <IMAGE> python -m app.worker

Configuration is entirely env-based (no CLI flags). Required vars: DATABASE_URL,
EMAIL_USER, EMAIL_PASS. Optional worker knobs: EMAIL_LIMIT, IMAP_SERVER,
IMAP_TIMEOUT_SECONDS, MAX_EMAILS_PER_RUN, STALE_RUN_TTL_MINUTES, LLM_PROVIDER,
GROQ_API_KEY. See app/config.py for defaults.

API-triggered runs pass worker_run_id for a row already created as 'queued'; the worker
claims it (queued → running) before IMAP/LLM work begins. Cron/manual runs insert a
queued row then claim it in-process. Stale queued/running rows are reconciled at startup
via WorkerRunRepository.

Exit codes
----------
EXIT_OK          (0)  — pipeline completed (even if 0 emails processed)
EXIT_NO_SLOT     (2)  — another run is active; this invocation is a no-op (cron-safe)
EXIT_CONFIG      (3)  — fatal configuration error before any IMAP/DB work
EXIT_PIPELINE    (1)  — unexpected pipeline failure; WorkerRun row marked 'failed'
"""
import logging
import sys
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.db import models
from app.db.database import SessionLocal, engine
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.application_repo import ApplicationRepository
from app.db.repositories.company_repo import CompanyRepository
from app.db.repositories.email_repo import EmailRepository
from app.db.repositories.worker_run_repo import WorkerRunRepository
from app.email_client.client import get_latest_uid, get_uid_received_date
from app.llm.base import EmailClassification
from app.llm.factory import build_classifier
from app.services.email_service import EmailProcessor
from app.services.follow_up_service import FollowUpService
from app.services.worker_runtime import get_effective_max_emails

# ---------------------------------------------------------------------------
# Exit codes — documented in module docstring above.
# ---------------------------------------------------------------------------
EXIT_OK = 0
EXIT_PIPELINE = 1
EXIT_NO_SLOT = 2
EXIT_CONFIG = 3
UID_STALE_DAYS = 30
UNKNOWN_COMPANY = "Unknown Company"
UNKNOWN_POSITION = "Unknown Position"

logger = logging.getLogger(__name__)


def _resolve_uid_cursor(last_processed_uid: int, imap_timeout_seconds: int) -> int:
    """Reset tracked UID to mailbox head when the tracked email is stale/missing."""
    if last_processed_uid <= 0:
        return 0

    tracked_email_date = get_uid_received_date(last_processed_uid, timeout=imap_timeout_seconds)
    latest_uid: int | None = None

    if tracked_email_date is None:
        latest_uid = get_latest_uid(timeout=imap_timeout_seconds)
        if latest_uid is not None:
            logger.info(
                (
                    "UID cursor reset: tracked uid=%d not found/date unavailable; "
                    "jumping to latest uid=%d"
                ),
                last_processed_uid,
                latest_uid,
            )
            return latest_uid
        logger.warning(
            (
                "UID cursor check skipped: tracked uid=%d date unavailable and "
                "latest uid could not be determined"
            ),
            last_processed_uid,
        )
        return last_processed_uid

    tracked_email_date_utc = (
        tracked_email_date.replace(tzinfo=UTC)
        if tracked_email_date.tzinfo is None
        else tracked_email_date.astimezone(UTC)
    )
    stale_threshold = datetime.now(UTC) - timedelta(days=UID_STALE_DAYS)
    if tracked_email_date_utc >= stale_threshold:
        return last_processed_uid

    latest_uid = get_latest_uid(timeout=imap_timeout_seconds)
    if latest_uid is not None:
        logger.info(
            (
                "UID cursor reset: tracked uid=%d email_date=%s older than %d days; "
                "jumping to latest uid=%d"
            ),
            last_processed_uid,
            tracked_email_date_utc.isoformat(),
            UID_STALE_DAYS,
            latest_uid,
        )
        return latest_uid

    logger.warning(
        "UID cursor stale: tracked uid=%d email_date=%s but latest uid unavailable; keeping cursor",
        last_processed_uid,
        tracked_email_date_utc.isoformat(),
    )
    return last_processed_uid


def _validate_config(settings) -> str | None:
    """Return an error message if config is fatally invalid, else None."""
    valid_providers = ("groq", "ollama")
    provider = (settings.llm_provider or "").strip().lower()
    if provider not in valid_providers:
        return (
            f"Invalid LLM_PROVIDER={settings.llm_provider!r}. "
            f"Expected one of: {valid_providers}. Set the env var and retry."
        )
    if provider == "groq" and not settings.groq_api_key:
        return (
            "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
            "Provide the key or switch to LLM_PROVIDER=ollama."
        )
    return None


def run(
    worker_run_id: int | None = None,
    backfill_from: datetime | None = None,
    backfill_to: datetime | None = None,
    backfill_max_emails: int | None = None,
) -> int:
    """Run the email pipeline. Returns an EXIT_* code."""
    logger.info("Worker starting — Job Application Email Pipeline")

    try:
        settings = get_settings()
    except Exception as exc:
        logger.critical("Failed to load settings: %s", exc)
        return EXIT_CONFIG

    config_error = _validate_config(settings)
    if config_error:
        logger.critical("Configuration error: %s", config_error)
        return EXIT_CONFIG

    logger.info("Config: %s", settings.safe_summary())

    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.critical("Cannot connect to database: %s", exc)
        return EXIT_CONFIG

    session = SessionLocal()
    worker_run = None
    run_id: int | None = None
    run_repo = WorkerRunRepository(session)
    processor = None
    try:
        run_repo.reconcile_stale_worker_runs(max_age_minutes=settings.stale_run_ttl_minutes)
        session.commit()
        latest_run = run_repo.get_latest_run()
        last_processed_uid = (
            latest_run.last_processed_uid
            if latest_run is not None and latest_run.last_processed_uid is not None
            else 0
        )
        backfill_mode = backfill_from is not None
        # Backfill mode is date-window driven; skip UID cursor IMAP lookups.
        cursor_uid = (
            last_processed_uid
            if backfill_mode
            else _resolve_uid_cursor(last_processed_uid, settings.imap_timeout_seconds)
        )
        since_uid = 1 if backfill_mode else cursor_uid + 1
        highest_uid = cursor_uid

        if worker_run_id is not None:
            worker_run = run_repo.get_by_id(worker_run_id)
            if worker_run is None:
                logger.error("WorkerRun id=%s not found — aborting.", worker_run_id)
                return EXIT_PIPELINE
            worker_run = run_repo.claim_if_queued(worker_run.id)
            if worker_run is None:
                logger.error(
                    "WorkerRun id=%s could not be claimed (not in queued state).", worker_run_id
                )
                return EXIT_NO_SLOT
            session.commit()
            logger.info("Claimed API-triggered WorkerRun id=%s", worker_run.id)
        else:
            worker_run = run_repo.try_create_queued_run()
            if worker_run is None:
                logger.info(
                    "No WorkerRun slot available (another job is active) — exiting gracefully."
                )
                return EXIT_NO_SLOT
            worker_run = run_repo.claim_if_queued(worker_run.id)
            if worker_run is None:
                logger.error("Could not claim newly enqueued WorkerRun — aborting.")
                return EXIT_PIPELINE
            session.commit()
            logger.info("Created and claimed cron/manual WorkerRun id=%s", worker_run.id)

        run_id = worker_run.id
        # Prefer the higher of the two config caps so MAX_EMAILS_PER_RUN
        # is not capped by legacy EMAIL_LIMIT, then apply runtime override.
        configured_limit = max(settings.max_emails_per_run, settings.email_limit)
        default_limit = get_effective_max_emails(configured_limit)
        effective_limit = backfill_max_emails if backfill_max_emails is not None else default_limit
        if backfill_mode:
            logger.info(
                "run_id=%s backfill fetching up to %d emails from_date=%s to_date=%s",
                worker_run.id,
                effective_limit,
                backfill_from.isoformat(),
                backfill_to.isoformat() if backfill_to else "now",
            )
        else:
            logger.info(
                "run_id=%s fetching up to %d emails since_uid=%d",
                worker_run.id,
                effective_limit,
                since_uid,
            )

        classifier = build_classifier(settings)
        processor = EmailProcessor(classifier)
        processor.fetch_emails(
            effective_limit,
            since_uid=since_uid,
            from_date=backfill_from,
            to_date=backfill_to,
        )
        processor.analyze_emails()

        email_repo = EmailRepository(session)
        company_repo = CompanyRepository(session)
        app_repo = ApplicationRepository(session)
        analysis_repo = AnalysisRepository(session)

        saved = 0
        model_name = getattr(classifier, "model_name", "unknown")

        for email_data in processor.email_list:
            try:
                highest_uid = max(highest_uid, int(email_data.uid))
            except (TypeError, ValueError):
                logger.warning("run_id=%s invalid UID value=%r", run_id, email_data.uid)

            if email_repo.exists(email_data.message_id, email_data.uid):
                logger.debug(
                    "run_id=%s duplicate email — skipping: %s",
                    run_id,
                    email_data.message_id or email_data.uid,
                )
                continue

            received = email_data.date or datetime.now(UTC)
            if email_data.date is None:
                mid = email_data.message_id or "(no Message-ID)"
                logger.warning(
                    "run_id=%s missing received_date for uid=%s message_id=%s",
                    run_id,
                    email_data.uid,
                    mid,
                )

            email_record = email_repo.create(
                message_id=email_data.message_id,
                uid=email_data.uid,
                sender=email_data.sender,
                subject=email_data.subject,
                body=email_data.body,
                received_date=received,
            )

            # Only create an analysis row if LLM classification ran.
            if email_data.is_application is not None:
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

                if email_data.is_application:
                    company_name = (email_data.company or "").strip() or UNKNOWN_COMPANY
                    position_name = (email_data.position or "").strip() or UNKNOWN_POSITION
                    used_fallback = (
                        company_name == UNKNOWN_COMPANY or position_name == UNKNOWN_POSITION
                    )

                    if used_fallback:
                        logger.warning(
                            (
                                "run_id=%s forcing application insert with fallback values "
                                "(company=%r position=%r uid=%s)"
                            ),
                            run_id,
                            company_name,
                            position_name,
                            email_data.uid,
                        )
                        analysis.needs_review = True

                    company = company_repo.find_or_create(company_name)
                    application = app_repo.find_or_create(company.id, position_name)
                    analysis_repo.link_to_application(analysis, application.id)
                    app_repo.update_stage(application, email_data.stage, email_data.date)
                    FollowUpService(session).recompute_last_contact_at(application)

            session.commit()
            saved += 1

        emails_fetched = len(processor.email_list)
        applications_found = len(processor.application_emails)
        if not backfill_mode:
            worker_run.last_processed_uid = highest_uid
        run_repo.complete(worker_run, emails_fetched, applications_found, saved)
        session.commit()

    except Exception as exc:
        if worker_run is not None:
            wid = run_id if run_id is not None else worker_run.id
            try:
                session.rollback()
                wr = run_repo.get_by_id(wid)
                if wr is not None:
                    run_repo.fail(wr, str(exc))
                    session.commit()
            except Exception as secondary:
                logger.error(
                    "Failed to persist WorkerRun failure state: %s",
                    secondary,
                    exc_info=True,
                )
        logger.exception("Pipeline failed: %s", exc)
        return EXIT_PIPELINE
    finally:
        session.close()

    logger.info(
        "run_id=%s completed — fetched=%s applications=%s saved=%s high_conf=%s needs_review=%s",
        run_id,
        emails_fetched,
        applications_found,
        saved,
        len(processor.get_high_confidence()),
        len(processor.get_needs_review()),
    )
    return EXIT_OK


def main() -> None:
    """Entry point for `python -m app.worker`. Exits with appropriate code."""
    from app.logging_config import configure_logging
    configure_logging()
    sys.exit(run())


if __name__ == "__main__":
    main()
