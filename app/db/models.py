from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    literal_column,
    text,
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
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

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
    stage = Column(String(50), server_default="applied", default="applied", nullable=False)
    applied_date = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    last_updated = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
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
    received_date = Column(DateTime(timezone=True), nullable=False, index=True)
    body = Column(Text)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

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

    __table_args__ = (
        Index(
            "uq_worker_runs_single_active",
            # PostgreSQL requires an expression index on a constant to use
            # double-parens syntax: ON worker_runs ((1)) WHERE ...
            literal_column("(1)"),
            unique=True,
            sqlite_where=text("status IN ('queued', 'running')"),
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id = Column(Integer, primary_key=True)
    last_processed_uid = Column(Integer, nullable=True)
    queued_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), server_default="queued", default="queued", nullable=False)
    emails_fetched = Column(Integer, server_default="0", default=0, nullable=False)
    applications_found = Column(Integer, server_default="0", default=0, nullable=False)
    emails_saved = Column(Integer, server_default="0", default=0, nullable=False)
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
    is_application = Column(Boolean, server_default=false(), default=False, nullable=False)
    detected_company = Column(String(255))
    detected_position = Column(String(500))
    detected_stage = Column(String(50))
    confidence = Column(String(20))
    needs_review = Column(
        Boolean, server_default=false(), default=False, nullable=False, index=True
    )
    model_used = Column(String(100))
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    email = relationship("Email", back_populates="analysis")
    application = relationship("Application", back_populates="analyses")
    worker_run = relationship("WorkerRun", back_populates="analyses")

    def __repr__(self) -> str:
        return (
            f"<EmailAnalysis(id={self.id}, is_application={self.is_application}, "
            f"confidence='{self.confidence}')>"
        )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), server_default="viewer", default="viewer", nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
