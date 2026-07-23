import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel
from app.celonis_deployer import get_celonis_connection

# Use the latest session's credentials
db = SessionLocal()
sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()

if not sess:
    print("No session found in DB to extract connection info.")
    sys.exit(1)

print(f"Connecting to Celonis using session: {sess.name} (id={sess.id})...")
celonis = get_celonis_connection(db, sess.id, "analysis")

space_id = "cc86cf31-dfbb-45cf-b5aa-9df159d64dd3"
package_id = "9c3c4895-8433-407e-a2bb-0e65a1066b09"
document_id = "6921f873-9404-482c-98b1-9056e2e7a5ed"

try:
    print(f"Fetching space: {space_id}...")
    space = celonis.studio.get_space(space_id)
    print(f"Fetching package: {package_id}...")
    package = space.get_package(package_id)
    print(f"Fetching analysis: {document_id}...")
    analysis = package.get_analysis(document_id)
    
    print("Successfully fetched analysis document!")
    content = analysis.serialized_content
    
    if content:
        # If it is a string containing YAML or JSON, parse it
        if isinstance(content, str):
            import yaml
            try:
                content = yaml.safe_load(content)
            except Exception:
                try:
                    content = json.loads(content)
                except Exception:
                    pass
        
        # Save layout to scratch
        out_path = "scratch/downloaded_analysis_layout.json"
        with open(out_path, "w") as f:
            json.dump(content, f, indent=2)
        print(f"Saved serialized layout to {out_path}")
    else:
        print("Warning: serialized_content was empty!")

except Exception as err:
    print(f"Error fetching from Celonis: {err}")

db.close()
