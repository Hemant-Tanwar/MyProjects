import os
import re
import json
import logging
import yaml
import time
import pandas as pd
from pycelonis import get_celonis
from app.config import CELONIS_URL, CELONIS_API_TOKEN
from app.database import SessionModel, ArtifactModel, AuditLogModel

logger = logging.getLogger(__name__)

def log_progress(db, sess_id, stage, action, msg):
    logger.info(msg)
    if db:
        try:
            log = AuditLogModel(
                session_id=sess_id,
                stage=stage,
                agent_name="Celonis Deployer",
                action=action,
                prompt=msg
            )
            db.add(log)
            db.commit()
        except Exception as log_err:
            logger.error(f"Failed to log promote progress: {log_err}")

def get_celonis_connection(db, sess_id, stage):
    log_progress(db, sess_id, stage, "celonis_connect", "Connecting to Celonis platform...")
    return get_celonis(base_url=CELONIS_URL, api_token=CELONIS_API_TOKEN, key_type="USER_KEY")

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return text.strip('_')

import urllib.request
from html.parser import HTMLParser

class LeanXParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cells = []
        self.current_cell = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.cells = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.in_row = False
            if self.cells:
                self.rows.append(self.cells)
        elif tag == "td" and self.in_row:
            self.in_cell = False
            self.cells.append(" ".join(self.current_cell).strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())

_LEANX_SCHEMA_CACHE = {}

def get_leanx_schema(table_name: str, db=None, sess_id=None, stage=None) -> dict:
    t_name = table_name.lower()
    if t_name in _LEANX_SCHEMA_CACHE:
        return _LEANX_SCHEMA_CACHE[t_name]

    url = f"https://leanx.eu/sap/table/{t_name}"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    try:
        if db and sess_id and stage:
            log_progress(db, sess_id, stage, "leanx_schema_fetch", f"Fetching schema for {table_name.upper()} from LeanX...")
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            parser = LeanXParser()
            parser.feed(html)
            
            schema = {}
            for r in parser.rows:
                if len(r) >= 5:
                    first_cell = r[0]
                    words = first_cell.split()
                    if not words:
                        continue
                    col_name = words[0].upper()
                    if re.match(r'^[A-Z0-9_\/]{2,30}$', col_name):
                        data_type_words = r[3].split()
                        data_type = data_type_words[0].upper() if data_type_words else "CHAR"
                        
                        length_words = r[4].split()
                        length = length_words[0] if length_words else "10"
                        
                        schema[col_name] = {
                            "type": data_type,
                            "length": length
                        }
            _LEANX_SCHEMA_CACHE[t_name] = schema
            if db and sess_id and stage:
                log_progress(db, sess_id, stage, "leanx_schema_success", f"Successfully synced schema for {table_name.upper()} from LeanX with {len(schema)} columns.")
            return schema
    except Exception as e:
        logger.warning(f"Failed to fetch LeanX schema for {table_name}: {e}")
        if db and sess_id and stage:
            log_progress(db, sess_id, stage, "leanx_schema_failed", f"Warning: Could not fetch schema for {table_name.upper()} from LeanX: {e}. Falling back to default types.")
        return {}

def cast_dataframe_to_leanx_schema(table_name: str, df: pd.DataFrame, db=None, sess_id=None, stage=None) -> pd.DataFrame:
    schema = get_leanx_schema(table_name, db, sess_id, stage)
    if not schema:
        return df

    df_copy = df.copy()
    for col in df_copy.columns:
        col_upper = col.upper()
        if col_upper in schema:
            sap_type = schema[col_upper]["type"]
            try:
                # ── 1. Float / Decimal / Currency ────────────────────────────
                if sap_type in ["DEC", "CURR", "QUAN", "FLTP"]:
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').astype('float64')
                # ── 2. Integer / Numeric count ────────────────────────────────
                elif sap_type in ["INT1", "INT2", "INT4"]:
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').astype('Int64')
                # ── 3. Date / Timestamp ───────────────────────────────────────
                elif sap_type == "DATS":
                    df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                # ── 4. String / Varchar (CLNT, CHAR, NUMC, TIMS, LANG, CUKY, UNIT) ──
                else:
                    df_copy[col] = df_copy[col].astype(str)
                    df_copy[col] = df_copy[col].replace({'nan': None, '<NA>': None, 'None': None, '': None})
                    df_copy[col] = df_copy[col].where(pd.notnull(df_copy[col]), None)
            except Exception as cast_err:
                logger.warning(f"Failed to cast column {col} in table {table_name} to {sap_type}: {cast_err}")
    return df_copy

def normalize_temp_tables(sql: str) -> str:
    sql = re.sub(r'CREATE\s+(?:TEMPORARY\s+)?VIEW\s+([a-zA-Z0-9_]+)\s+AS', r'CREATE TABLE \1 AS', sql, flags=re.IGNORECASE)
    sql = re.sub(r'DROP\s+VIEW\s+IF\s+EXISTS\s+([a-zA-Z0-9_]+)', r'DROP TABLE IF EXISTS \1', sql, flags=re.IGNORECASE)
    return sql

