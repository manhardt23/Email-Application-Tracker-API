from sqlalchemy import Boolean, Column, Integer, String, DateTime, create_engine, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
Base = declarative_base()

class Company(Base):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    domain = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship: One company has many applications
    applications = relationship("Application", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}')>"

class Application(Base):
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    position = Column(String(500), nullable=False)
    stage = Column(String(50), default='applied', nullable=False)
    applied_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = Column(Text)
    
    # Relationships
    company = relationship("Company", back_populates="applications")
    emails = relationship("ApplicationEmail", back_populates="application", cascade="all, delete-orphan")
    
    # Constraint: Can't have duplicate position at same company
    __table_args__ = (
        UniqueConstraint('company_id', 'position', name='unique_company_position'),
    )
    
    def __repr__(self):
        return f"<Application(id={self.id}, position='{self.position}', stage='{self.stage}')>"

class ApplicationEmail(Base):
    __tablename__ = 'application_emails'
    
    id = Column(Integer, primary_key=True)
    email_id = Column(String(255), unique=True, nullable=False, index=True)
    application_id = Column(Integer, ForeignKey('applications.id'), nullable=True, index=True)
    
    # Email metadata
    sender = Column(String(255), nullable=False)
    subject = Column(String(1000))
    received_date = Column(DateTime, nullable=False, index=True)
    email_body = Column(Text)
    
    # LLM-extracted information
    detected_company = Column(String(255))
    detected_position = Column(String(500))
    detected_stage = Column(String(50))
    is_application = Column(Boolean, default=False, nullable=False)
    confidence = Column(String(20))
    
    # Review flag
    needs_review = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    application = relationship("Application", back_populates="emails")
    
    def __repr__(self):
        return f"<ApplicationEmail(id={self.id}, subject='{self.subject[:30]}...', confidence='{self.confidence}')>"


def get_engine():
    db_url = os.getenv("DATABASE_URL")
    return create_engine(
        db_url,
        echo=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def create_tables():
    """Create all tables in the database"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully!")


def drop_tables():
    """Drop all tables - USE WITH CAUTION"""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped!")


def get_db():
    """Generator function to get database session (for FastAPI dependency injection)"""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
