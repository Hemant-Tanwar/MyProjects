import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel, ArtifactModel

db = SessionLocal()
try:
    sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
    print("Latest Session Name:", sess.name)
    art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == sess.id,
        ArtifactModel.stage == "sql"
    ).order_by(ArtifactModel.version.desc()).first()
    
    if art:
        print("SQL Artifact Content:")
        print(art.content)
    else:
        print("No SQL artifact found!")
finally:
    db.close()
