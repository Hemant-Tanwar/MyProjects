import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel
from app.celonis_deployer import get_celonis_connection

db = SessionLocal()
sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
celonis = get_celonis_connection(db, sess.id, "analysis")

space_name = f"{sess.name} Space"
space = next((s for s in celonis.studio.get_spaces() if s.name == space_name), None)
pkg = next((p for p in space.get_packages() if "Procure to Pay P2P" in p.name), None)

TARGET_ID = "2cea82f0-1c76-4021-b66b-5c8481845948"
analysis = next((a for a in pkg.get_analyses() if a.id == TARGET_ID), None)

content = analysis.serialized_content
parsed = json.loads(content) if isinstance(content, str) else content
doc = parsed["draft"]["document"]
comps = doc["components"]

print(f"Analysis: {analysis.name}")
print(f"URL: https://wbd8lqn9-2026-06-12.training.celonis.cloud/package-manager/ui/studio/ui/spaces/{space.id}/packages/{pkg.id}/nodes/{TARGET_ID}#!/documents/{TARGET_ID}/view")
print(f"\nSheets ({len(comps)}):")
for sh in comps:
    inner = sh.get("components", [])
    print(f"\n  [{sh.get('contentType','custom')}] '{sh.get('name')}'")
    for c in inner[:12]:
        print(f"    [{c.get('type')}] {c.get('title', c.get('name', '?'))}")

db.close()