def extract_table_columns_from_sql(sql_content: str) -> dict:
    import re
    table_to_cols = {}
    
    if not sql_content:
        return table_to_cols
        
    # Find all target tables created in the SQL to exclude them from columns
    target_tables = set()
    target_pattern = re.compile(r'\bCREATE\s+(?:TEMPORARY\s+)?(?:TABLE|VIEW)\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
    for m in target_pattern.finditer(sql_content):
        target_tables.add(m.group(1).upper())
        
    # Find all aliases defined in SELECT list (AS alias) to exclude them
    select_aliases = set()
    as_pattern = re.compile(r'\bAS\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
    for m in as_pattern.finditer(sql_content):
        alias_upper = m.group(1).upper()
        if alias_upper not in ["TIMESTAMP", "VARCHAR", "INT", "DATE", "DOUBLE", "FLOAT", "STRING", "CHAR"]:
            select_aliases.add(alias_upper)
        
    # Split SQL into select blocks
    statements = sql_content.split(';')
    blocks = []
    for stmt in statements:
        stmt_clean = stmt.strip()
        if not stmt_clean:
            continue
        union_blocks = re.split(r'\bUNION\s+(?:ALL\s+)?', stmt_clean, flags=re.IGNORECASE)
        for ub in union_blocks:
            ub_clean = ub.strip()
            if ub_clean:
                blocks.append(ub_clean)
                
    SQL_KEYWORDS = {
        "SELECT", "FROM", "JOIN", "ON", "WHERE", "AND", "OR", "UNION", "ALL", "AS", 
        "CREATE", "TABLE", "VIEW", "TEMPORARY", "TEMP", "DROP", "IF", "EXISTS", "CAST", 
        "TIMESTAMP", "NULL", "IN", "NOT", "IS", "LEFT", "RIGHT", "INNER", "OUTER", 
        "CROSS", "USING", "GROUP", "BY", "ORDER", "LIMIT", "CASE", "WHEN", "THEN", 
        "ELSE", "END", "LIKE", "DISTINCT", "AVG", "SUM", "COUNT", "MAX", "MIN",
        "COALESCE", "SUBSTRING", "ROUND", "UPPER", "LOWER", "CONCAT", "DATE",
        "VARCHAR", "INSERT", "INTO", "TRIM", "NULLIF", "TO_TIMESTAMP", "DECIMAL",
        "BIGINT", "TO_DATE", "TO_CHAR", "INT", "DOUBLE", "FLOAT", "STRING", "CHAR",
        "VALUES", "DELETE", "UPDATE", "SET", "ALTER", "ADD", "COLUMN", "DEFAULT",
        "KEY", "PRIMARY", "FOREIGN", "REFERENCES", "UNIQUE", "CHECK", "INDEX",
        "TRUE", "FALSE", "BOOLEAN", "CASE_ID", "ACTIVITY", "SORTING", "CURRENT_DATE"
    }

    for block in blocks:
        # Strip string literals to avoid matching words inside quotes
        block_no_literals = re.sub(r"'[^']*'", "", block)
        block_clean = re.sub(r'\s+', ' ', block_no_literals)
        
        # 1. Extract table names in this block
        table_pattern = re.compile(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
        block_tables = []
        alias_to_table = {}
        
        for m in table_pattern.finditer(block_clean):
            t_upper = m.group(1).upper()
            if t_upper.startswith("TEMP_"):
                continue
            block_tables.append(t_upper)
            alias_to_table[t_upper] = t_upper
            if t_upper not in table_to_cols:
                table_to_cols[t_upper] = set()
                
            # Find aliases of this table in the block
            alias_pattern = re.compile(rf'\b{t_upper}\s+(?:AS\s+)?([a-zA-Z0-9_]+)\b', re.IGNORECASE)
            for am in alias_pattern.finditer(block_clean):
                alias = am.group(1).upper()
                if alias not in ["ON", "WHERE", "JOIN", "GROUP", "ORDER", "SELECT", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "USING", "AS"]:
                    alias_to_table[alias] = t_upper

        if not block_tables:
            continue
            
        # 2. Extract prefixed columns in this block
        col_pattern = re.compile(r'\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b')
        for match in col_pattern.finditer(block_clean):
            prefix, col = match.groups()
            p_upper = prefix.upper()
            col_upper = col.upper()
            if p_upper in alias_to_table:
                real_table = alias_to_table[p_upper]
                if col_upper not in select_aliases and col_upper not in target_tables:
                    table_to_cols[real_table].add(col_upper)

        # 3. Extract prefix-less words as potential columns in this block
        sql_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', block_clean)
        potential_cols = set()
        for word in sql_words:
            w_upper = word.upper()
            if w_upper in SQL_KEYWORDS:
                continue
            if w_upper in alias_to_table:
                continue
            if w_upper.startswith("TEMP_"):
                continue
            if w_upper in select_aliases:
                continue
            if w_upper in target_tables:
                continue
            potential_cols.add(w_upper)
            
        # Associate potential cols with all tables found in this block
        for col in potential_cols:
            for t_name in block_tables:
                table_to_cols[t_name].add(col)

    # Ensure every table has at least MANDT if no columns were parsed
    for t_name in table_to_cols:
        if not table_to_cols[t_name]:
            table_to_cols[t_name].add("MANDT")
            
    return table_to_cols


# SAP column name patterns that indicate a NUMERIC (INT/FLOAT) data type.
# Any column matching these patterns will get integer/float sample values
# so that CAST(column AS BIGINT/DECIMAL) never raises CAST_INVALID_INPUT.
_NUMERIC_SUFFIXES = (
    "netwr", "netpr", "dmbtr", "wrbtr", "kwmeng", "menge",
    "amount", "price", "qty", "quantity", "value", "betr",
    "taxwr", "peinh", "prsfd", "stprs",
    "anzah", "zzpozic", "zzpoze",
)
_NUMERIC_CONTAINS = ("amt", "_qty", "_val", "_cnt", "_num", "count",
                     "_rate", "_pct", "_amount", "_value", "_price",
                     "po_amount", "so_amount")
_DATE_SUFFIXES = ("dat", "time", "dt", "ts", "date", "timestamp",
                  "budat", "cpudt", "aedat", "erdat", "bldat",
                  "event_time", "eventtime", "create_date")

def generate_sample_data(columns: list, row_count: int = 5) -> pd.DataFrame:
    """Generate realistic SAP-style sample data for a list of column names.

    Key safety rule: unknown columns default to *integers* (not strings like
    'VAL_1') so that SQL CAST(col AS BIGINT / DECIMAL) never raises
    CAST_INVALID_INPUT in the Celonis/Vertica engine.
    """
    import datetime

    data = {}
    base_time = datetime.datetime(2026, 1, 1, 8, 0, 0)

    for col in columns:
        col_lower = col.lower()
        col_values = []

        # ── Detect column semantic type ───────────────────────────────────────
        is_numeric = (
            any(col_lower.endswith(s) for s in _NUMERIC_SUFFIXES)
            or any(s in col_lower for s in _NUMERIC_CONTAINS)
        )
        is_date = any(s in col_lower for s in _DATE_SUFFIXES)

        # SAP document-number fields (stored as zero-padded strings)
        is_doc_nr = col_lower in (
            "vbeln", "ebeln", "belnr", "aufnr", "matnr",
            "case_key", "objectid", "objnr", "rsnum"
        )
        is_pos_nr = col_lower in ("posnr", "ebelp", "posnn", "buzei")

        # SAP key fields that are string-valued codes
        is_str_code = col_lower in (
            "mandt", "bukrs", "werks", "lgort", "land1",
            "waers", "bwart", "bwkey", "bklas", "ktosl",
            "gbstk", "lifnr", "kunnr", "ekorg", "ekgrp",
            "meins", "labst", "sobkz", "lgtyp", "lgpla",
            "objectclas", "tcode", "tdobject", "activity",
            "activity_name", "user_name", "username",
            "auart", "augru", "mvgr1",
        )

        for i in range(row_count):
            # --- specific field rules ---
            if col_lower == "mandt":
                col_values.append("800")
            elif col_lower == "objectclas":
                col_values.append("VERKBELEG")
            elif col_lower in ("gbstk",):
                col_values.append("A" if i == 0 else "C")
            elif col_lower == "bwart":
                col_values.append("601" if i % 2 == 0 else "602")
            elif col_lower in ("activity", "activity_name"):
                activities = ["Create Order", "Approve Order",
                               "Pick Goods", "Ship Goods", "Create Invoice"]
                col_values.append(activities[i % len(activities)])
            elif col_lower in ("user_name", "username"):
                users = ["SYSTEM", "JSMITH", "AMULLER", "SYSTEM", "KPATEL"]
                col_values.append(users[i % len(users)])
            elif col_lower in ("land1",):
                col_values.append(["DE", "US", "FR", "GB", "IN"][i % 5])
            elif col_lower in ("waers",):
                col_values.append("EUR")
            # --- document number (zero-padded string) ---
            elif is_doc_nr:
                col_values.append(f"{10000000 + i + 1:010d}")
            elif is_pos_nr:
                col_values.append(f"{(i + 1) * 10:06d}")
            # --- date / timestamp ---
            elif is_date:
                ts = base_time + datetime.timedelta(days=i, hours=i * 2)
                col_values.append(ts.strftime("%Y-%m-%d %H:%M:%S"))
            # --- string-valued SAP code fields ---
            elif is_str_code:
                col_values.append(f"CODE{i + 1}")
            # --- numeric value fields ---
            elif is_numeric:
                col_values.append(round(100.0 + i * 25.5, 2))
            # ── SAFE DEFAULT: integer, NOT 'VAL_N' string ─────────────────────
            # Using an integer means CAST(col AS BIGINT / DECIMAL) always
            # succeeds in the Celonis/Vertica transformation engine.
            else:
                col_values.append(i)   # 0, 1, 2, 3, 4 — safe for any numeric CAST

        data[col] = col_values

    return pd.DataFrame(data)

def deploy_sql(sess: SessionModel, sql_content: str, db) -> str:
    """
    Normalizes view creation, uploads CSV source files, creates/runs the Data Job.
    If it fails, triggers self-correction loop.
    Returns the final successful/corrected SQL.
    """
    stage = "sql"
    celonis = get_celonis_connection(db, sess.id, stage)
    
    # 1. Manage Data Pool
    pool_name = sess.name
    log_progress(db, sess.id, stage, "pool_management", f"Managing Data Pool: {pool_name}...")
    pools = celonis.data_integration.get_data_pools()
    data_pool = None
    for p in pools:
        if p.name == pool_name:
            data_pool = p
            break
    if not data_pool:
        data_pool = celonis.data_integration.create_data_pool(name=pool_name)
        
    # 2. Upload CSVs and create/extend tables
    data_source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data_source")
    if not os.path.exists(data_source_dir):
        data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"
        
    table_to_cols = extract_table_columns_from_sql(sql_content)
    
    log_progress(db, sess.id, stage, "csv_upload", f"Syncing tables and columns to pool '{pool_name}'...")
    pool_tables = {t.name.upper(): t for t in data_pool.get_tables()}
    
    for t_name, req_cols in table_to_cols.items():
        t_upper = t_name.upper()
        if t_upper.startswith("TEMP_"):
            continue
            
        csv_filename = f"{t_upper}.csv"
        csv_path = os.path.join(data_source_dir, csv_filename) if os.path.exists(data_source_dir) else None
        has_csv = csv_path and os.path.exists(csv_path)
        
        if t_upper not in pool_tables:
            # Table does not exist in Celonis
            if has_csv:
                try:
                    df = pd.read_csv(csv_path)
                    df.columns = [c.upper() for c in df.columns]
                    df = df.where(pd.notnull(df), None)
                    # Cast table to match SAP types from LeanX
                    df = cast_dataframe_to_leanx_schema(t_upper, df, db, sess.id, stage)
                    # Upload table exactly as it exists in the CSV
                    data_pool.create_table(df=df, table_name=t_upper, drop_if_exists=True)
                    pool_tables[t_upper] = True
                    log_progress(db, sess.id, stage, "csv_uploaded", f"Uploaded table {t_upper} successfully.")
                except Exception as upload_err:
                    log_progress(db, sess.id, stage, "csv_failed", f"Error: Failed to upload required table {t_upper} from CSV: {upload_err}")
                    raise Exception(f"Failed to upload required table {t_upper} from CSV: {upload_err}")
            else:
                try:
                    df_mock = generate_sample_data(list(req_cols), 5)
                    # Cast mock table to match SAP types from LeanX
                    df_mock = cast_dataframe_to_leanx_schema(t_upper, df_mock, db, sess.id, stage)
                    data_pool.create_table(df=df_mock, table_name=t_upper, drop_if_exists=True)
                    pool_tables[t_upper] = True
                    log_progress(db, sess.id, stage, "mock_created", f"Created mock table {t_upper} with {len(req_cols)} columns successfully.")
                except Exception as mock_err:
                    log_progress(db, sess.id, stage, "mock_failed", f"Error: Could not create mock for required table {t_upper}: {mock_err}")
                    raise Exception(f"Failed to create mock for required table {t_upper}: {mock_err}")
        else:
            # Table exists in Celonis. Do not check or alter the table.
            pass


                
    # 4. Normalize and Execute transformations
    final_sql = normalize_temp_tables(sql_content)
    max_retries = 10
    current_sql = final_sql
    
    for attempt in range(1, max_retries + 1):
        if not current_sql:
            break
        job_name = f"{sess.name} Data Job"
        log_progress(db, sess.id, stage, "data_job", f"Executing Data Job: {job_name} (Attempt {attempt}/{max_retries})...")
        
        for j in data_pool.get_jobs():
            if j.name == job_name:
                try:
                    j.delete()
                except Exception:
                    pass
                break
        data_job = data_pool.create_job(name=job_name)
        
        # Split current SQL, combine DROP TABLE with subsequent statement, and create transformations
        import re
        raw_statements = [stmt.strip() for stmt in current_sql.split(";") if stmt.strip()]
        sql_statements = []
        skip_next = False
        for i in range(len(raw_statements)):
            if skip_next:
                skip_next = False
                continue
            stmt = raw_statements[i]
            if stmt.upper().startswith("DROP TABLE") and i + 1 < len(raw_statements):
                combined = f"{stmt};\n{raw_statements[i+1]}"
                sql_statements.append(combined)
                skip_next = True
            else:
                sql_statements.append(stmt)
                
        for idx, stmt in enumerate(sql_statements):
            stmt_num = str(idx + 1).zfill(2)
            stmt_name = "Query"
            stmt_upper = stmt.upper()
            if "CREATE TABLE" in stmt_upper:
                match = re.search(r"CREATE TABLE\s+(\w+)", stmt, re.IGNORECASE)
                stmt_name = f"Create {match.group(1).upper()}" if match else "Create Table"
            elif "DROP TABLE" in stmt_upper:
                match = re.search(r"DROP TABLE\s+(?:IF EXISTS\s+)?(\w+)", stmt, re.IGNORECASE)
                stmt_name = f"Drop {match.group(1).upper()}" if match else "Drop Table"
            elif "INSERT INTO" in stmt_upper:
                match = re.search(r"INSERT INTO\s+(\w+)", stmt, re.IGNORECASE)
                target_tbl = match.group(1).upper() if match else "Table"
                act_match = re.search(r"'\s*([^']+)\s*'\s+AS\s+ACTIVITY", stmt, re.IGNORECASE)
                if act_match:
                    act_name = act_match.group(1)
                    stmt_name = f"Insert {target_tbl} - {act_name}"
                else:
                    stmt_name = f"Insert {target_tbl}"
            
            task = data_job.create_transformation(
                name=f"{stmt_num} - {stmt_name}", 
                description=f"Auto-generated step {stmt_num}"
            )
            # Add terminating semicolon if not present
            task_stmt = stmt if stmt.endswith(";") else f"{stmt};"
            task.update_statement(task_stmt)
        
        try:
            data_job.execute(wait=True)
            status_obj = data_job.get_current_execution_status()
            status_str = getattr(status_obj, "status", str(status_obj))
            log_progress(db, sess.id, stage, "execution_status", f"Job status: {status_str}")
            
            if "success" in status_str.lower():
                # Success! Save lesson learned to memory database
                try:
                    from app.agents.sql_agent import TransformationSQLAgent
                    sql_agent = TransformationSQLAgent()
                    sql_agent.save_lesson(
                        stage="sql",
                        requirement=sess.description or "",
                        error="None (Successful Run)",
                        fix_output=current_sql,
                        rationale="SQL executed successfully on Celonis database."
                    )
                except Exception as save_err:
                    logger.error(f"Failed to save successful SQL lesson: {save_err}")
                return current_sql
            else:
                raise Exception(f"SQL execution status not successful: {status_str}")
        except Exception as e:
            log_progress(db, sess.id, stage, "execution_failed", f"Attempt {attempt} failed: {e}")
            detailed_error = ""
            try:
                detailed_error = str(data_job._get_execution_detailed_error_log())
            except Exception as log_err:
                detailed_error = f"Could not fetch detailed Celonis error log: {log_err}"
            combined_error = f"{e}\n{detailed_error}"
            
            if attempt == max_retries:
                raise Exception(f"SQL execution failed after {max_retries} attempts. Last error: {combined_error}")
            
            # Self-correction loop
            log_progress(db, sess.id, stage, "self_correction", "Triggering Transformation SQL Agent self-correction loop...")
            from app.agents.sql_agent import TransformationSQLAgent
            sql_agent = TransformationSQLAgent()
            
            # Find requirement from latest artifact
            latest_req = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == sess.id,
                ArtifactModel.stage == "requirement"
            ).order_by(ArtifactModel.version.desc()).first()
            req_spec = latest_req.content if latest_req else sess.description or ""
            
            rationale, corrected_sql = sql_agent.fix_error(req_spec, current_sql, combined_error)
            log_progress(db, sess.id, stage, "corrected_sql_received", f"SQL Agent correction rationale: {rationale}")
            
            # Save corrected SQL back to DB as a new version
            try:
                last_art = db.query(ArtifactModel).filter(
                    ArtifactModel.session_id == sess.id,
                    ArtifactModel.stage == "sql"
                ).order_by(ArtifactModel.version.desc()).first()
                new_version = (last_art.version + 1) if last_art else 1
                
                new_art = ArtifactModel(
                    session_id=sess.id,
                    stage="sql",
                    version=new_version,
                    content=corrected_sql,
                    approved=False
                )
                db.add(new_art)
                db.commit()
                
                # Save lesson to memory database
                sql_agent.save_lesson(
                    stage="sql",
                    requirement=req_spec,
                    error=combined_error,
                    fix_output=corrected_sql,
                    rationale=rationale
                )
            except Exception as db_err:
                logger.error(f"Failed to save corrected SQL to DB: {db_err}")
                
            current_sql = normalize_temp_tables(corrected_sql)
            
    return current_sql

def deploy_data_model(sess: SessionModel, data_model_content: str, db) -> str:
    """
    Creates/maps Data Model, links event/case tables, reloads the model.
    If it fails, triggers self-correction loop.
    """
    stage = "data_model"
    celonis = get_celonis_connection(db, sess.id, stage)
    
    # Get pool
    pool_name = sess.name
    pools = celonis.data_integration.get_data_pools()
    data_pool = None
    for p in pools:
        if p.name == pool_name:
            data_pool = p
            break
    if not data_pool:
        data_pool = celonis.data_integration.create_data_pool(name=pool_name)
        
    latest_sql_art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == sess.id,
        ArtifactModel.stage == "sql"
    ).order_by(ArtifactModel.version.desc()).first()
    sql_text = latest_sql_art.content if latest_sql_art else ""
    
    max_dm_retries = 10
    current_dm_json = data_model_content
    
    for dm_attempt in range(1, max_dm_retries + 1):
        try:
            try:
                dm_obj = json.loads(current_dm_json)
            except Exception:
                dm_obj = {}
                
            dm_name = f"{sess.name} Data Model"
            log_progress(db, sess.id, stage, "data_model_setup", f"Managing Data Model: {dm_name} (Attempt {dm_attempt}/{max_dm_retries})...")
            
            data_models = data_pool.get_data_models()
            data_model = None
            for dm in data_models:
                if dm.name == dm_name:
                    data_model = dm
                    break
            if not data_model:
                data_model = data_pool.create_data_model(name=dm_name)
                
            # Load tables defined in the JSON configuration
            dm_tables = data_model.get_tables()
            dm_table_names = [t.name.upper() for t in dm_tables]
            
            # Fetch all actual tables currently existing in the Celonis Data Pool
            pool_tables = {t.name.upper() for t in data_pool.get_tables()}
            
            # Remove any table currently in the data model that is NOT present in the data pool
            for t in dm_tables:
                t_name_upper = t.name.upper()
                if t_name_upper not in pool_tables:
                    try:
                        t.delete()
                        log_progress(db, sess.id, stage, "table_removed", f"Removed table '{t.name}' from Data Model because it does not exist in the Data Pool.")
                        if t_name_upper in dm_table_names:
                            dm_table_names.remove(t_name_upper)
                    except Exception as t_del_err:
                        logger.warning(f"Could not delete table {t.name} from Data Model: {t_del_err}")
            
            for table_spec in dm_obj.get("tables", []):
                tname = table_spec.get("name", "").upper()
                # ONLY add the table to the Data Model if it exists in the Data Pool
                if tname in pool_tables:
                    if tname not in dm_table_names:
                        try:
                            data_model.add_table(name=tname)
                            dm_table_names.append(tname)
                        except Exception as t_err:
                            log_progress(db, sess.id, stage, "add_table_failed", f"Warning: Could not add table {tname} to Data Model: {t_err}")
                else:
                    log_progress(db, sess.id, stage, "table_skipped", f"Skipping configuration for table '{tname}' because it does not exist in the Data Pool.")
                        
            # Configure Event and Case mapping dynamically from the JSON
            event_table_name = dm_obj.get("event_table", "").upper()
            case_table_name = dm_obj.get("case_table", "").upper()
            dm_tables_dict = {t.name.upper(): t for t in data_model.get_tables()}
            
            event_table = dm_tables_dict.get(event_table_name)
            case_table = dm_tables_dict.get(case_table_name)
            
            # Clean and recreate foreign keys from relationships defined in JSON
            try:
                for fk in data_model.get_foreign_keys():
                    fk.delete()
            except Exception as fk_del_err:
                logger.warning(f"Could not delete existing foreign keys: {fk_del_err}")
                
            for rel in dm_obj.get("relationships", []):
                src_name = rel.get("source_table", "").upper()
                tgt_name = rel.get("target_table", "").upper()
                
                # Only create relationships if both tables actually exist in the Data Model
                if src_name not in dm_tables_dict or tgt_name not in dm_tables_dict:
                    continue
                
                src_cols = rel.get("source_columns") or rel.get("source_column")
                tgt_cols = rel.get("target_columns") or rel.get("target_column")
                
                if isinstance(src_cols, str):
                    src_cols = [src_cols]
                if isinstance(tgt_cols, str):
                    tgt_cols = [tgt_cols]
                
                src_t = dm_tables_dict.get(src_name)
                tgt_t = dm_tables_dict.get(tgt_name)
                
                if src_t and tgt_t and src_cols and tgt_cols and len(src_cols) == len(tgt_cols):
                    cols_pairs = list(zip(src_cols, tgt_cols))
                    try:
                        data_model.create_foreign_key(
                            source_table_id=src_t.id,
                            target_table_id=tgt_t.id,
                            columns=cols_pairs
                        )
                    except Exception as fk_err:
                        logger.warning(f"Failed to create foreign key {src_name} -> {tgt_name} with columns {cols_pairs}: {fk_err}")
            
            # Configure process configurations dynamically
            if event_table and case_table:
                case_id_col = None
                for rel in dm_obj.get("relationships", []):
                    src_name = rel.get("source_table", "").upper()
                    tgt_name = rel.get("target_table", "").upper()
                    if src_name == case_table_name and tgt_name == event_table_name:
                        case_id_col = rel.get("target_column")
                        break
                    elif src_name == event_table_name and tgt_name == case_table_name:
                        case_id_col = rel.get("source_column")
                        break
                        
                if not case_id_col:
                    case_id_col = "CASE_ID"
                    
                try:
                    event_cols = {c.name.upper() for c in event_table.get_columns()}
                except Exception:
                    event_cols = set()
                
                act_col = "ACTIVITY"
                for c in event_cols:
                    if c in ["ACTIVITY", "ACTIVITY_NAME", "ACT"]:
                        act_col = c
                        break
                        
                time_col = "EVENT_TIME"
                for c in event_cols:
                    if c in ["EVENT_TIME", "TIMESTAMP", "TIME", "EVENTTIME"]:
                        time_col = c
                        break
                        
                sort_col = None
                for c in event_cols:
                    if c in ["SORT_INDEX", "SORT", "INDEX"]:
                        sort_col = c
                        break
                
                try:
                    for conf in data_model.get_process_configurations():
                        conf.delete()
                except Exception as pc_del_err:
                    logger.warning(f"Could not delete process config: {pc_del_err}")
                    
                try:
                    data_model.create_process_configuration(
                        activity_table_id=event_table.id,
                        case_id_column=case_id_col,
                        activity_column=act_col,
                        timestamp_column=time_col,
                        sorting_column=sort_col,
                        case_table_id=case_table.id
                    )
                except Exception as pc_err:
                    logger.warning(f"Could not build process config: {pc_err}")
            
            log_progress(db, sess.id, stage, "reloading_data_model", "Reloading Data Model...")
            data_model.reload(wait=True)
            log_progress(db, sess.id, stage, "reload_success", "Data Model reloaded successfully.")
            
            # Save success to lessons learned
            try:
                from app.agents.data_model_agent import DataModelAgent
                dm_agent = DataModelAgent()
                dm_agent.save_lesson(
                    stage="data_model",
                    requirement=sess.description or "",
                    error="None (Successful Run)",
                    fix_output=current_dm_json,
                    rationale="Data model successfully configured and reloaded."
                )
            except Exception as save_err:
                logger.error(f"Failed to save successful data model lesson: {save_err}")
                
            return current_dm_json
            
        except Exception as e:
            log_progress(db, sess.id, stage, "data_model_failed", f"Attempt {dm_attempt} failed: {e}")
            
            # Check if this error is related to table data or schema issues (duplicates, columns, tables)
            err_msg_lower = str(e).lower()
            if any(k in err_msg_lower for k in ["duplicate", "primary key", "key violation", "column", "table", "not found", "exist", "cast", "malformed"]):
                log_progress(db, sess.id, stage, "data_model_sql_feedback", f"Data Model reload failed due to table data/schema issue. Routing feedback to SQL Agent on-the-fly...")
                try:
                    from app.agents.sql_agent import TransformationSQLAgent
                    sql_agent = TransformationSQLAgent()
                    
                    latest_req = db.query(ArtifactModel).filter(
                        ArtifactModel.session_id == sess.id,
                        ArtifactModel.stage == "requirement"
                    ).order_by(ArtifactModel.version.desc()).first()
                    req_spec = latest_req.content if latest_req else sess.description or ""
                    
                    # Fix SQL
                    sql_rationale, corrected_sql = sql_agent.fix_error(req_spec, sql_text, str(e))
                    log_progress(db, sess.id, stage, "sql_refixed_by_dm_feedback", f"SQL Agent updated transformations. Rationale: {sql_rationale}")
                    
                    # Update SQL artifact in database
                    last_sql_art = db.query(ArtifactModel).filter(
                        ArtifactModel.session_id == sess.id,
                        ArtifactModel.stage == "sql"
                    ).order_by(ArtifactModel.version.desc()).first()
                    new_sql_version = (last_sql_art.version + 1) if last_sql_art else 1
                    
                    new_sql_art = ArtifactModel(
                        session_id=sess.id,
                        stage="sql",
                        version=new_sql_version,
                        content=corrected_sql,
                        rationale=sql_rationale,
                        approved=False
                    )
                    db.add(new_sql_art)
                    db.commit()
                    
                    # Re-deploy SQL
                    sql_text = corrected_sql
                    deploy_sql(sess, corrected_sql, db)
                    
                    # Retry the data model configuration with the newly deployed tables
                    continue
                except Exception as sql_fix_err:
                    log_progress(db, sess.id, stage, "sql_refix_failed", f"SQL Agent self-correction loop failed: {sql_fix_err}")
            
            if dm_attempt == max_dm_retries:
                raise e
                
            # Self-healing loop
            from app.agents.data_model_agent import DataModelAgent
            dm_agent = DataModelAgent()
            
            latest_req = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == sess.id,
                ArtifactModel.stage == "requirement"
            ).order_by(ArtifactModel.version.desc()).first()
            req_spec = latest_req.content if latest_req else sess.description or ""
            
            rationale, corrected_dm = dm_agent.fix_error(req_spec, sql_text, current_dm_json, str(e))
            log_progress(db, sess.id, stage, "data_model_healed", f"Data Model healed. Rationale: {rationale}")
            
            try:
                last_art = db.query(ArtifactModel).filter(
                    db.query(ArtifactModel).filter(
                        ArtifactModel.session_id == sess.id,
                        ArtifactModel.stage == "data_model"
                    )
                ).order_by(ArtifactModel.version.desc()).first()
                new_version = (last_art.version + 1) if last_art else 1
                
                new_art = ArtifactModel(
                    session_id=sess.id,
                    stage="data_model",
                    version=new_version,
                    content=corrected_dm,
                    approved=False
                )
                db.add(new_art)
                db.commit()
                
                # Save lesson to memory database
                dm_agent.save_lesson(
                    stage="data_model",
                    requirement=req_spec,
                    error=str(e),
                    fix_output=corrected_dm,
                    rationale=rationale
                )
            except Exception as db_err:
                logger.error(f"Failed to save corrected Data Model: {db_err}")
                
            current_dm_json = corrected_dm
            
    return current_dm_json

