import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def api_post(endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    req_data = json.dumps(data).encode("utf-8") if data is not None else b""
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def run():
    print("1. Creating a new integration test session...")
    session = api_post("/sessions", {
        "name": "Purchase to Pay Cockpit Integration",
        "initial_requirement": "Monitor SAP P2P process. Focus on invoice processing delays, throughput times between purchase order creation and goods receipt, and automation KPIs."
    })
    session_id = session["id"]
    print(f"Session created. ID: {session_id}")

    print("2. Switching role to Admin...")
    api_post(f"/sessions/{session_id}/role", {"role": "Admin"})

    stages = ["sql", "data_model", "knowledge_model", "view", "qa"]
    for stage in stages:
        print(f"3. Running pipeline stage: {stage}...")
        api_post(f"/sessions/{session_id}/trigger", {"stage": stage})
        print(f"Stage {stage} completed.")
        time.sleep(1)

    # Note: Promote endpoint expects the active session role to be Admin or Reviewer
    # We are already Admin, which is authorized.
    print("4. Triggering Promotion endpoint (should export files and push to Celonis)...")
    promote_url = f"{BASE_URL}/sessions/{session_id}/promote"
    req = urllib.request.Request(promote_url, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            print(f"Promotion succeeded! Downloaded zip size: {len(content)} bytes.")
            
        print("\nChecking audit logs for promotion status...")
        logs = api_post(f"/sessions/{session_id}/role", {"role": "Admin"})  # Keep active
        audit_logs = urllib.request.urlopen(f"{BASE_URL}/sessions/{session_id}/audit_logs")
        logs_data = json.loads(audit_logs.read().decode("utf-8"))
        for log in logs_data:
            if log["action"] == "promoted_to_production":
                print(f"\nFound promotion audit log:\n  Action: {log['action']}\n  Details: {log['prompt']}")
    except Exception as e:
        print("Promotion failed:", e)

if __name__ == "__main__":
    run()
