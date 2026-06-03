"""
mining/models.py
Data models for the Hard-Case Mining pipeline.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProductionTurn:
    speaker: str
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ProductionCall:
    """A proxy model representing a completed call transcript."""
    call_id: str
    turns: list[ProductionTurn]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def full_transcript(self) -> str:
        lines = [f"[{t.speaker.upper()}]: {t.text}" for t in self.turns]
        return "\n".join(lines)


@dataclass
class FailureEvent:
    """A detected failure in a production call."""
    call_id: str
    failure_tags: list[str]
    call_data: ProductionCall
