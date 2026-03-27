from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    applications = relationship("Application", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}')>"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    position = Column(String(500), nullable=False)
    stage = Column(String(50), default="applied", nullable=False)
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = Column(Text)

    company = relationship("Company", back_populates="applications")
    emails = relationship("ApplicationEmail", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "position", name="unique_company_position"),
    )

    def __repr__(self) -> str:
        return f"<Application(id={self.id}, position='{self.position}', stage='{self.stage}')>"


class ApplicationEmail(Base):
    __tablename__ = "application_emails"

    id = Column(Integer, primary_key=True)
    email_id = Column(String(255), unique=True, nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    sender = Column(String(255), nullable=False)
    subject = Column(String(1000))
    received_date = Column(DateTime, nullable=False, index=True)
    email_body = Column(Text)
    detected_company = Column(String(255))
    detected_position = Column(String(500))
    detected_stage = Column(String(50))
    is_application = Column(Boolean, default=False, nullable=False)
    confidence = Column(String(20))
    needs_review = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    application = relationship("Application", back_populates="emails")

    def __repr__(self) -> str:
        preview = (self.subject or "")[:30]
        return f"<ApplicationEmail(id={self.id}, subject='{preview}...', confidence='{self.confidence}')>"
