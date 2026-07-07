from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import AuditLogModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- LATEST VBAK MISSING COLUMNS LOG ---")
logs = db.query(AuditLogModel).filter(
    (AuditLogModel.prompt.like("%Table VBAK has missing columns%")) |
    (AuditLogModel.prompt.like("%Table VBAK is missing columns%"))
).order_by(AuditLogModel.id.desc()).limit(3).all()

for l in logs:
    print(f"[{l.timestamp}] Action: {l.action}")
    print(f"Prompt: {l.prompt}")
    print("="*60)
