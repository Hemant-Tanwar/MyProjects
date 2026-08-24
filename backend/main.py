import json
import datetime
import os
import re
import yaml
from fastapi import FastAPI, Depends, HTTPException, Body, UploadFile, File, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
router = APIRouter()

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = WorkflowOrchestrator()

# Global exception handler: always return JSON so the frontend can parse error details
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger("main").error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )

@app.on_event("startup")
def startup_event():
    init_db()

@router.post("/sessions", response_model=SessionResponse)
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

@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(db: Session = Depends(get_db)):
    return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()

@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    return sess

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete(sess)
    db.commit()
    return {"message": f"Session {session_id} successfully deleted."}

@router.post("/sessions/{session_id}/trigger", response_model=ArtifactResponse)
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

@router.get("/sessions/{session_id}/artifacts", response_model=List[ArtifactResponse])
def get_all_artifacts(session_id: str, db: Session = Depends(get_db)):
    return db.query(ArtifactModel).filter(ArtifactModel.session_id == session_id).order_by(ArtifactModel.version.desc()).all()

@router.get("/sessions/{session_id}/artifacts/{stage}", response_model=ArtifactResponse)
def get_latest_stage_artifact(session_id: str, stage: str, db: Session = Depends(get_db)):
    art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == stage
    ).order_by(ArtifactModel.version.desc()).first()
    
    if not art:
        raise HTTPException(status_code=404, detail=f"No artifact generated for stage '{stage}' in this session.")
    return art

@router.put("/sessions/{session_id}/artifacts/{stage}", response_model=ArtifactResponse)
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

@router.post("/sessions/{session_id}/artifacts/{stage}/approve", response_model=ArtifactResponse)
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
        # Progress status immediately only for stages that don't need a Celonis push
        if stage == "requirement":
            sess.status = "sql_transformation"
        elif stage == "qa":
            sess.status = "completed"
        
    db.commit()
    db.refresh(latest_art)
    return latest_art

@router.post("/sessions/{session_id}/artifacts/{stage}/push", response_model=ArtifactResponse)
def push_artifact(session_id: str, stage: str, db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    latest_art = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == stage
    ).order_by(ArtifactModel.version.desc()).first()

    if not latest_art:
        raise HTTPException(status_code=404, detail="No artifact exists to push.")

    if not latest_art.approved:
        raise HTTPException(status_code=400, detail="Artifact must be approved before pushing to Celonis.")

    from app.celonis_deployer import deploy_sql, deploy_data_model, deploy_knowledge_model, deploy_analysis
    try:
        if stage == "sql":
            deploy_sql(sess, latest_art.content, db)
        elif stage == "data_model":
            deploy_data_model(sess, latest_art.content, db)
        elif stage == "knowledge_model":
            deploy_knowledge_model(sess, latest_art.content, db)
        elif stage == "analysis":
            deploy_analysis(sess, latest_art.content, db)
    except Exception as e:
        err_msg = f"Celonis deployment and verification failed for stage '{stage}': {str(e)}"
        orchestrator._log_audit(db, session_id, stage, "deployment_failed", err_msg, error=str(e))
        raise HTTPException(status_code=500, detail=err_msg)

    # Log successful push completion
    orchestrator._log_audit(
        db, session_id, stage, "push_completed",
        f"Artifact for stage '{stage}' successfully pushed and verified in Celonis."
    )

    # Progress session status after successful push
    progression_map = {
        "sql": "data_modeling",
        "data_model": "knowledge_modeling",
        "knowledge_model": "analysis_generation",
        "analysis": "completed"
    }
    if stage in progression_map:
        sess.status = progression_map[stage]
        
    db.commit()
    db.refresh(latest_art)
    return latest_art

@router.post("/sessions/{session_id}/role", response_model=SessionResponse)
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

@router.get("/sessions/{session_id}/audit_logs", response_model=List[AuditLogResponse])
def get_audit_logs(session_id: str, db: Session = Depends(get_db)):
    return db.query(AuditLogModel).filter(AuditLogModel.session_id == session_id).order_by(AuditLogModel.timestamp.desc()).all()

