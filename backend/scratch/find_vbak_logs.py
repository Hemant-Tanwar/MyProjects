from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import AuditLogModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- AUDIT LOGS SEARCH FOR 'VBAK' ---")
logs = db.query(AuditLogModel).filter(
    (AuditLogModel.prompt.like("%VBAK%")) | 
    (AuditLogModel.response.like("%VBAK%")) | 
    (AuditLogModel.error.like("%VBAK%"))
).all()

for l in logs:
    print(f"[{l.timestamp}] Action: {l.action}")
    print(f"Prompt: {l.prompt}")
    if l.error:
        print(f"Error: {l.error}")
    print("="*60)
