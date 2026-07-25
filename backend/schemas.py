from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    url: str


class ViolationNode(BaseModel):
    html: str
    target: List[str]
    failure_summary: Optional[str] = None


class Violation(BaseModel):
    id: str
    impact: str
    description: str
    help: str
    help_url: str
    tags: List[str]
    nodes: List[ViolationNode]


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    score: float
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int
    passes_count: int
    error: Optional[str] = None
    created_at: datetime


class ScanDetailOut(ScanOut):
    violations: List[Violation]
