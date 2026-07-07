from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import AuditLogModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- DATA MODEL STAGE LOGS ---")
logs = db.query(AuditLogModel).filter(AuditLogModel.stage == "data_model").order_by(AuditLogModel.id.desc()).limit(15).all()
for l in reversed(logs):
    print(f"[{l.timestamp}] Action: {l.action}")
    print(f"Prompt: {l.prompt}")
    if l.error:
        print(f"Error: {l.error}")
    print("="*60)
