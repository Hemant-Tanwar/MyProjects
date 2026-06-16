import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set logging to debug/info so we can see everything
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

from app.database import SessionLocal, SessionModel, ArtifactModel
from main import push_to_celonis_platform

db = SessionLocal()
try:
    sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
    print("Running push_to_celonis_platform for session:", sess.name)
    
    stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
    bundle = {}
    for stg in stages:
        art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == sess.id,
            ArtifactModel.stage == stg
        ).order_by(ArtifactModel.version.desc()).first()
        bundle[stg] = art.content if art else ""
        
    success = push_to_celonis_platform(sess, bundle)
    print("push_to_celonis_platform returned:", success)
    
finally:
    db.close()
