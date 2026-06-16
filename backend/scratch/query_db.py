import sqlite3

conn = sqlite3.connect("celonis_orchestrator.db")
cursor = conn.cursor()

cursor.execute("SELECT id, name, status, description FROM sessions WHERE id='e2066cf3-c0de-44ab-a808-b2a32a3fc7d7'")
sess = cursor.fetchone()
print("Session details:")
print("ID:", sess[0])
print("Name:", sess[1])
print("Status:", sess[2])
print("Description:", sess[3])

print("\nAudit Logs:")
cursor.execute("SELECT stage, action, prompt FROM audit_logs WHERE session_id='e2066cf3-c0de-44ab-a808-b2a32a3fc7d7' ORDER BY timestamp DESC")
for row in cursor.fetchall():
    print(f"Stage: {row[0]}, Action: {row[1]}")
    print(f"  Log: {row[2]}")
conn.close()
