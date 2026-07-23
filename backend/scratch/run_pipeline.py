"""
Generic Process Mining Pipeline Runner
Usage:
  python run_pipeline.py                              # Uses defaults (Accounts Payable)
  python run_pipeline.py "Order to Cash O2C" "O2C requirement..."
  python run_pipeline.py "Procure to Pay P2P" "P2P requirement..."

The backend automatically:
  1. Creates a new Data Pool with the given session name
  2. Uploads ALL tables from Data_source/ directly into that pool
  3. Generates SQL, runs it, creates Data Model / Knowledge Model / View
  4. Creates a Studio Space, Package, and publishes the view
"""
import urllib.request
import urllib.parse
import json
import sys
import time

BASE_URL = "http://127.0.0.1:8001"


def api_post(endpoint, data=None, timeout=600):
    url = f"{BASE_URL}{endpoint}"
    req_data = json.dumps(data).encode("utf-8") if data is not None else b""
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run(session_name: str, requirement: str):
    print("=" * 65)
    print(f"  Process Mining Pipeline: {session_name}")
    print("=" * 65)

    # 1. Create session
    print(f"\n[1/5] Creating session: '{session_name}'...")
    session = api_post("/sessions", {
        "name": session_name,
        "initial_requirement": requirement
    })
    session_id = session["id"]
    print(f"  Session ID : {session_id}")

    # 2. Set role
    print("[2/5] Setting role to Admin...")
    api_post(f"/sessions/{session_id}/role", {"role": "Admin"})

    # 3. Run all pipeline stages
    stages = ["sql", "data_model", "knowledge_model", "analysis"]
    print("[3/5] Running pipeline stages...")
    for stage in stages:
        print(f"  → {stage} ...", end="", flush=True)
        t0 = time.time()
        api_post(f"/sessions/{session_id}/trigger", {"stage": stage})
        print(f" done ({time.time()-t0:.1f}s)")
        time.sleep(1)

    # 4. Promote → uploads all Data_source CSVs to the new pool + full Celonis deploy
    print(f"\n[4/5] Promoting to Celonis Cloud...")
    print("  Uploading all Data_source tables to the new pool + running SQL + deploying...")
    print("  (This takes 5-10 minutes — please wait)\n")
    promote_url = f"{BASE_URL}/sessions/{session_id}/promote"
    req = urllib.request.Request(promote_url, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            content = resp.read()
            print(f"  ✅ Push succeeded! Bundle size: {len(content)} bytes")
    except Exception as e:
        print(f"  ❌ Push error: {e}")

    # 5. Audit log
    print("\n[5/5] Audit log:")
    try:
        with urllib.request.urlopen(f"{BASE_URL}/sessions/{session_id}/audit_logs") as r:
            for log in json.loads(r.read()):
                if log["action"] == "promoted_to_production":
                    print(f"  {log['action']}: {log.get('prompt','')}")
    except Exception as e:
        print(f"  Could not fetch audit: {e}")

    print("\n" + "=" * 65)
    print("  Pipeline complete. Check Celonis Cloud for results.")
    print("=" * 65)


if __name__ == "__main__":
    # Accept any session name and requirement from command line
    name = sys.argv[1] if len(sys.argv) > 1 else "Accounts Payable P2P"
    req  = sys.argv[2] if len(sys.argv) > 2 else (
        "Procure-to-Pay process monitoring. Identify bottlenecks in PO creation, "
        "goods receipt, invoice processing and payment."
    )
    run(name, req)
