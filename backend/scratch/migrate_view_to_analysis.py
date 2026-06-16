import sqlite3

def migrate():
    db_path = "/Users/hemanttanwar/Documents/hemant_process_mine/backend/celonis_orchestrator.db"
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Update session status stages
    print("Updating session statuses...")
    cursor.execute("UPDATE sessions SET status = 'analysis_generation' WHERE status = 'view_generation'")
    print(f"  Sessions updated: {cursor.rowcount}")

    # 2. Update artifact stages
    print("Updating artifact stages...")
    cursor.execute("UPDATE artifacts SET stage = 'analysis' WHERE stage = 'view'")
    print(f"  Artifacts updated: {cursor.rowcount}")

    # 3. Update audit log stages and agent names
    print("Updating audit log entries...")
    cursor.execute("UPDATE audit_logs SET stage = 'analysis' WHERE stage = 'view'")
    print(f"  Audit log stages updated: {cursor.rowcount}")

    cursor.execute("UPDATE audit_logs SET agent_name = 'Analysis Agent' WHERE agent_name = 'View Agent'")
    print(f"  Audit log agent names updated: {cursor.rowcount}")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
