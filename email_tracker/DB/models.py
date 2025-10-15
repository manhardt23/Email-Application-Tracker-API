from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
Base = declarative_base()

class ApplicationEmail(Base):
    __tablename__ = "application_emails"

    id = Column(Integer, primary_key=True)
    sender = Column(String)
    subject = Column(String)
    position = Column(String)
    company = Column(String)
    status = Column(String, default="Received")
    received_at = Column(DateTime, default=datetime.utcnow)

def get_engine():
    db_url = os.getenv("DATABASE_URL")
    return create_engine(db_url)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
