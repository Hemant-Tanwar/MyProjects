from pycelonis import get_celonis
import re

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
pools = c.data_integration.get_data_pools()
target_pool = [p for p in pools if p.name == "Accounts Payable Direct Push"][0]
master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]

master_id = master_pool.id

# Build a minimal test: just create one view + create one table from it
test_sql = f"""
DROP VIEW IF EXISTS EKKO;
CREATE VIEW EKKO AS SELECT * FROM "{master_id}"."ekko";

DROP VIEW IF EXISTS EKPO;
CREATE VIEW EKPO AS SELECT * FROM "{master_id}"."ekpo";

DROP TABLE IF EXISTS TEMP_TEST_COUNT;
CREATE TABLE TEMP_TEST_COUNT AS
SELECT COUNT(*) AS cnt FROM EKKO;
"""

print("Test SQL:")
print(test_sql)

# Create a test job
for j in target_pool.get_jobs():
    if j.name == "Debug Test Job":
        j.delete()
        break

job = target_pool.create_job(name="Debug Test Job")
job.create_transformation(name="Test Transform", statement=test_sql)

print("\nExecuting...")
try:
    job.execute(wait=True)
    status = job.get_current_execution_status()
    print("Status:", getattr(status, 'status', status))
except Exception as e:
    print("Exception:", e)

# Try to get error log
try:
    err = job._get_execution_detailed_error_log()
    if err:
        print("Error Log:", err[:2000])
except Exception as e:
    print("Could not get error log:", e)

# Check tables
print("\nTables after execution:")
for t in target_pool.get_tables():
    print(f"  {t.name}")

# Cleanup
try:
    job.delete()
except:
    pass