def deploy_knowledge_model(sess: SessionModel, km_content: str, db) -> str:
    """
    Creates Packages, links Data Models variables, uploads Knowledge Model YAML configurations.
    """
    stage = "knowledge_model"
    celonis = get_celonis_connection(db, sess.id, stage)
    
    # Get Data Model ID
    pool_name = sess.name
    pools = celonis.data_integration.get_data_pools()
    data_pool = None
    for p in pools:
        if p.name == pool_name:
            data_pool = p
            break
    if not data_pool:
        raise Exception(f"Data Pool {pool_name} not found.")
        
    dm_name = f"{sess.name} Data Model"
    data_model = None
    for dm in data_pool.get_data_models():
        if dm.name == dm_name:
            data_model = dm
            break
    if not data_model:
        raise Exception(f"Data Model {dm_name} not found.")
        
    # Manage Space
    space_name = f"{sess.name} Space"
    log_progress(db, sess.id, stage, "space_management", f"Managing Space: {space_name}...")
    spaces = celonis.studio.get_spaces()
    space = None
    for s in spaces:
        if s.name == space_name:
            space = s
            break
    if not space:
        space = celonis.studio.create_space(name=space_name)
        
    # Manage Package
    pkg_name = f"{sess.name} Package"
    pkg_key = f"{slugify(sess.name).replace('_', '-')}-{sess.id[:8]}"
    log_progress(db, sess.id, stage, "package_management", f"Managing Package: {pkg_name}...")
    packages = space.get_packages()
    package = None
    for p in packages:
        if p.name == pkg_name or p.key == pkg_key:
            package = p
            break
    if package:
        pkg_key = package.key
    else:
        # Create package. If key conflict, try with timestamp
        try:
            package = space.create_package(name=pkg_name, key=pkg_key)
        except Exception as e:
            if "already exists" in str(e).lower():
                alt_pkg_key = f"{pkg_key}-{int(time.time())}"
                log_progress(db, sess.id, stage, "package_key_retry", f"Package key '{pkg_key}' exists in recycle bin. Retrying with key '{alt_pkg_key}'...")
                package = space.create_package(name=pkg_name, key=alt_pkg_key)
                pkg_key = alt_pkg_key
            else:
                raise e
        
    # Manage data model package variable
    try:
        existing_var = None
        for v in package.get_variables():
            if v.key == "data-model":
                existing_var = v
                break
        if existing_var:
            existing_var.value = data_model.id
            existing_var.update()
        else:
            package.create_variable(key="data-model", value=data_model.id, type_="DATA_MODEL", runtime=False)
    except Exception as var_err:
        logger.warning(f"Could not link variable: {var_err}")
        
    # Create / Update Knowledge Model
    try:
        km_obj = json.loads(km_content)
    except Exception:
        km_obj = {}
        
    session_suffix = sess.id[:8]
    km_key = f"{pkg_key}-km-{session_suffix}"
    
    mapped_kpis = []
    for item in km_obj.get("key_performance_indicators", []):
        mapped_kpis.append({
            "id": item.get("id"),
            "displayName": item.get("name") or item.get("displayName"),
            "description": item.get("description"),
            "pql": item.get("formula")
        })
        
    mapped_filters = []
    for item in km_obj.get("process_filters", []):
        mapped_filters.append({
            "id": item.get("id"),
            "displayName": item.get("name") or item.get("displayName"),
            "description": item.get("description"),
            "pql": item.get("filter_expression")
        })
        
    event_log_id = "TEMP_P2P_EVENT_LOG"
    for t in data_model.get_tables():
        if "EVENT" in t.name.upper() or "LOG" in t.name.upper():
            event_log_id = t.name
            break
            
    km_yaml_content = {
        "kind": "BASE",
        "metadata": {
            "key": km_key,
            "displayName": km_obj.get("displayName", f"{sess.name} Semantic Layer"),
        },
        "dataModelId": "${{data-model}}",
        "kpis": mapped_kpis,
        "filters": mapped_filters,
        "records": [{"id": event_log_id, "displayName": f"{event_log_id} Table", "pql": f'"{event_log_id}"'}],
        "eventLogsMetadata": {"eventLogs": [{"id": event_log_id, "displayName": event_log_id, "pql": f'"{event_log_id}"."ACTIVITY"', "recordId": event_log_id}]}
    }
    
    existing_km = None
    for existing in package.get_knowledge_models():
        if existing.key == km_key:
            existing_km = existing
            break
            
    if existing_km:
        existing_km.serialized_content = yaml.dump(km_yaml_content, sort_keys=False)
        existing_km.update()
    else:
        package.create_knowledge_model(content=km_yaml_content)
        
    log_progress(db, sess.id, stage, "km_deployed", "Knowledge model semantic definitions deployed successfully.")

    # Save success to lessons learned
    try:
        from app.agents.knowledge_model_agent import KnowledgeModelAgent
        km_agent = KnowledgeModelAgent()
        km_agent.save_lesson(
            stage="knowledge_model",
            requirement=sess.description or "",
            error="None (Successful Run)",
            fix_output=km_content,
            rationale="Knowledge model successfully generated and deployed."
        )
    except Exception as save_err:
        logger.error(f"Failed to save successful KM lesson: {save_err}")

    return km_content



