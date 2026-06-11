import io
import zipfile
import json
import datetime
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import init_db, get_db, SessionModel, ArtifactModel, AuditLogModel
from app.schemas import (
    SessionCreate, SessionResponse, ArtifactResponse, ArtifactEdit,
    AuditLogResponse, ApprovalRequest, RoleSwitchRequest, TriggerAgentRequest
)
from app.orchestrator import WorkflowOrchestrator
from app.config import ROLES

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
        f"Session created with initial requirement: {session_data.initial_requirement[:100]}..."
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
        "view": ["Process Analyst", "Admin"],
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
    
    # Move session status logic
    if req.approved:
        progression_map = {
            "requirement": "sql_transformation",
            "sql": "data_modeling",
            "data_model": "knowledge_modeling",
            "knowledge_model": "view_generation",
            "view": "qa_validation",
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

    # 2. Check QA Validation status
    qa_artifact = db.query(ArtifactModel).filter(
        ArtifactModel.session_id == session_id,
        ArtifactModel.stage == "qa"
    ).order_by(ArtifactModel.version.desc()).first()

    if not qa_artifact:
        raise HTTPException(status_code=400, detail="QA validation has not been executed yet. Run QA first.")

    try:
        report = json.loads(qa_artifact.content)
        score = report.get("total_score", 0)
    except Exception:
        score = 0

    if score < 80:
        raise HTTPException(status_code=400, detail=f"Deployment rejected: QA validation score ({score}) is below deployment threshold of 80.")

    # Fetch all latest stage artifacts
    stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
    bundle = {}
    for stg in stages:
        art = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == session_id,
            ArtifactModel.stage == stg
        ).order_by(ArtifactModel.version.desc()).first()
        bundle[stg] = art.content if art else ""

    # Generate a ZIP deliverable in-memory containing all code assets and runbooks
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("business_requirement_spec.json", bundle.get("requirement", "{}"))
        zip_file.writestr("transformations.sql", bundle.get("sql", "-- empty SQL"))
        zip_file.writestr("celonis_data_model.json", bundle.get("data_model", "{}"))
        zip_file.writestr("knowledge_model.json", bundle.get("knowledge_model", "{}"))
        zip_file.writestr("studio_view_spec.json", bundle.get("view", "{}"))
        zip_file.writestr("qa_validation_checklist.json", bundle.get("qa", "{}"))
        
        # Add a deployment runbook
        runbook = (
            f"# Deployment Runbook - {sess.name}\n"
            f"Promoted by: {sess.current_role}\n"
            f"QA Validation Score: {score}/100\n"
            f"Deployment Timestamp: {datetime.datetime.utcnow().isoformat()}\n\n"
            "## Promotion Steps:\n"
            "1. Execute `transformations.sql` in Celonis Event Collection (Data Pool).\n"
            "2. Map `TEMP_P2P_CASES` (Case Table) and `TEMP_P2P_EVENT_LOG` (Event Table) in Data Model.\n"
            "3. Create new Knowledge Model package using the defined schema in `knowledge_model.json`.\n"
            "4. Publish Studio View layout using components list in `studio_view_spec.json`.\n"
        )
        zip_file.writestr("deployment_runbook.md", runbook)

    zip_buffer.seek(0)
    
    # Update session status
    sess.status = "completed"
    orchestrator._log_audit(
        db, session_id, "governance", "promoted_to_production",
        f"Deployment bundle successfully built and promoted. QA Score: {score}"
    )
    db.commit()

    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": f"attachment; filename=celonis_deployment_{session_id}.zip"}
    )
