import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import ArtifactModel

engine = create_engine("sqlite:///./celonis_orchestrator.db")
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

print("--- LATEST DATA MODEL ARTIFACT ---")
a = db.query(ArtifactModel).filter(ArtifactModel.stage == "data_model").order_by(ArtifactModel.id.desc()).first()
if a:
    print(f"Artifact ID: {a.id}, Version: {a.version}, Approved: {a.approved}")
    print("Content:")
    print(a.content)
else:
    print("No data model artifact found.")
