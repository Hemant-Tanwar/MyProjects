from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime

class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    initial_requirement: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    status: str
    current_role: str
    requirement_file: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ArtifactCreate(BaseModel):
    stage: str
    content: str
    rationale: Optional[str] = None
    approved: Optional[bool] = False

class ArtifactEdit(BaseModel):
    content: str
    rationale: Optional[str] = None

class ArtifactResponse(BaseModel):
    id: int
    session_id: str
    stage: str
    version: int
    content: str
    rationale: Optional[str]
    approved: bool
    approved_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    session_id: str
    stage: str
    agent_name: str
    action: str
    prompt: Optional[str]
    response: Optional[str]
    error: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class ApprovalRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None

class RoleSwitchRequest(BaseModel):
    role: str

class TriggerAgentRequest(BaseModel):
    stage: str
    overrides: Optional[Dict[str, Any]] = None
