from datetime import datetime

from app.db.models import WorkerRun
from app.db.repositories.base import BaseRepository


class WorkerRunRepository(BaseRepository):
    def create(self) -> WorkerRun:
        run = WorkerRun(status="running")
        self.session.add(run)
        self.session.flush()
        return run

    def complete(
        self,
        run: WorkerRun,
        emails_fetched: int,
        applications_found: int,
        emails_saved: int,
    ) -> None:
        run.finished_at = datetime.utcnow()
        run.status = "completed"
        run.emails_fetched = emails_fetched
        run.applications_found = applications_found
        run.emails_saved = emails_saved

    def fail(self, run: WorkerRun, error_message: str) -> None:
        run.finished_at = datetime.utcnow()
        run.status = "failed"
        run.error_message = error_message

    def get_by_id(self, run_id: int) -> WorkerRun | None:
        return self.session.query(WorkerRun).filter(WorkerRun.id == run_id).first()

    def get_recent(self, limit: int = 10) -> list[WorkerRun]:
        return (
            self.session.query(WorkerRun)
            .order_by(WorkerRun.started_at.desc())
            .limit(limit)
            .all()
        )
