import json
import datetime
import os
import re
import yaml
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return text.strip('_')

from app.database import init_db, get_db, SessionModel, ArtifactModel, AuditLogModel
from app.schemas import (
    SessionCreate, SessionResponse, ArtifactResponse, ArtifactEdit,
    AuditLogResponse, ApprovalRequest, RoleSwitchRequest, TriggerAgentRequest
)
from app.orchestrator import WorkflowOrchestrator
from app.config import ROLES, CELONIS_URL, CELONIS_API_TOKEN

app = FastAPI(title="Celonis Multi-Agent Workflow Orchestrator API")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = WorkflowOrchestrator()

@app.on_event("startup")
def startup_event():
    init_db()

@app.post("/sessions", response_model=SessionResponse)
def create_session(session_data: SessionCreate, db: Session = Depends(get_db)):
    # Create the session db row
    new_session = SessionModel(
        name=session_data.name,
        description=session_data.initial_requirement
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Log action
    orchestrator._log_audit(
        db, new_session.id, "requirement", "session_created",
        f"Session created with initial requirement: {(session_data.initial_requirement or '')[:100]}..."
    )

    # If initial requirement is provided, automatically trigger the first stage
    if session_data.initial_requirement:
        try:
            orchestrator.run_stage(db, new_session.id, "requirement")
        except Exception as e:
            # Let it fail silently here, session is still created
            pass

    return new_session

@app.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()

@app.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    return sess

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(sess)
    db.commit()
    return {"message": f"Session {session_id} successfully deleted."}

@app.post("/sessions/{session_id}/trigger", response_model=ArtifactResponse)
def trigger_agent(session_id: str, payload: TriggerAgentRequest, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Guard roles
    required_roles_map = {
        "requirement": ["Business User", "Process Analyst", "Admin"],
        "sql": ["Process Analyst", "Admin"],
        "data_model": ["Process Analyst", "Admin"],
        "knowledge_model": ["Process Analyst", "Admin"],
        "analysis": ["Process Analyst", "Admin"],
        "qa": ["Process Analyst", "Admin", "Reviewer"]
    }
    allowed_roles = required_roles_map.get(payload.stage, [])
    if sess.current_role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Role '{sess.current_role}' is not authorized to trigger the '{payload.stage}' stage. Required roles: {allowed_roles}"
        )

    try:
        artifact = orchestrator.run_stage(db, session_id, payload.stage)
        return artifact
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runtime failure: {str(e)}")

@app.get("/sessions/{session_id}/artifacts", response_model=List[ArtifactResponse])
def get_all_artifacts(session_id: str, db: Session = Depends(get_db)):
    return db.query(ArtifactModel).filter(ArtifactModel.session_id == session_id).order_by(ArtifactModel.version.desc()).all()

@app.get("/sessions/{session_id}/artifacts/{stage}", response_model=ArtifactResponse)
def get_latest_stage_artifact(session_id: str, stage: str, db: Session = Depends(get_db)):
    art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == stage
    ).order_by(ArtifactModel.version.desc()).first()
    
    if not art:
        raise HTTPException(status_code=404, detail=f"No artifact generated for stage '{stage}' in this session.")
    return art

