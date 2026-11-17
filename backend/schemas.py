from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_serializer


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

    @field_serializer("created_at")
    def _as_utc(self, value: datetime) -> str:
        # La base stocke l'heure UTC sans fuseau : on le précise, sinon le navigateur
        # l'interprète comme une heure locale et l'affiche décalée.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()


class ScanDetailOut(ScanOut):
    violations: List[Violation]
