import json
import logging
from sqlalchemy.orm import Session
from app.database import SessionModel, ArtifactModel, AuditLogModel
from app.agents.requirement_agent import RequirementAnalyzerAgent
from app.agents.sql_agent import TransformationSQLAgent
from app.agents.data_model_agent import DataModelAgent
from app.agents.knowledge_model_agent import KnowledgeModelAgent
from app.agents.view_agent import ViewAgent
from app.agents.qa_agent import QAAgent

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    def __init__(self):
        self.requirement_agent = RequirementAnalyzerAgent()
        self.sql_agent = TransformationSQLAgent()
        self.data_model_agent = DataModelAgent()
        self.knowledge_model_agent = KnowledgeModelAgent()
        self.view_agent = ViewAgent()
        self.qa_agent = QAAgent()

    def run_stage(self, db: Session, session_id: str, stage: str) -> ArtifactModel:
        session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        # Log start
        self._log_audit(db, session_id, stage, "run_started", f"Starting generation for stage: {stage}")

        try:
            # 1. Requirement Stage
            if stage == "requirement":
                # Get initial requirement description
                req_text = session.description or "Analyze the Procurement Process"
                rationale, content = self.requirement_agent.analyze(req_text)
                
            # 2. SQL Stage
            elif stage == "sql":
                req_artifact = self._get_approved_or_latest_artifact(db, session_id, "requirement")
                if not req_artifact:
                    raise ValueError("Requirement specification must be generated first.")
                rationale, content = self.sql_agent.generate(req_artifact.content)

            # 3. Data Model Stage
            elif stage == "data_model":
                req_artifact = self._get_approved_or_latest_artifact(db, session_id, "requirement")
                sql_artifact = self._get_approved_or_latest_artifact(db, session_id, "sql")
                if not req_artifact or not sql_artifact:
                    raise ValueError("Requirement specification and SQL transformations must be generated first.")
                rationale, content = self.data_model_agent.generate(req_artifact.content, sql_artifact.content)

            # 4. Knowledge Model Stage
            elif stage == "knowledge_model":
                req_artifact = self._get_approved_or_latest_artifact(db, session_id, "requirement")
                dm_artifact = self._get_approved_or_latest_artifact(db, session_id, "data_model")
                if not req_artifact or not dm_artifact:
                    raise ValueError("Requirement specification and Data Model must be generated first.")
                rationale, content = self.knowledge_model_agent.generate(req_artifact.content, dm_artifact.content)

            # 5. View Stage
            elif stage == "view":
                req_artifact = self._get_approved_or_latest_artifact(db, session_id, "requirement")
                km_artifact = self._get_approved_or_latest_artifact(db, session_id, "knowledge_model")
                if not req_artifact or not km_artifact:
                    raise ValueError("Requirement specification and Knowledge Model must be generated first.")
                rationale, content = self.view_agent.generate(req_artifact.content, km_artifact.content)

            # 6. QA Stage
            elif stage == "qa":
                req_artifact = self._get_approved_or_latest_artifact(db, session_id, "requirement")
                sql_artifact = self._get_approved_or_latest_artifact(db, session_id, "sql")
                dm_artifact = self._get_approved_or_latest_artifact(db, session_id, "data_model")
                km_artifact = self._get_approved_or_latest_artifact(db, session_id, "knowledge_model")
                view_artifact = self._get_approved_or_latest_artifact(db, session_id, "view")
                
                if not all([req_artifact, sql_artifact, dm_artifact, km_artifact, view_artifact]):
                    raise ValueError("All prior stages (Requirement, SQL, Data Model, Knowledge Model, View) must be completed before running QA.")
                
                rationale, content = self.qa_agent.validate(
                    req_artifact.content,
                    sql_artifact.content,
                    dm_artifact.content,
                    km_artifact.content,
                    view_artifact.content
                )
            else:
                raise ValueError(f"Unknown workflow stage: {stage}")

            # Save the generated artifact (versioned)
            latest_version = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == session_id,
                ArtifactModel.stage == stage
            ).order_by(ArtifactModel.version.desc()).first()

            version = 1 if not latest_version else latest_version.version + 1

            artifact = ArtifactModel(
                session_id=session_id,
                stage=stage,
                version=version,
                content=content,
                rationale=rationale,
                approved=False
            )
            db.add(artifact)

            # Log completion
            self._log_audit(db, session_id, stage, "run_completed", f"Generation completed. Version: {version}", response=content)
            
            # Switch session status appropriately based on stages
            next_status_map = {
                "requirement": "sql_transformation",
                "sql": "data_modeling",
                "data_model": "knowledge_modeling",
                "knowledge_model": "view_generation",
                "view": "qa_validation",
                "qa": "qa_validation"  # QA stays in validation until promoted
            }
            session.status = next_status_map.get(stage, session.status)
            db.commit()
            db.refresh(artifact)
            return artifact

        except Exception as e:
            logger.error(f"Error executing stage {stage}: {str(e)}")
            self._log_audit(db, session_id, stage, "run_failed", f"Failed to execute stage: {stage}", error=str(e))
            db.rollback()
            raise e

    def _get_approved_or_latest_artifact(self, db: Session, session_id: str, stage: str) -> ArtifactModel:
        # Try approved first
        artifact = db.query(ArtifactModel).filter(
            ArtifactModel.session_id == session_id,
            ArtifactModel.stage == stage,
            ArtifactModel.approved == True
        ).order_by(ArtifactModel.version.desc()).first()
        
        # Fallback to latest
        if not artifact:
            artifact = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == session_id,
                ArtifactModel.stage == stage
            ).order_by(ArtifactModel.version.desc()).first()
            
        return artifact

    def _log_audit(self, db: Session, session_id: str, stage: str, action: str, prompt: str, response: str = None, error: str = None):
        agent_names = {
            "requirement": "Requirement Analyzer Agent",
            "sql": "Transformation SQL Agent",
            "data_model": "Data Model Agent",
            "knowledge_model": "Knowledge Model Agent",
            "view": "View Agent",
            "qa": "QA / Validation Agent"
        }
        
        log = AuditLogModel(
            session_id=session_id,
            stage=stage,
            agent_name=agent_names.get(stage, "Orchestrator"),
            action=action,
            prompt=prompt,
            response=response,
            error=error
        )
        db.add(log)
        db.commit()
