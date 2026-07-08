from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class TargetCreate(BaseModel):
    name: str
    target_type: str
    url: Optional[str] = None
    ip_address: Optional[str] = None
    code_path: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    notes: Optional[str] = None
    scope_domains: Optional[List[str]] = None


class EngagementCreate(BaseModel):
    name: str
    description: Optional[str] = None
    targets: List[TargetCreate] = []
    mode: str = "standard"
    scope_domains: List[str] = []

class FindingOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    severity: str
    cve_id: Optional[str]
    cwe_id: Optional[str]
    cvss_score: Optional[float]
    confidence: float
    is_verified: bool
    is_novel: bool
    payload: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}

class AgentRunOut(BaseModel):
    id: int
    agent_name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    findings_count: int
    rl_reward: Optional[float]

    model_config = {"from_attributes": True}

class TargetOut(BaseModel):
    id: int
    name: str
    target_type: str
    url: Optional[str] = None
    ip_address: Optional[str] = None
    code_path: Optional[str] = None

    model_config = {"from_attributes": True}


class EngagementOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    agent_runs: List[AgentRunOut] = []
    targets: List[TargetOut] = []
    findings: List[FindingOut] = []

    model_config = {"from_attributes": True}
