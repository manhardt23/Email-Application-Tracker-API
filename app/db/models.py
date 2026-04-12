from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.database import Base

# NOTE: Phase 2 will replace this schema with normalized tables
# (emails + email_analyses + worker_runs). These models are preserved
# for Phase 1 to keep the app fully functional during restructuring.


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    domain = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    applications = relationship(
        "Application",
        back_populates="company",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}')>"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    position = Column(String(500), nullable=False)
    stage = Column(String(50), default="applied", nullable=False)
    applied_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes = Column(Text)

    company = relationship("Company", back_populates="applications")
    analyses = relationship(
        "EmailAnalysis",
        back_populates="application",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "position", name="unique_company_position"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, position='{self.position}', stage='{self.stage}')>"


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True)
    message_id = Column(String(512), unique=True, nullable=True, index=True)
    uid = Column(String(255), nullable=False, index=True)
    sender = Column(String(255), nullable=False)
    subject = Column(String(1000))
    received_date = Column(DateTime, nullable=False, index=True)
    body = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    analysis = relationship(
        "EmailAnalysis",
        back_populates="email",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        preview = (self.subject or "")[:30]
        return f"<Email(id={self.id}, subject='{preview}...')>"


class WorkerRun(Base):
    __tablename__ = "worker_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running", nullable=False)
    emails_fetched = Column(Integer, default=0, nullable=False)
    applications_found = Column(Integer, default=0, nullable=False)
    emails_saved = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    analyses = relationship("EmailAnalysis", back_populates="worker_run")

    def __repr__(self) -> str:
        return f"<WorkerRun(id={self.id}, status='{self.status}')>"


class EmailAnalysis(Base):
    __tablename__ = "email_analyses"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, unique=True, index=True)
    worker_run_id = Column(Integer, ForeignKey("worker_runs.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    is_application = Column(Boolean, default=False, nullable=False)
    detected_company = Column(String(255))
    detected_position = Column(String(500))
    detected_stage = Column(String(50))
    confidence = Column(String(20))
    needs_review = Column(Boolean, default=False, nullable=False, index=True)
    model_used = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    email = relationship("Email", back_populates="analysis")
    application = relationship("Application", back_populates="analyses")
    worker_run = relationship("WorkerRun", back_populates="analyses")

    def __repr__(self) -> str:
        return (
            f"<EmailAnalysis(id={self.id}, is_application={self.is_application}, "
            f"confidence='{self.confidence}')>"
        )
