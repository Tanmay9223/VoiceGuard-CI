"""
harness/models.py
Core data models for VoiceGuard CI.
These typed contracts flow through every module — harness, scoring, CI gate, and dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Workflow(str, Enum):
    QUOTE = "quote"
    RENEWAL = "renewal"
    CLAIMS = "claims"
    LEAD = "lead"


class ReleaseDecision(str, Enum):
    SHIP = "ship"
    WARN = "ship_with_warnings"
    BLOCK = "block_merge"


class TriggerType(str, Enum):
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Scenario models (input)
# ---------------------------------------------------------------------------

@dataclass
class TurnExpectation:
    """What we expect the agent to do on a given turn."""
    must_include: list[str] = field(default_factory=list)   # phrases that must appear
    must_not_include: list[str] = field(default_factory=list)
    tool_called: str | None = None
    tool_args: dict[str, Any] = field(default_factory=dict)  # expected arg schema
    should_route: bool = False


@dataclass
class Turn:
    speaker: str                        # "caller" | "agent"
    text: str | None = None             # seed text (caller turns) or None (agent generates)
    expectation: TurnExpectation | None = None


@dataclass
class CallScenario:
    id: str
    name: str
    workflow: Workflow
    caller_persona: str                 # 1–2 sentence description for CallerSimulator
    turns: list[Turn]
    expected_outcomes: list[dict[str, Any]]
    tags: list[str]
    failure_class: str | None = None    # e.g. "missed_disclosure" — set on red-team scenarios
    use_audio_pipeline: bool = False    # True only for asr-noise-injection


# ---------------------------------------------------------------------------
# Result models (output)
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    response: Any | None = None


@dataclass
class TurnResult:
    speaker: str
    text: str
    audio_bytes: bytes | None = None    # populated only when use_audio_pipeline=True
    tool_calls: list[ToolCall] = field(default_factory=list)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CallResult:
    scenario_id: str
    run_id: str
    turns: list[TurnResult]
    scores: dict[str, float] = field(default_factory=dict)
    failure_tags: list[str] = field(default_factory=list)
    passed: bool = False
    error: str | None = None            # set if the call raised an exception
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def full_transcript(self) -> str:
        """Return full call as a single string for LLM judges."""
        lines = [f"[{t.speaker.upper()}]: {t.text}" for t in self.turns]
        return "\n".join(lines)

    def agent_utterances(self) -> list[str]:
        """Return only agent turns — used to pass to judges."""
        return [t.text for t in self.turns if t.speaker == "agent"]

    def all_tool_calls(self) -> list[ToolCall]:
        """Flatten all tool calls across all turns."""
        return [tc for t in self.turns for tc in t.tool_calls]


@dataclass
class EvalRun:
    run_id: str
    trigger: TriggerType
    commit_sha: str
    results: list[CallResult]
    release_decision: ReleaseDecision = ReleaseDecision.SHIP
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)


# ---------------------------------------------------------------------------
# Scoring models
# ---------------------------------------------------------------------------

@dataclass
class RuleScore:
    """Result of a single rule-based evaluator."""
    passed: bool
    detail: str
    failure_tag: str | None = None      # set when passed=False


@dataclass
class EvalScore:
    """Aggregated score for a single CallResult."""
    compliance_score: float             # 0–1, rule-based (DisclosureChecker + RoutingChecker)
    hallucination_score: float          # 0–1, LLM judge (0 = no hallucinations)
    quality_score: float                # 1–5, LLM judge
    tool_accuracy: float                # 0–1, rule-based (ToolCallChecker)
    failure_tags: list[str] = field(default_factory=list)
    overall_pass: bool = False
    run_id: str = ""
    scenario_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_id": self.scenario_id,
            "compliance_score": self.compliance_score,
            "hallucination_score": self.hallucination_score,
            "quality_score": self.quality_score,
            "tool_accuracy": self.tool_accuracy,
            "failure_tags": self.failure_tags,
            "overall_pass": self.overall_pass,
            "timestamp": self.timestamp.isoformat(),
        }