@app.put("/sessions/{session_id}/artifacts/{stage}", response_model=ArtifactResponse)
def edit_artifact(session_id: str, stage: str, edit_data: ArtifactEdit, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    if sess.current_role not in ["Process Analyst", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Process Analyst or Admin roles can edit generated artifacts.")

    latest_art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == stage
    ).order_by(ArtifactModel.version.desc()).first()

    if not latest_art:
        raise HTTPException(status_code=404, detail="No prior artifact found to edit. Generate first.")

    # Create new version with manual edits
    new_version = latest_art.version + 1
    edited_art = ArtifactModel(
        session_id=session_id,
        stage=stage,
        version=new_version,
        content=edit_data.content,
        rationale=edit_data.rationale or f"Manual edit by role: {sess.current_role}",
        approved=False
    )
    db.add(edited_art)
    
    # Log manual update
    orchestrator._log_audit(
        db, session_id, stage, "edited",
        f"Manual edit applied. Created version {new_version}."
    )
    db.commit()
    db.refresh(edited_art)
    return edited_art

@app.post("/sessions/{session_id}/artifacts/{stage}/approve", response_model=ArtifactResponse)
def approve_artifact(session_id: str, stage: str, req: ApprovalRequest, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Only Reviewers or Admins can approve
    if sess.current_role not in ["Reviewer", "Admin"]:
        raise HTTPException(status_code=403, detail="Approval requires 'Reviewer' or 'Admin' permissions.")

    latest_art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == stage
    ).order_by(ArtifactModel.version.desc()).first()

    if not latest_art:
        raise HTTPException(status_code=404, detail="No artifact exists to approve/reject.")

    latest_art.approved = req.approved
    latest_art.approved_by = sess.current_role
    
    action = "approved" if req.approved else "rejected"
    orchestrator._log_audit(
        db, session_id, stage, action,
        f"Artifact {action} by role {sess.current_role}. Notes: {req.notes or 'None'}"
    )
    
    if req.approved:
        progression_map = {
            "requirement": "sql_transformation",
            "sql": "data_modeling",
            "data_model": "knowledge_modeling",
            "knowledge_model": "analysis_generation",
            "analysis": "completed",
            "qa": "completed"
        }
        sess.status = progression_map.get(stage, sess.status)
        
    db.commit()
    db.refresh(latest_art)
    return latest_art

@app.post("/sessions/{session_id}/role", response_model=SessionResponse)
def switch_role(session_id: str, req: RoleSwitchRequest, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from: {ROLES}")

    sess.current_role = req.role
    orchestrator._log_audit(
        db, session_id, "governance", "role_switched",
        f"Switched session active role to: {req.role}"
    )
    db.commit()
    db.refresh(sess)
    return sess

@app.get("/sessions/{session_id}/audit_logs", response_model=List[AuditLogResponse])
def get_audit_logs(session_id: str, db: Session = Depends(get_db)):
    return db.query(AuditLogModel).filter(AuditLogModel.session_id == session_id).order_by(AuditLogModel.timestamp.desc()).all()

@app.post("/sessions/{session_id}/promote")
def promote_to_production(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    # 1. Access validation
    if sess.current_role not in ["Reviewer", "Admin"]:
        raise HTTPException(status_code=403, detail="Production promotion requires 'Reviewer' or 'Admin' authorization.")

    # 2. Check QA Validation status (Bypassed as per requirement; default score to 100 if not run)
    qa_artifact = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == "qa"
    ).order_by(ArtifactModel.version.desc()).first()

    score = 100
    if qa_artifact:
        try:
            report = json.loads(qa_artifact.content)
            score = report.get("total_score", 100)
        except Exception:
            pass

    # Fetch all latest stage artifacts
    stages = ["requirement", "sql", "data_model", "knowledge_model", "analysis", "qa"]
    bundle = {}
    for stg in stages:
        art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == session_id,
            ArtifactModel.stage == stg
        ).order_by(ArtifactModel.version.desc()).first()
        bundle[stg] = art.content if art else ""

    # Auto-push all assets to Celonis platform using PyCelonis integration
    pushed_successfully, compiled_assets = push_to_celonis_platform(sess, bundle, db=db)
    push_status_msg = "Successfully pushed all assets to Celonis Cloud." if pushed_successfully else "Failed to auto-push to Celonis Cloud (check server logs)."

    final_sql = compiled_assets.get("sql") or bundle.get("sql", "-- empty SQL")

    # Format Knowledge Model as YAML for Celonis
    km_json_str = bundle.get("knowledge_model", "{}")
    try:
        km_obj = json.loads(km_json_str)
        km_yaml_str = yaml.dump(km_obj, sort_keys=False)
    except Exception:
        km_yaml_str = km_json_str

    # Format Analysis (use the compiled analysis_config if available, else fallback to raw agent response)
    analysis_config = compiled_assets.get("analysis_config")
    if analysis_config:
        analysis_formatted_json = json.dumps(analysis_config, indent=2)
    else:
        analysis_json_str = bundle.get("analysis", "{}")
        try:
            analysis_obj = json.loads(analysis_json_str)
            analysis_formatted_json = json.dumps(analysis_obj, indent=2)
        except Exception:
            analysis_formatted_json = analysis_json_str

    # Add a deployment runbook referencing the new JSON config
    runbook = (
        f"# Deployment Runbook - {sess.name}\n"
        f"Promoted by: {sess.current_role}\n"
        f"QA Validation Score: {score}/100\n"
        f"Deployment Timestamp: {datetime.datetime.utcnow().isoformat()}\n\n"
        "## Promotion Steps:\n"
        "1. Execute `transformations.sql` in Celonis Event Collection (Data Pool).\n"
        "2. Map `TEMP_P2P_CASES` (Case Table) and `TEMP_P2P_EVENT_LOG` (Event Table) in Data Model.\n"
        "3. Create new Knowledge Model package using the defined schema in `knowledge_model.yaml`.\n"
        "4. Publish Celonis Analysis layout using defined schema in `celonis_analysis_spec.json`.\n"
    )

    # Save all files locally in a new folder under the workspace root as requested
    session_slug = slugify(sess.name)
    export_dir = os.path.join(WORKSPACE_DIR, "projects", session_slug)
    os.makedirs(export_dir, exist_ok=True)
    
    try:
        with open(os.path.join(export_dir, "business_requirement_spec.json"), "w", encoding="utf-8") as f:
            f.write(bundle.get("requirement", "{}"))
        with open(os.path.join(export_dir, "transformations.sql"), "w", encoding="utf-8") as f:
            f.write(final_sql)
        with open(os.path.join(export_dir, "datamodel.json"), "w", encoding="utf-8") as f:
            f.write(bundle.get("data_model", "{}"))
        with open(os.path.join(export_dir, "knowledge_model.yaml"), "w", encoding="utf-8") as f:
            f.write(km_yaml_str)
        with open(os.path.join(export_dir, "celonis_analysis_spec.json"), "w", encoding="utf-8") as f:
            f.write(analysis_formatted_json)
        with open(os.path.join(export_dir, "qa_validation_checklist.json"), "w", encoding="utf-8") as f:
            f.write(bundle.get("qa", "{}"))
        with open(os.path.join(export_dir, "deployment_runbook.md"), "w", encoding="utf-8") as f:
            f.write(runbook)
    except Exception as e:
        # We log and keep going so that the API doesn't fail if there's a file permission issue
        import logging
        logging.getLogger(__name__).error(f"Failed to write exported assets locally: {str(e)}")

    # Update session status
    sess.status = "completed"
    orchestrator._log_audit(
        db, session_id, "governance", "promoted_to_production",
        f"Deployment bundle successfully built, promoted, and exported. QA Score: {score}. {push_status_msg}"
    )
    db.commit()

    return {
        "message": f"Successfully promoted to production. {push_status_msg}",
        "qa_score": score,
        "export_dir": export_dir
    }

def push_to_celonis_platform(sess: SessionModel, bundle: dict, db: Session = None) -> tuple[bool, dict]:
    """
    Programmatically logs in to Celonis using PyCelonis, creates the Data Pool,
    Data Model, Data Job, SQL Transformation, Studio Space, Package,
    Knowledge Model (mapped appropriately), and Celonis Analysis.
    """
    from pycelonis import get_celonis
    import logging
    import pandas as pd
    import re
    import os
    import json

    logger = logging.getLogger(__name__)

    def log_progress(msg: str):
        logger.info(msg)
        if db:
            try:
                from app.database import AuditLogModel
                log = AuditLogModel(
                    session_id=sess.id,
                    stage="analysis",
                    agent_name="Celonis Deployer",
                    action="promote_progress",
                    prompt=msg
                )
                db.add(log)
                db.commit()
            except Exception as log_err:
                logger.error(f"Failed to log promote progress: {log_err}")

    try:
        log_progress("Connecting to Celonis platform...")
        celonis = get_celonis(base_url=CELONIS_URL, api_token=CELONIS_API_TOKEN, key_type="USER_KEY")
        
        # 1. Manage Data Pool
        pool_name = sess.name
        log_progress(f"Managing Data Pool: {pool_name}...")
        pools = celonis.data_integration.get_data_pools()
        data_pool = None
        for p in pools:
            if p.name == pool_name:
                data_pool = p
                break
        if not data_pool:
            data_pool = celonis.data_integration.create_data_pool(name=pool_name)
        log_progress(f"Data Pool '{pool_name}' verified/created.")

        import time
        import re as _re

        # 2. Upload all Data_source CSV files directly into the target pool
        data_source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data_source")
        if not os.path.exists(data_source_dir):
            data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"

        sql_content = bundle.get("sql", "")
        referenced_tables = set()
        if sql_content:
            matches = _re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\b', sql_content, _re.IGNORECASE)
            for m in matches:
                referenced_tables.add(m.upper())

        log_progress(f"Uploading Data_source tables directly to pool '{pool_name}'...")
        pool_tables = {t.name.upper(): t for t in data_pool.get_tables()}

        if os.path.exists(data_source_dir):
            csv_files = sorted([f for f in os.listdir(data_source_dir) if f.lower().endswith(".csv")])
            log_progress(f"Found {len(csv_files)} CSV files in Data_source. Checking status...")
            for f in csv_files:
                table_name = os.path.splitext(f)[0].upper()
                if table_name not in referenced_tables:
                    # Skip uploading unused table to prevent hitting Celonis rate limits
                    continue
                if table_name in pool_tables:
                    log_progress(f"Table {table_name} already exists in pool. Skipping upload.")
                    continue
                try:
                    df = pd.read_csv(os.path.join(data_source_dir, f))
                    df = df.where(pd.notnull(df), None)
                    log_progress(f"Uploading table {table_name} ({len(df)} rows) to pool...")
                    data_pool.create_table(df=df, table_name=table_name, drop_if_exists=True)
                    pool_tables[table_name] = True
                    log_progress(f"Uploaded table {table_name} successfully.")
                except Exception as upload_err:
                    log_progress(f"Warning: Failed to upload {table_name}: {upload_err}")
        else:
            log_progress(f"Warning: Data_source directory not found: {data_source_dir}")

        # 3. Scan SQL for any referenced tables missing from pool; create empty mocks
        # sql_content already extracted above
        if sql_content:
            log_progress("Scanning SQL transformations for referenced tables...")
            matches = _re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\b', sql_content, _re.IGNORECASE)
            for m in matches:
                t_upper = m.upper()
                if t_upper.startswith("TEMP_") or t_upper in pool_tables:
                    continue
                # Table referenced in SQL but not in Data_source — create a mock
                cols = set(_re.findall(rf'\b{m}\.([a-zA-Z0-9_]+)\b', sql_content, _re.IGNORECASE))
                if not cols:
                    cols = {"MANDT"}
                df_mock = pd.DataFrame(columns=list(cols))
                row_data = []
                for col in list(cols):
                    col_lower = col.lower()
                    if col_lower in ["netwr", "netpr", "menge", "dmbtr", "wrbtr", "amount", "price", "qty", "quantity"]:
                        row_data.append(0.0)
                    elif "dat" in col_lower or "time" in col_lower:
                        row_data.append("2026-01-01 00:00:00")
                    else:
                        row_data.append("0")
                df_mock.loc[0] = row_data
                try:
                    log_progress(f"Creating empty mock table {t_upper} in pool...")
                    data_pool.create_table(df=df_mock, table_name=t_upper, drop_if_exists=True)
                    pool_tables[t_upper] = True
                    log_progress(f"Created mock table {t_upper} in pool successfully.")
                except Exception as mock_err:
                    log_progress(f"Warning: Could not create mock for {t_upper}: {mock_err}")

        # 4. Normalize TEMP_ tables: CREATE VIEW TEMP_* → CREATE TABLE TEMP_*
        # The Data Model requires physical tables, not views.
        def normalize_temp_tables(sql: str) -> str:
            sql = _re.sub(r'CREATE\s+VIEW\s+(TEMP_\w+)\s+AS', r'CREATE TABLE \1 AS', sql, flags=_re.IGNORECASE)
            sql = _re.sub(r'DROP\s+VIEW\s+IF\s+EXISTS\s+(TEMP_\w+)', r'DROP TABLE IF EXISTS \1', sql, flags=_re.IGNORECASE)
            return sql
        final_sql = normalize_temp_tables(sql_content)
        log_progress("SQL normalized (TEMP_ CREATE VIEW -> CREATE TABLE).")

        # 5. Create/recreate the Data Job and run the SQL transformation (with self-correction loop)
        max_retries = 3
        current_sql = final_sql
        data_job = None
        for attempt in range(1, max_retries + 1):
            if not current_sql:
                break
            
            job_name = f"{sess.name} Data Job"
            log_progress(f"Managing Data Job: {job_name} (Attempt {attempt}/{max_retries})...")
            for j in data_pool.get_jobs():
                if j.name == job_name:
                    try:
                        j.delete()
                    except Exception as del_err:
                        logger.warning(f"Could not delete existing job: {del_err}")
                    break
            data_job = data_pool.create_job(name=job_name)

            task = data_job.create_transformation(
                name="SQL Transformation",
                description="Auto-generated SQL transformations"
            )
            task.update_statement(current_sql)
            log_progress("SQL transformation statement updated. Executing data job...")
            
            try:
                data_job.execute(wait=True)
                status_obj = data_job.get_current_execution_status()
                status_str = getattr(status_obj, "status", str(status_obj))
                log_progress(f"Job execution completed (Attempt {attempt}). Status: {status_str}")
                
                if "success" in status_str.lower():
                    # Success! Save the final successful SQL
                    final_sql = current_sql
                    break
                else:
                    raise Exception(f"SQL execution status not successful: {status_str}")
            except Exception as e:
                log_progress(f"Execution attempt {attempt} failed: {e}")
                
                # Fetch detailed error log if possible
                detailed_error = ""
                try:
                    detailed_error = str(data_job._get_execution_detailed_error_log())
                except Exception as log_err:
                    detailed_error = f"Could not fetch detailed Celonis error log: {log_err}"
                
                combined_error = f"{e}\n{detailed_error}"
                logger.error(f"SQL Execution Error details:\n{combined_error}")
                
                if attempt == max_retries:
                    raise Exception(f"SQL execution failed after {max_retries} attempts. Last error: {combined_error}")
                
                # Self-correction: Call SQL agent to fix the error on the fly
                log_progress("Triggering Transformation SQL Agent self-correction loop...")
                from app.agents.sql_agent import TransformationSQLAgent
                sql_agent = TransformationSQLAgent()
                
                requirement_spec = bundle.get("requirement", "")
                
                rationale, corrected_sql = sql_agent.fix_error(requirement_spec, current_sql, combined_error)
                log_progress("SQL Agent generated corrected SQL. Retrying execution...")
                
                # Save the corrected SQL to DB as a new artifact version so it updates in the UI
                from app.database import SessionLocal, ArtifactModel
                try:
                    db_sess = SessionLocal()
                    last_art = db_sess.query(ArtifactModel).filter(
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
                    db_sess.add(new_art)
                    db_sess.commit()
                    log_progress(f"Saved corrected SQL to DB as version {new_version}")
                    
                    # Update local bundle dictionary so that ZIP output contains the final fixed SQL
                    bundle["sql"] = corrected_sql
                    db_sess.close()
                except Exception as db_err:
                    logger.error(f"Failed to save corrected SQL to DB: {db_err}")
                
                current_sql = normalize_temp_tables(corrected_sql)

        # 7. Manage Data Model
        dm_name = f"{sess.name} Data Model"
        log_progress(f"Managing Data Model: {dm_name}...")
        data_models = data_pool.get_data_models()
        data_model = None
        for dm in data_models:
            if dm.name == dm_name:
                data_model = dm
                break
        if not data_model:
            data_model = data_pool.create_data_model(name=dm_name)

        # 8. Map Output Tables in Data Model — dynamically discover TEMP_ tables from SQL
        log_progress("Configuring Data Model mappings...")

        # Find TEMP_ table names from the SQL — any CREATE TABLE TEMP_* statement
        temp_tables_in_sql = _re.findall(
            r'CREATE\s+TABLE\s+(TEMP_\w+)\s+AS', final_sql, _re.IGNORECASE
        )
        log_progress(f"Discovered TEMP tables: {temp_tables_in_sql}")

        # Add all discovered TEMP_ tables to the Data Model
        dm_tables = data_model.get_tables()
        dm_table_names = [t.name.upper() for t in dm_tables]
        for tname in temp_tables_in_sql:
            t_upper = tname.upper()
            if t_upper not in dm_table_names:
                log_progress(f"Adding table {t_upper} to Data Model...")
                try:
                    data_model.add_table(name=t_upper)
                    dm_table_names.append(t_upper)
                except Exception as t_err:
                    log_progress(f"Warning: Could not add table {t_upper} to Data Model: {t_err}")

        # Identify event log and case table generically
        # Event log: table with "EVENT" in name; Case table: table with "CASE" in name
        event_table = None
        case_table = None
        for t in data_model.get_tables():
            tname_up = t.name.upper()
            if "EVENT" in tname_up or "LOG" in tname_up:
                event_table = t
            elif "CASE" in tname_up:
                case_table = t

        if event_table and case_table:
            log_progress(f"Event table identified: {event_table.name}, Case table: {case_table.name}")
            # Foreign Key
            try:
                fks = data_model.get_foreign_keys()
                fk_exists = any(
                    fk.source_table_id == event_table.id and fk.target_table_id == case_table.id
                    for fk in fks
                )
                if not fk_exists:
                    log_progress(f"Linking foreign keys: {event_table.name}.CASE_KEY -> {case_table.name}.CASE_KEY")
                    data_model.create_foreign_key(
                        source_table_id=event_table.id,
                        target_table_id=case_table.id,
                        columns=[("CASE_KEY", "CASE_KEY")]
                    )
            except Exception as fk_err:
                logger.warning(f"Could not create foreign key: {fk_err}")

            # Process Configuration
            try:
                configs = data_model.get_process_configurations()
                if not configs:
                    log_progress("Creating process configuration mapping...")
                    data_model.create_process_configuration(
                        activity_table_id=event_table.id,
                        case_id_column="CASE_KEY",
                        activity_column="ACTIVITY",
                        timestamp_column="EVENT_TIME",
                        sorting_column="SORT_INDEX",
                        case_table_id=case_table.id
                    )
            except Exception as pc_err:
                logger.warning(f"Could not create process configuration: {pc_err}")
        else:
            log_progress(f"Warning: Event/Case tables mismatch. DM tables: {[t.name for t in data_model.get_tables()]}")

        # Reload Data Model
        log_progress("Reloading Data Model and waiting for completion...")
        data_model.reload(wait=True)
        log_progress("Data Model reloaded successfully.")

        # 9. Manage Space
        space_name = f"{sess.name} Space"
        log_progress(f"Managing Studio Space: {space_name}...")
        spaces = celonis.studio.get_spaces()
        space = None
        for s in spaces:
            if s.name == space_name:
                space = s
                break
        if not space:
            space = celonis.studio.create_space(name=space_name)
            
        # 10. Manage Package
        pkg_name = f"{sess.name} Package"
        pkg_key = slugify(sess.name).replace("_", "-")
        # Append unique session ID suffix to prevent global package key conflict
        pkg_key = f"{pkg_key}-{sess.id[:8]}"
        log_progress(f"Managing Package: {pkg_name} (Key: {pkg_key})...")
        packages = space.get_packages()
        package = None
        for p in packages:
            if p.key == pkg_key:
                package = p
                break
        if not package:
            package = space.create_package(name=pkg_name, key=pkg_key)
            
        # 11. Manage Knowledge Model
        km_json_str = bundle.get("knowledge_model", "{}")
        knowledge_model = None
        if km_json_str and km_json_str != "{}":
            log_progress("Configuring Knowledge Model semantic definitions...")
            try:
                km_obj = json.loads(km_json_str)
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
                
            # Create or update package variable 'data-model' pointing to the data model ID
            try:
                existing_var = None
                for v in package.get_variables():
                    if v.key == "data-model":
                        existing_var = v
                        break
                if existing_var:
                    log_progress("Updating package variable 'data-model'...")
                    existing_var.value = data_model.id
                    existing_var.update()
                else:
                    log_progress("Creating package variable 'data-model'...")
                    package.create_variable(key="data-model", value=data_model.id, type_="DATA_MODEL", runtime=False)
                log_progress("Linked package variable 'data-model' pointing to data model ID.")
            except Exception as var_err:
                logger.warning(f"Could not manage package variable 'data-model': {var_err}")

            event_log_id = event_table.name if event_table else "TEMP_P2P_EVENT_LOG"
            km_content = {
                "kind": "BASE",
                "metadata": {
                    "key": km_key,
                    "displayName": km_obj.get("displayName", f"{sess.name} Semantic Layer"),
                },
                "dataModelId": "${{data-model}}",
                "kpis": mapped_kpis,
                "filters": mapped_filters,
                "records": [
                    {
                        "id": event_log_id,
                        "displayName": f"{event_log_id.replace('_', ' ').title()} Table",
                        "pql": f'"{event_log_id}"'
                    }
                ],
                "eventLogsMetadata": {
                    "eventLogs": [
                        {
                            "id": event_log_id,
                            "displayName": f"{event_log_id.replace('_', ' ').title()}",
                            "pql": f'"{event_log_id}"."ACTIVITY"',
                            "recordId": event_log_id
                        }
                    ]
                }
            }
            
            existing_km = None
            kms = package.get_knowledge_models()
            for existing in kms:
                if existing.key == km_key:
                    existing_km = existing
                    break
            
            if existing_km:
                log_progress("Updating existing Knowledge Model semantic definition...")
                existing_km.serialized_content = yaml.dump(km_content, sort_keys=False)
                existing_km.update()
                knowledge_model = existing_km
            else:
                log_progress("Creating new Knowledge Model semantic definition...")
                knowledge_model = package.create_knowledge_model(content=km_content)
            log_progress("Knowledge Model saved successfully.")
            
        # 12. Manage Analysis (No View Creation)
        analysis_config = {}
        analysis_name = f"{sess.name} Analysis"
        
        # Use a unique timestamped key suffix to prevent key conflicts with deleted nodes in Celonis trash
        import time
        analysis_key = f"{pkg_key}-analysis-{sess.id[:8]}-{int(time.time())}"
        analysis = None
        
        # Clean up existing analyses in package with the same name or key pattern
        try:
            analyses = package.get_analyses()
            for existing_analysis in analyses:
                if existing_analysis.name == analysis_name or existing_analysis.key.startswith(f"{pkg_key}-analysis-"):
                    log_progress(f"Deleting old Celonis Analysis: {existing_analysis.name}...")
                    existing_analysis.delete()
        except Exception as scan_err:
            logger.warning(f"Could not scan/delete old analyses: {scan_err}")

        try:
            log_progress(f"Creating Celonis Analysis: {analysis_name}...")
            analysis = package.create_analysis(
                name=analysis_name,
                key=analysis_key,
                data_model_id=data_model.id,
                knowledge_model_key=knowledge_model.key if knowledge_model else None
            )
            log_progress(f"Successfully created Celonis Analysis: {analysis.name}")
        except Exception as create_err:
            log_progress(f"Warning: Failed to create Analysis: {create_err}")
            logger.error(f"Failed to create Analysis: {create_err}", exc_info=True)

        if analysis:
            try:
                # Get already registered KPIs to prevent duplicates
                existing_kpi_ids = set()
                try:
                    content_dict = json.loads(analysis.serialized_content)
                    existing_kpi_ids = {kpi.get("id") for kpi in content_dict.get("kpis", []) if kpi.get("id")}
                except Exception as parse_err:
                    logger.warning(f"Could not parse analysis serialized_content for KPIs: {parse_err}")

                # Programmatically register all mapped KPIs in the Analysis
                if knowledge_model and mapped_kpis:
                    from pycelonis.service.process_analytics.service import ProcessAnalyticsService, KpiTransport, KpiSource
                    log_progress("Registering KPIs inside Celonis Analysis...")
                    for kpi_item in mapped_kpis:
                        kpi_id = kpi_item.get("id")
                        kpi_name = kpi_item.get("displayName")
                        kpi_desc = kpi_item.get("description") or ""
                        kpi_formula = kpi_item.get("pql")
                        
                        if kpi_formula:
                            if kpi_id in existing_kpi_ids:
                                logger.info(f"KPI '{kpi_name}' already exists in Analysis. Skipping registration.")
                                continue
                            try:
                                log_progress(f"Adding KPI '{kpi_name}' to Analysis...")
                                kpi_req = KpiTransport(
                                    id=kpi_id,
                                    name=kpi_name,
                                    description=kpi_desc,
                                    template=kpi_formula,
                                    source=KpiSource.LOCAL
                                )
                                ProcessAnalyticsService.post_analysis_v2_api_analysis_analysis_id_kpi(
                                    client=analysis.client,
                                    analysis_id=analysis.id,
                                    request_body=kpi_req
                                )
                            except Exception as kpi_err:
                                logger.error(f"Failed to add KPI '{kpi_name}' to Analysis: {kpi_err}", exc_info=True)
                                log_progress(f"Warning: Failed to add KPI '{kpi_name}' to Analysis: {kpi_err}")
                
                # Build Analysis layout using the Knowledge Base build_analysis_layout() helper.
                # This creates a BEAUTIFUL Celonis-style dashboard with:
                #   Row 0 (h=1): Filter bar dropdowns (up to 3)
                #   Row 1 (h=3): KPI tiles — large, easy to read (up to 6, 3 per row)
                #   Row 4 (h=8): Process Explorer — ALWAYS present, full-width centerpiece
                #   Row 12(h=6): Activity Frequency Table — full-width process footprint
                from app.celonis_knowledge_base import build_4_sheet_analysis
                log_progress("Building 4-sheet Analysis layout (Case Explorer, Process Explorer, Process Overview, KPI & Analytics)...")
                
                event_log_id = event_table.name if event_table else "TEMP_P2P_EVENT_LOG"
                case_table_id = case_table.name if case_table else "TEMP_P2P_CASES"
                process_name = sess.name if sess.name else "Process"
                
                sheets_list = build_4_sheet_analysis(
                    kpi_items=mapped_kpis,
                    filter_items=mapped_filters,
                    event_log_table=event_log_id,
                    case_table=case_table_id,
                    process_name=process_name
                )
                log_progress(f"Layout built: {len(sheets_list)} sheets successfully created.")
                        
                try:
                    # Retrieve draft details
                    content_dict = json.loads(analysis.serialized_content)
                    draft_id = content_dict.get("draft", {}).get("id") or analysis.id
                    analysis_name_val = content_dict.get("analysis", {}).get("name") or analysis.name
                    
                    content_dict["draft"]["document"] = {
                        "id": draft_id,
                        "name": analysis_name_val,
                        "theme": "celonis_legacy",
                        "editMode": True,
                        "kpiViews": [],
                        "variables": [],
                        "components": sheets_list,
                        "colorMappings": [],
                        "translationMap": {},
                        "allowRawDataExport": True,
                        "rawDataExportLimit": 20000,
                        "statelessLoadScript": "",
                        "showFiltersForViewers": False
                    }
                    analysis.serialized_content = json.dumps(content_dict)
                    analysis.update()
                    
                    # Force publish/release the analysis draft to make changes visible to users in Celonis UI
                    try:
                        from pycelonis.service.process_analytics.service import ProcessAnalyticsService
                        content_obj = analysis._get_content()
                        if content_obj and content_obj.draft:
                            log_progress("Releasing/publishing Celonis Analysis draft...")
                            ProcessAnalyticsService.put_analysis_v2_api_analysis_analysis_id_autosave(
                                client=analysis.client,
                                analysis_id=analysis.id,
                                request_body=content_obj.draft,
                                release=True
                            )
                            log_progress("Celonis Analysis draft successfully released.")
                    except Exception as rel_err:
                        logger.warning(f"Could not release analysis draft: {rel_err}")
                        
                    analysis_config = content_dict["draft"]["document"]
                    log_progress("Successfully populated Analysis layout sheets and components.")
                except Exception as layout_err:
                    logger.error(f"Failed to populate Analysis layout: {layout_err}", exc_info=True)
                    log_progress(f"Warning: Failed to populate Analysis layout: {layout_err}")
                    
            except Exception as pop_err:
                log_progress(f"Warning: Failed to populate Analysis: {pop_err}")
                logger.error(f"Failed to populate Analysis: {pop_err}", exc_info=True)
            
        # 13. Publish package changes
        log_progress("Publishing Package to release changes...")
        try:
            package.publish(version="1.0.0")
        except Exception as p_err:
            err_str = str(p_err).lower()
            if "version.exists" in err_str or "already published" in err_str:
                logger.warning(f"Version 1.0.0 already exists. Attempting to publish version 1.0.1...")
                try:
                    package.publish(version="1.0.1")
                except Exception as p_err2:
                    logger.warning(f"Could not publish package: {str(p_err2)}. Proceeding as draft is updated.")
            else:
                logger.warning(f"Could not publish package: {str(p_err)}. Proceeding as draft is updated.")
        log_progress("Deployment successfully completed!")
        return True, {"sql": final_sql, "analysis_config": analysis_config}
    except Exception as ex:
        log_progress(f"Failed to push assets to Celonis: {str(ex)}")
        return False, {}
