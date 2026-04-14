from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError

from app.db.models import WorkerRun
from app.db.repositories.base import BaseRepository

# Long IMAP / LLM runs: stale reconciliation frees the single active-job slot.
STALE_WORKER_RUN_MINUTES = 24 * 60


class WorkerRunRepository(BaseRepository):
    def get_latest_run(self) -> WorkerRun | None:
        return (
            self.session.query(WorkerRun)
            .order_by(WorkerRun.queued_at.desc(), WorkerRun.id.desc())
            .first()
        )

    def reconcile_stale_worker_runs(self, max_age_minutes: int = STALE_WORKER_RUN_MINUTES) -> None:
        """Mark queued/running rows older than max_age_minutes as failed so new jobs can enqueue."""
        threshold = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        stale = (
            self.session.query(WorkerRun)
            .filter(
                or_(
                    and_(WorkerRun.status == "queued", WorkerRun.queued_at < threshold),
                    and_(
                        WorkerRun.status == "running",
                        WorkerRun.started_at.isnot(None),
                        WorkerRun.started_at < threshold,
                    ),
                )
            )
            .all()
        )
        msg = (
            f"Stale run auto-failed (exceeded {max_age_minutes} minutes in queued/running state)."
        )
        now = datetime.now(timezone.utc)
        for run in stale:
            run.status = "failed"
            run.finished_at = now
            run.error_message = msg

    def try_create_queued_run(self) -> WorkerRun | None:
        """Insert a queued WorkerRun, or None if another active (queued/running) row exists."""
        self.reconcile_stale_worker_runs()
        run = WorkerRun(status="queued")
        try:
            with self.session.begin_nested():
                self.session.add(run)
                self.session.flush()
            return run
        except IntegrityError:
            return None

    def claim_if_queued(self, run_id: int) -> WorkerRun | None:
        """Transition run_id from queued to running and set started_at. Returns None if not queued."""
        now = datetime.now(timezone.utc)
        updated = (
            self.session.query(WorkerRun)
            .filter(WorkerRun.id == run_id, WorkerRun.status == "queued")
            .update(
                {"status": "running", "started_at": now},
                synchronize_session=False,
            )
        )
        if updated != 1:
            return None
        return self.get_by_id(run_id)

    def complete(
        self,
        run: WorkerRun,
        emails_fetched: int,
        applications_found: int,
        emails_saved: int,
    ) -> None:
        run.finished_at = datetime.now(timezone.utc)
        run.status = "completed"
        run.emails_fetched = emails_fetched
        run.applications_found = applications_found
        run.emails_saved = emails_saved

    def fail(self, run: WorkerRun, error_message: str) -> None:
        run.finished_at = datetime.now(timezone.utc)
        run.status = "failed"
        run.error_message = error_message

    def get_by_id(self, run_id: int) -> WorkerRun | None:
        return self.session.query(WorkerRun).filter(WorkerRun.id == run_id).first()

    def get_recent(self, limit: int = 10) -> list[WorkerRun]:
        return (
            self.session.query(WorkerRun)
            .order_by(func.coalesce(WorkerRun.started_at, WorkerRun.queued_at).desc())
            .limit(limit)
            .all()
        )
