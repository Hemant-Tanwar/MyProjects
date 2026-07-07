import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import AuditLogModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- ALL AUDIT LOGS FOR LATEST RUN ---")
logs = db.query(AuditLogModel).order_by(AuditLogModel.id.desc()).limit(100).all()
for l in reversed(logs):
    print(f"[{l.timestamp}] Stage: {l.stage}, Agent: {l.agent_name}, Action: {l.action}")
    print(f"Prompt: {l.prompt}")
    if l.error:
        print(f"Error: {l.error}")
    print("="*60)
