import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.database import SessionLocal, ArtifactModel

db = SessionLocal()
sess_id = "57cf1d9f-f876-4836-ba1c-5e25095b028a"
art = db.query(ArtifactModel).filter(
    ArtifactModel.session_id == sess_id,
    ArtifactModel.stage == "sql"
).order_by(ArtifactModel.version.desc()).first()
db.close()
if art:
    print(art.content[:3000])
else:
    print("No SQL artifact found")
