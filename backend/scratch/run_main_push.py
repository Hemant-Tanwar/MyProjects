import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel, ArtifactModel
from pycelonis import get_celonis
from app.config import CELONIS_URL, CELONIS_API_TOKEN
import pandas as pd
import re

db = SessionLocal()
try:
    sess = db.query(SessionModel).filter(SessionModel.id == "0abcf69a-09c8-42ed-92b6-7bec79d9de62").first()
    if not sess:
        print("Session not found!")
        sys.exit(1)
        
    stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
    bundle = {}
    for stg in stages:
        art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == sess.id,
            ArtifactModel.stage == stg
        ).order_by(ArtifactModel.version.desc()).first()
        bundle[stg] = art.content if art else ""
        
    print(f"Connecting to Celonis instance: {CELONIS_URL}...")
    celonis = get_celonis(base_url=CELONIS_URL, api_token=CELONIS_API_TOKEN, key_type="USER_KEY")
    
    # 1. Manage Data Pool
    pool_name = sess.name
    print(f"1. Managing Data Pool: {pool_name}")
    pools = celonis.data_integration.get_data_pools()
    data_pool = None
    for p in pools:
        if p.name == pool_name:
            data_pool = p
            break
    if not data_pool:
        data_pool = celonis.data_integration.create_data_pool(name=pool_name)
    print(f"Target Pool Name: {data_pool.name}, ID: {data_pool.id}")
    
    # 2. Get Data Connection
    tables = [t.name.upper() for t in data_pool.get_tables()]
    data_source_id = None
    if "DUMMY_CONNECTION_INIT" not in tables:
        print("No connections exist in target pool. Creating a dummy table to initialize connection...")
        df_dummy = pd.DataFrame({"col": [1]})
        tbl = data_pool.create_table(
            df=df_dummy,
            table_name="DUMMY_CONNECTION_INIT",
            drop_if_exists=True
        )
        data_source_id = tbl.data_source_id
        import time
        time.sleep(5)
    else:
        print("Connection already initialized (DUMMY_CONNECTION_INIT exists).")
        try:
            tbl = data_pool.get_table("DUMMY_CONNECTION_INIT")
            data_source_id = tbl.data_source_id
        except Exception as conn_err:
            print("Failed to get DUMMY_CONNECTION_INIT table connection ID:", conn_err)
    
    print(f"Using connection ID: {data_source_id}")
    
    # 3. Manage Master Data Pool
    master_pool_name = "SAP_Dictionary_Master_Pool"
    print(f"3. Managing Master Data Pool: {master_pool_name}")
    master_pool = None
    for p in pools:
        if p.name == master_pool_name:
            master_pool = p
            break
    if not master_pool:
        master_pool = celonis.data_integration.create_data_pool(name=master_pool_name)
    print(f"Master Pool ID: {master_pool.id}")
    
    master_tables = {t.name.upper(): t for t in master_pool.get_tables()}
    
    sql_content = bundle.get("sql", "")
    if sql_content:
        view_statements = []
        for table_name in master_tables.keys():
            t_upper = table_name.upper()
            if t_upper.startswith("CELONIS_") or t_upper == "DUMMY" or t_upper == "DUMMY_CONNECTION_INIT":
                continue
            view_statements.append(f"DROP VIEW IF EXISTS {t_upper};")
            view_statements.append(f"CREATE VIEW {t_upper} AS SELECT * FROM \"{master_pool.id}\".\"{t_upper}\";")
        
        prefixed_sql = "\n".join(view_statements) + "\n\n" + sql_content
    else:
        prefixed_sql = ""
        
    print(f"SQL transformation statements count: {len(view_statements)}")
    
    # 6. Manage and Execute SQL Job
    print("6. Managing and Executing Data Job...")
    job_name = f"{sess.name} Data Job"
    
    jobs = data_pool.get_jobs()
    for j in jobs:
        if j.name == job_name:
            print(f"Found existing job '{job_name}'. Deleting...")
            j.delete()
            break
            
    print(f"Creating job...")
    data_job = data_pool.create_job(name=job_name)
    
    if prefixed_sql:
        task = data_job.create_transformation(
            name="SQL Transformation",
            description="Auto-generated SQL transformations"
        )
        task.update_statement(prefixed_sql)
        print("SQL statement created and statement updated. Executing job synchronously...")
        try:
            data_job.execute(wait=True)
            print("Execution SUCCESS!")
        except Exception as exec_err:
            print("Execution FAILED:", exec_err)
            try:
                print(data_job._get_execution_detailed_error_log())
            except Exception:
                pass
    
finally:
    db.close()
