import sqlite3

conn = sqlite3.connect("celonis_orchestrator.db")
cursor = conn.cursor()

# Get the latest created session
cursor.execute("SELECT id, name FROM sessions ORDER BY created_at DESC LIMIT 1")
sess = cursor.fetchone()
if sess:
    print(f"Latest Session: {sess[1]} (id={sess[0]})")
    cursor.execute("SELECT stage, action, prompt, error, timestamp FROM audit_logs WHERE session_id = ? ORDER BY timestamp DESC LIMIT 20", (sess[0],))
    rows = cursor.fetchall()
    print("Audit Logs:")
    for row in rows:
        print(f"[{row[4]}] Stage: {row[0]}, Action: {row[1]}, Prompt: {row[2]}, Error: {row[3]}")
else:
    print("No sessions found.")

conn.close()
