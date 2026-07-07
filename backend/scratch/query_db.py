import sqlite3

conn = sqlite3.connect("celonis_orchestrator.db")
cursor = conn.cursor()

print("Sessions:")
cursor.execute("SELECT id, name, status FROM sessions ORDER BY created_at DESC LIMIT 5")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Name: {row[1]}, Status: {row[2]}")

print("\nLatest Audit Logs:")
cursor.execute("SELECT stage, action, prompt, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 15")
for row in cursor.fetchall():
    print(f"[{row[3]}] Stage: {row[0]}, Action: {row[1]}")
    print(f"  Log: {row[2]}")

conn.close()