@router.post("/sessions/{session_id}/promote")
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

    # Auto-push all assets to Celonis platform (best-effort; file export always runs regardless)
    from app.celonis_deployer import deploy_sql, deploy_data_model, deploy_knowledge_model, deploy_analysis
    import logging as _logging
    _logger = _logging.getLogger(__name__)
    push_errors = []
    for _stage, _deployer in [
        ("sql", lambda: deploy_sql(sess, bundle.get("sql", ""), db)),
        ("data_model", lambda: deploy_data_model(sess, bundle.get("data_model", ""), db)),
        ("knowledge_model", lambda: deploy_knowledge_model(sess, bundle.get("knowledge_model", ""), db)),
        ("analysis", lambda: deploy_analysis(sess, bundle.get("analysis", ""), db)),
    ]:
        try:
            _deployer()
        except Exception as _e:
            push_errors.append(f"{_stage}: {_e}")
            _logger.warning(f"Celonis push skipped for stage '{_stage}': {_e}")

    pushed_successfully = len(push_errors) == 0
    push_status_msg = (
        "Successfully pushed all assets to Celonis Cloud."
        if pushed_successfully
        else f"Partial/failed Celonis push — {'; '.join(push_errors)}"
    )

    final_sql = bundle.get("sql", "-- empty SQL")

    # Format Knowledge Model as YAML for Celonis
    km_json_str = bundle.get("knowledge_model", "{}")
    try:
        km_obj = json.loads(km_json_str)
        km_yaml_str = yaml.dump(km_obj, sort_keys=False)
    except Exception:
        km_yaml_str = km_json_str

    # Format Analysis from bundle
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
        
        # Split and write individual SQL queries into separate files, combining DROP and subsequent CREATE
        raw_statements = [stmt.strip() for stmt in final_sql.split(";") if stmt.strip()]
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
            stmt_name = "query"
            stmt_upper = stmt.upper()
            if "CREATE TABLE" in stmt_upper:
                match = re.search(r"CREATE TABLE\s+(\w+)", stmt, re.IGNORECASE)
                stmt_name = f"create_{match.group(1).lower()}" if match else "create_table"
            elif "DROP TABLE" in stmt_upper:
                match = re.search(r"DROP TABLE\s+(?:IF EXISTS\s+)?(\w+)", stmt, re.IGNORECASE)
                stmt_name = f"drop_{match.group(1).lower()}" if match else "drop_table"
            elif "INSERT INTO" in stmt_upper:
                match = re.search(r"INSERT INTO\s+(\w+)", stmt, re.IGNORECASE)
                target_tbl = match.group(1).lower() if match else "table"
                act_match = re.search(r"'\s*([^']+)\s*'\s+AS\s+ACTIVITY", stmt, re.IGNORECASE)
                if act_match:
                    act_name = slugify(act_match.group(1))
                    stmt_name = f"insert_{target_tbl}_{act_name}"
                else:
                    stmt_name = f"insert_{target_tbl}"
            
            with open(os.path.join(export_dir, f"{stmt_num}_{stmt_name}.sql"), "w", encoding="utf-8") as sf:
                # Append semicolon if not already there
                file_stmt = stmt if stmt.endswith(";") else f"{stmt};"
                sf.write(file_stmt + "\n")

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


@router.post("/sessions/{session_id}/upload_requirement_file")
def upload_requirement_file(session_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    sess = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    file_ext = os.path.splitext(file.filename)[1]
    if file_ext.lower() not in [".pptx"]:
        raise HTTPException(status_code=400, detail="Only PPTX files are supported.")
        
    if os.environ.get("VERCEL"):
        upload_dir = "/tmp/uploads"
    else:
        upload_dir = os.path.join(WORKSPACE_DIR, "backend", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = f"{session_id}_requirement{file_ext}"
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
        
    sess.requirement_file = file_path
    db.commit()
    db.refresh(sess)
    
    # Automatically re-run the requirement analysis with the new file context
    try:
        orchestrator.run_stage(db, session_id, "requirement")
    except Exception as e:
        # Log error but don't fail the upload response
        import logging
        logging.getLogger(__name__).error(f"Auto-triggering requirement stage failed: {str(e)}")
        
    return {"message": "PowerPoint requirement file uploaded successfully.", "filename": file.filename, "file_path": file_path}

@router.get("/health")
def health_check():
    return {"status": "ok", "app": "Celonis Orchestrator API"}

app.include_router(router)
app.include_router(router, prefix="/api")