def deploy_analysis(sess: SessionModel, analysis_content: str, db) -> str:
    """
    Deploys a Celonis Studio ANALYSIS (not a View / BOARD_V2).

    Uses the analysis configuration built by analysis_agent.py (which calls
    build_3_sheet_analysis() from celonis_knowledge_base.py) and pushes it
    directly to the Celonis Analysis API via package.create_analysis().

    The 3-sheet structure built by the KB:
      Sheet 1: Case Explorer     (contentType='case-explorer')
      Sheet 2: Process Explorer  (contentType='process-explorer', processExplorerComponent at sheet level)
      Sheet 3: KPI & Analytics   (no contentType — custom sheet with filters + KPI tiles + tables)

    Why Analysis (not View/BOARD_V2)?
      - The user requested an Analysis, which is the classic Celonis Studio interface
      - Analyses support Process Explorer, Case Explorer, and process-level KPIs natively
      - BOARD_V2 is for data dashboards; Analyses are for process mining
    """
    stage = "analysis"
    celonis = get_celonis_connection(db, sess.id, stage)

    # ── Identify Space and Package ───────────────────────────────────────────
    space_name = f"{sess.name} Space"
    space = next((s for s in celonis.studio.get_spaces() if s.name == space_name), None)
    if not space:
        raise Exception(f"Space '{space_name}' not found.")

    pkg_name = f"{sess.name} Package"
    pkg_key = f"{slugify(sess.name).replace('_', '-')}-{sess.id[:8]}"
    package = next((p for p in space.get_packages() if p.name == pkg_name or p.key == pkg_key), None)
    if not package:
        raise Exception(f"Package '{pkg_name}' not found.")

    pkg_key = package.key
    km_key = f"{pkg_key}-km-{sess.id[:8]}"

    # ── Parse analysis config from agent output ──────────────────────────────
    try:
        analysis_config = json.loads(analysis_content)
    except Exception:
        analysis_config = {}

    analysis_title  = analysis_config.get("analysis_title", f"{sess.name} Analysis")
    sheets          = analysis_config.get("sheets", [])
    event_log_table = analysis_config.get("event_log_table", "TEMP_P2P_EVENT_LOG")
    case_table      = analysis_config.get("case_table", "TEMP_P2P_CASES")
    kpi_items       = analysis_config.get("kpi_items", [])
    filter_items    = analysis_config.get("filter_items", [])

    # ── Resolve real table/column names from the Celonis Data Model ────────────
    # Replace TEMP_X defaults with actual DM table names so the layout JSON
    # never contains placeholder names regardless of what the agent returned.
    real_case_col = "CASE_ID"  # default; overridden below if SQL says otherwise
    try:
        pools = celonis.data_integration.get_data_pools()
        dm_pool = next((p for p in pools if p.name == sess.name), None)
        if dm_pool:
            dm_name = f"{sess.name} Data Model"
            dm_obj = next(
                (dm for dm in dm_pool.get_data_models() if dm.name == dm_name), None
            )
            if dm_obj:
                dm_table_names = [t.name for t in dm_obj.get_tables()]
                # Find event-log table: contains EVENT_LOG in name
                real_elt = next(
                    (t for t in dm_table_names if "EVENT_LOG" in t.upper()), None
                )
                # Find cases table: contains CASE in name but not EVENT
                real_ct = next(
                    (t for t in dm_table_names if "CASE" in t.upper() and "EVENT" not in t.upper()), None
                )
                if real_elt:
                    event_log_table = real_elt
                    log_progress(db, sess.id, stage, "resolve_elt",
                                 f"Resolved event log table: {real_elt}")
                if real_ct:
                    case_table = real_ct
                    log_progress(db, sess.id, stage, "resolve_ct",
                                 f"Resolved cases table: {real_ct}")
    except Exception as resolve_err:
        logger.warning(f"Could not resolve real table names from DM: {resolve_err}")

    # Resolve actual case column name from SQL artifact
    try:
        from app.database import ArtifactModel
        import re as _re
        sql_art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == sess.id,
            ArtifactModel.stage == "sql"
        ).order_by(ArtifactModel.version.desc()).first()
        if sql_art and sql_art.content:
            m = _re.search(r'AS\s+(CASE_ID|CASE_KEY|CASEID|CASE_NO)', sql_art.content.upper())
            if m:
                real_case_col = m.group(1)
    except Exception as col_err:
        logger.warning(f"Could not resolve case column from SQL: {col_err}")

    # ── If agent didn't call the KB builder, do it now as fallback ───────────
    if not sheets:
        log_progress(db, sess.id, stage, "kb_fallback",
                     "No sheets in analysis config — building 3-sheet layout from KB...")
        from app.celonis_knowledge_base import (
            build_3_sheet_analysis, KPI_CATALOG, PROCESS_FILTER_TEMPLATES
        )
        process_type = analysis_config.get("process_type", "P2P").upper()
        # Use this process's catalog; fall back to GENERIC if process not in catalog
        specific = KPI_CATALOG.get(process_type, [])
        generic  = KPI_CATALOG.get("GENERIC", [])
        catalog  = specific if specific else generic
        # If still empty, build minimal generic KPIs from resolved table names
        if not catalog:
            catalog = [
                {
                    "id": "CASE_COUNT",
                    "name": "Total Cases",
                    "formula": "COUNT({case_table}.{case_col})",
                    "component_type": "single-kpi"
                },
                {
                    "id": "ACTIVITY_COUNT",
                    "name": "Total Activities",
                    "formula": "COUNT({event_log_table}.ACTIVITY)",
                    "component_type": "single-kpi"
                },
                {
                    "id": "THROUGHPUT",
                    "name": "Avg Throughput Time (Days)",
                    "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE[ACTIVITY] TO LAST_OCCURRENCE[ACTIVITY], EVENTTIME('_cel_event_log')))",
                    "component_type": "single-kpi"
                }
            ]
        if not kpi_items:
            # Replace template placeholders in formula strings
            for k in catalog[:6]:
                formula = k.get("formula", "")
                try:
                    formula = formula.format(
                        event_log_table=event_log_table,
                        case_table=case_table,
                        case_col=real_case_col
                    )
                except Exception:
                    formula = formula.replace(f"TEMP_{event_log_table}", event_log_table)
                    formula = formula.replace(f"TEMP_{case_table}", case_table)
                    formula = formula.replace("CASE_KEY", real_case_col)
                kpi_items.append({"id": k["id"], "displayName": k["name"], "pql": formula})
        if not filter_items:
            ftemplates = PROCESS_FILTER_TEMPLATES.get(process_type, {}) or PROCESS_FILTER_TEMPLATES.get("GENERIC", {})
            filter_items = []
            for fid, fpql in list(ftemplates.items())[:3]:
                try:
                    fpql = fpql.format(
                        event_log_table=event_log_table,
                        case_table=case_table,
                        case_col=real_case_col
                    )
                except Exception:
                    pass
                filter_items.append({"id": fid, "displayName": fid.replace("_", " ").title(), "pql": fpql})
        sheets = build_3_sheet_analysis(
            kpi_items=kpi_items,
            filter_items=filter_items,
            event_log_table=event_log_table,
            case_table=case_table,
            case_col=real_case_col,
            process_name=analysis_title.replace(" Analysis", "")
        )

    analysis_key = f"{pkg_key}-analysis-{sess.id[:8]}"

    # ── Create or Get the Analysis ──────────────────────────────────────────
    log_progress(db, sess.id, stage, "create_analysis",
                 f"Creating or fetching Celonis Analysis: {analysis_title} (key={analysis_key})...")
    analysis = None
    
    # Try fetching existing
    try:
        for existing in package.get_analyses():
            if getattr(existing, "key", None) == analysis_key or existing.name == analysis_title:
                analysis = existing
                log_progress(db, sess.id, stage, "analysis_found", f"Found existing analysis (id={analysis.id}). Updating layout.")
                break
    except Exception as fetch_err:
        log_progress(db, sess.id, stage, "analysis_fetch_warn", f"Warning during fetching analyses: {fetch_err}")

    if not analysis:
        try:
            analysis = package.create_analysis(
                name=analysis_title,
                key=analysis_key,
                knowledge_model_key=km_key
            )
            log_progress(db, sess.id, stage, "analysis_created", f"Analysis object created (id={analysis.id}).")
        except Exception as create_err:
            if "already exists" in str(create_err).lower():
                alt_key = f"{analysis_key}-{int(time.time())}"
                log_progress(db, sess.id, stage, "analysis_key_retry", f"Key '{analysis_key}' exists in recycle bin. Retrying with key '{alt_key}'...")
                try:
                    analysis = package.create_analysis(
                        name=analysis_title,
                        key=alt_key,
                        knowledge_model_key=km_key
                    )
                    log_progress(db, sess.id, stage, "analysis_created_alt", f"Analysis object created with alt key (id={analysis.id}).")
                except Exception as alt_err:
                    raise Exception(f"Failed to create Analysis with alternate key: {alt_err}")
            else:
                raise Exception(f"Failed to create Analysis: {create_err}")

    # ── Push the sheet layout into the Analysis document ─────────────────────
    log_progress(db, sess.id, stage, "push_sheets",
                 f"Pushing {len(sheets)} sheets to Analysis...")
    try:
        # Build the full Analysis document structure.
        # Verified against a real working Celonis analysis serialized_content.
        # Celonis analysis uses serialized_content.draft.document for the layout
        # Get the current serialized content and update it
        current_content = analysis.serialized_content or {}
        if isinstance(current_content, str):
            import yaml as _yaml
            try:
                current_content = _yaml.safe_load(current_content) or {}
            except Exception:
                current_content = {}

        # Ensure draft and document exist as dicts
        if "draft" not in current_content or not isinstance(current_content["draft"], dict):
            current_content["draft"] = {}
        if "document" not in current_content["draft"] or not isinstance(current_content["draft"]["document"], dict):
            current_content["draft"]["document"] = {}

        doc_id = current_content["draft"].get("id") or getattr(analysis, "id", None) or str(uuid.uuid4())
        current_content["draft"]["id"] = doc_id

        doc_dict = current_content["draft"]["document"]
        doc_dict["id"] = doc_dict.get("id") or doc_id
        doc_dict["name"] = doc_dict.get("name") or analysis_title
        doc_dict["theme"] = doc_dict.get("theme") or "celonis_current"

        # CRITICAL: Celonis stores sheets under document.components (NOT document.sheets).
        # Verified by comparing serialized_content of manually-created vs agent-created analyses.
        # The 'sheets' key is ignored by the Celonis UI — only 'components' is rendered.
        doc_dict.pop("sheets", None)  # Remove any stale 'sheets' key
        doc_dict["components"] = sheets
        # editMode must be True (seen in manually-created analyses) for the UI to render correctly
        doc_dict["editMode"] = True

        # Add top-level keys that match manually-created Celonis analyses
        # (missing these causes blank render in some Celonis UI versions)
        if "eventLog" not in current_content:
            current_content["eventLog"] = ""
        if "customDimension" not in current_content:
            current_content["customDimension"] = ""

        # Set the published field to draft's representation
        current_content["published"] = json.loads(json.dumps(current_content["draft"]))

        # Check if Celonis also requires analysis.document key
        if "analysis" not in current_content or not isinstance(current_content["analysis"], dict):
            current_content["analysis"] = {}
        if "document" not in current_content["analysis"] or not isinstance(current_content["analysis"]["document"], dict):
            current_content["analysis"]["document"] = {}
        
        current_content["analysis"]["id"] = doc_id
        current_content["analysis"]["document"]["id"] = doc_id
        current_content["analysis"]["document"]["name"] = analysis_title
        current_content["analysis"]["document"]["theme"] = "celonis_current"
        # Also use 'components' (not 'sheets') in the analysis.document key
        current_content["analysis"]["document"].pop("sheets", None)
        current_content["analysis"]["document"]["components"] = sheets

        # Push back
        serialized_str = json.dumps(current_content)

        # ── Dynamic normalization: replace TEMP_X with X for all real DM tables ──
        # Build replacement map from actual tables in the Celonis Data Model.
        # This handles P2P, O2C, R2R or any future process without hardcoded names.
        try:
            pool_name = sess.name
            pools = celonis.data_integration.get_data_pools()
            data_pool = next((p for p in pools if p.name == pool_name), None)
            if data_pool:
                dm_name = f"{sess.name} Data Model"
                data_model = next(
                    (dm for dm in data_pool.get_data_models() if dm.name == dm_name),
                    None
                )
                if data_model:
                    dm_table_names = [t.name.upper() for t in data_model.get_tables()]
                    # For every real table X, if TEMP_X appears in the JSON → replace with X
                    for real_table in dm_table_names:
                        temp_name = f"TEMP_{real_table}"
                        if temp_name in serialized_str:
                            serialized_str = serialized_str.replace(temp_name, real_table)
                            log_progress(db, sess.id, stage, "normalize_table",
                                         f"Replaced {temp_name} → {real_table} in analysis layout.")
        except Exception as norm_err:
            logger.warning(f"Could not auto-normalize table names: {norm_err}")

        # ── Dynamic column alias normalization from SQL artifact ─────────────────
        # Read the SQL artifact for this session to detect aliased columns
        # e.g. "... AS CASE_ID" tells us the real column name is CASE_ID, not CASE_KEY
        try:
            from app.database import ArtifactModel
            sql_art = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == sess.id,
                ArtifactModel.stage == "sql"
            ).order_by(ArtifactModel.version.desc()).first()

            if sql_art and sql_art.content:
                import re
                sql_upper = sql_art.content.upper()

                # Detect actual case column: look for "... AS CASE_ID" or "... AS CASE_KEY"
                # and use whichever is actually in the SQL
                case_col_match = re.search(
                    r'AS\s+(CASE_ID|CASE_KEY|CASEID|CASE_NO)',
                    sql_upper
                )
                if case_col_match:
                    actual_case_col = case_col_match.group(1)
                    # Replace any wrong alias with the real one found in SQL
                    for wrong_alias in ["CASE_KEY", "CASE_ID", "CASEID", "CASE_NO"]:
                        if wrong_alias != actual_case_col and wrong_alias in serialized_str:
                            serialized_str = serialized_str.replace(wrong_alias, actual_case_col)
                            log_progress(db, sess.id, stage, "normalize_col",
                                         f"Replaced column alias {wrong_alias} → {actual_case_col}")
        except Exception as col_norm_err:
            logger.warning(f"Could not auto-normalize column aliases: {col_norm_err}")

        analysis.serialized_content = serialized_str
        analysis.update()

        # ── Publish the analysis so it appears in View mode (not just Edit mode) ──
        try:
            analysis.publish()
            log_progress(db, sess.id, stage, "analysis_published",
                         "Analysis published successfully — sheets visible in View mode.")
        except Exception as pub_err:
            logger.warning(f"Could not publish analysis (non-fatal): {pub_err}")

        log_progress(db, sess.id, stage, "sheets_pushed",
                     f"Successfully pushed {len(sheets)} sheets to Analysis.")

    except Exception as layout_err:
        log_progress(db, sess.id, stage, "layout_warn",
                     f"Warning: Could not update Analysis layout: {layout_err}. "
                     "Analysis was created — add sheets manually in Celonis Studio.")

    # ── Publish Package ──────────────────────────────────────────────────────
    try:
        next_version = "1.0.0"
        try:
            history = package.get_history()
            if history:
                versions = []
                for h in history:
                    v_str = getattr(h, "version", None)
                    if not v_str:
                        continue
                    parts = v_str.split('.')
                    if len(parts) == 3:
                        try:
                            versions.append(tuple(map(int, parts)))
                        except ValueError:
                            pass
                if versions:
                    max_v = max(versions)
                    next_version = f"{max_v[0]}.{max_v[1]}.{max_v[2] + 1}"
        except Exception as hist_err:
            logger.warning(f"Failed to fetch package history: {hist_err}")

        package.publish(version=next_version)
        log_progress(db, sess.id, stage, "package_published",
                     f"Package published to v{next_version}.")
    except Exception as pub_err:
        logger.warning(f"Failed to publish package: {pub_err}")

    # ── Save success lesson ──────────────────────────────────────────────────
    try:
        from app.agents.analysis_agent import AnalysisAgent
        analysis_agent = AnalysisAgent()
        analysis_agent.save_lesson(
            stage="analysis",
            requirement=sess.description or "",
            error="None (Successful Run)",
            fix_output=analysis_content,
            rationale=(
                "Celonis Analysis (3-sheet: Case Explorer, Process Explorer, "
                "KPI & Analytics) successfully deployed using "
                "build_3_sheet_analysis() from celonis_knowledge_base.py."
            )
        )
    except Exception as save_err:
        logger.error(f"Failed to save successful analysis lesson: {save_err}")

    return analysis_content
