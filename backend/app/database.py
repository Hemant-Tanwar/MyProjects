import datetime
import uuid
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="requirement_analysis")  # stages: requirement_analysis, sql_transformation, data_modeling, knowledge_modeling, view_generation, qa_validation, completed
    current_role = Column(String(50), default="Business User")
    requirement_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    artifacts = relationship("ArtifactModel", back_populates="session", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogModel", back_populates="session", cascade="all, delete-orphan")

class ArtifactModel(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    stage = Column(String(50), nullable=False)  # requirement, sql, data_model, knowledge_model, view, qa
    version = Column(Integer, nullable=False, default=1)
    content = Column(Text, nullable=False)  # JSON spec or SQL code
    rationale = Column(Text, nullable=True)  # Agent explanation
    approved = Column(Boolean, default=False)
    approved_by = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("SessionModel", back_populates="artifacts")

class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    stage = Column(String(50), nullable=False)
    agent_name = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)  # run_started, run_completed, run_failed, approved, rejected, edited
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("SessionModel", back_populates="audit_logs")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
