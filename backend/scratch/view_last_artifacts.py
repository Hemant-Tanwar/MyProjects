import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import ArtifactModel, SessionModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- LATEST SQL ARTIFACTS ---")
artifacts = db.query(ArtifactModel).filter(ArtifactModel.stage == "sql").order_by(ArtifactModel.id.desc()).limit(3).all()
for a in artifacts:
    print(f"Artifact ID: {a.id}, Session ID: {a.session_id}, Version: {a.version}, Approved: {a.approved}")
    print("Content:")
    print(a.content)
    print("="*60)
