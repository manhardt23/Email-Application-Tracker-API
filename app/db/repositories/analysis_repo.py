from app.db.models import EmailAnalysis
from app.db.repositories.base import BaseRepository
from app.llm.base import EmailClassification


class AnalysisRepository(BaseRepository):
    def create(
        self,
        email_id: int,
        classification: EmailClassification,
        model_used: str,
        worker_run_id: int | None = None,
    ) -> EmailAnalysis:
        confidence = classification.confidence
        needs_review = confidence not in {"high", "medium"}

        analysis = EmailAnalysis(
            email_id=email_id,
            worker_run_id=worker_run_id,
            is_application=classification.is_application,
            detected_company=classification.company,
            detected_position=classification.position,
            detected_stage=classification.stage,
            confidence=confidence,
            needs_review=needs_review,
            model_used=model_used,
        )
        self.session.add(analysis)
        self.session.flush()
        return analysis

    def link_to_application(self, analysis: EmailAnalysis, application_id: int) -> None:
        analysis.application_id = application_id

    def get_needs_review(self) -> list[EmailAnalysis]:
        return (
            self.session.query(EmailAnalysis)
            .filter(EmailAnalysis.needs_review == True)  # noqa: E712
            .all()
        )

    def get_by_worker_run(self, worker_run_id: int) -> list[EmailAnalysis]:
        return (
            self.session.query(EmailAnalysis)
            .filter(EmailAnalysis.worker_run_id == worker_run_id)
            .all()
        )
