import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel, ArtifactModel
from pycelonis import get_celonis
from app.config import CELONIS_URL, CELONIS_API_TOKEN

db = SessionLocal()
try:
    sess = db.query(SessionModel).filter(SessionModel.id == "0abcf69a-09c8-42ed-92b6-7bec79d9de62").first()
    stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
    bundle = {}
    for stg in stages:
        art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == sess.id,
            ArtifactModel.stage == stg
        ).order_by(ArtifactModel.version.desc()).first()
        bundle[stg] = art.content if art else ""
        
    c = get_celonis(base_url=CELONIS_URL, api_token=CELONIS_API_TOKEN, key_type="USER_KEY")
    master_pool = [p for p in c.data_integration.get_data_pools() if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    # 1. From test_views_plus_sql
    master_tables_1 = [t.name.upper() for t in master_pool.get_tables()]
    view_statements_1 = []
    for table_name in master_tables_1:
        t_upper = table_name.upper()
        if t_upper.startswith("CELONIS_") or t_upper == "DUMMY" or t_upper == "DUMMY_CONNECTION_INIT":
            continue
        view_statements_1.append(f"DROP VIEW IF EXISTS {t_upper};")
        view_statements_1.append(f"CREATE VIEW {t_upper} AS SELECT * FROM \"{master_pool.id}\".\"{t_upper}\";")
    sql_1 = "\n".join(view_statements_1) + "\n\n" + bundle["sql"]
    
    # 2. From run_main_push.py
    master_tables_2 = {t.name.upper(): t for t in master_pool.get_tables()}
    view_statements_2 = []
    for table_name in master_tables_2.keys():
        t_upper = table_name.upper()
        if t_upper.startswith("CELONIS_") or t_upper == "DUMMY" or t_upper == "DUMMY_CONNECTION_INIT":
            continue
        view_statements_2.append(f"DROP VIEW IF EXISTS {t_upper};")
        view_statements_2.append(f"CREATE VIEW {t_upper} AS SELECT * FROM \"{master_pool.id}\".\"{t_upper}\";")
    sql_2 = "\n".join(view_statements_2) + "\n\n" + bundle["sql"]
    
    print("Length of sql_1 (test_views_plus_sql):", len(sql_1))
    print("Length of sql_2 (run_main_push):", len(sql_2))
    print("Are they identical?", sql_1 == sql_2)
    if sql_1 != sql_2:
        print("Diff:")
        import difflib
        print("".join(difflib.unified_diff(sql_1.splitlines(keepends=True), sql_2.splitlines(keepends=True))))
finally:
    db.close()
