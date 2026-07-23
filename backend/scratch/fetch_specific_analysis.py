import sqlite3

conn = sqlite3.connect("celonis_orchestrator.db")
cursor = conn.cursor()

cursor.execute("SELECT stage, action, prompt, error, timestamp FROM audit_logs WHERE session_id = 'c55c2461-a204-4b57-a0f8-0600bf711219' ORDER BY timestamp DESC LIMIT 20")
rows = cursor.fetchall()
print("Audit Logs:")
for row in rows:
    print(f"[{row[4]}] Stage: {row[0]}, Action: {row[1]}, Prompt: {row[2]}, Error: {row[3]}")

conn.close()
