"""
harness/loader.py
YAML scenario loader with Pydantic validation.
Also builds scenarios/index.json — the tag index required for --tags CLI filtering.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError, field_validator

from harness.models import (
    CallScenario, Turn, TurnExpectation, Workflow
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schema for YAML validation
# ---------------------------------------------------------------------------

class TurnExpectationSchema(BaseModel):
    must_include: list[str] = []
    must_not_include: list[str] = []
    tool_called: str | None = None
    tool_args: dict[str, Any] = {}
    should_route: bool = False


class TurnSchema(BaseModel):
    speaker: str
    text: str | None = None
    expect: TurnExpectationSchema | None = None

    @field_validator("speaker")
    @classmethod
    def speaker_must_be_valid(cls, v: str) -> str:
        if v not in ("caller", "agent"):
            raise ValueError(f"speaker must be 'caller' or 'agent', got {v!r}")
        return v


class ExpectedOutcomeSchema(BaseModel):
    tool_called: str | None = None
    args: dict[str, Any] = {}
    disclosed: str | None = None
    routed: bool | None = None


class ScenarioSchema(BaseModel):
    id: str
    name: str
    workflow: str
    caller_persona: str
    turns: list[TurnSchema]
    expected_outcomes: list[ExpectedOutcomeSchema] = []
    tags: list[str] = []
    failure_class: str | None = None
    use_audio_pipeline: bool = False

    @field_validator("workflow")
    @classmethod
    def workflow_must_be_valid(cls, v: str) -> str:
        valid = {w.value for w in Workflow}
        if v not in valid:
            raise ValueError(f"workflow must be one of {valid}, got {v!r}")
        return v


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class ScenarioLoader:
    """Loads YAML scenario files and builds/updates the tag index."""

    def load(self, path: Path) -> CallScenario:
        """Load a single scenario YAML file and return a validated CallScenario."""
        raw = yaml.safe_load(path.read_text())
        try:
            schema = ScenarioSchema.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"Invalid scenario {path}: {exc}") from exc

        turns = []
        for t in schema.turns:
            expectation = None
            if t.expect:
                expectation = TurnExpectation(
                    must_include=t.expect.must_include,
                    must_not_include=t.expect.must_not_include,
                    tool_called=t.expect.tool_called,
                    tool_args=t.expect.tool_args,
                    should_route=t.expect.should_route,
                )
            turns.append(Turn(speaker=t.speaker, text=t.text, expectation=expectation))

        return CallScenario(
            id=schema.id,
            name=schema.name,
            workflow=Workflow(schema.workflow),
            caller_persona=schema.caller_persona,
            turns=turns,
            expected_outcomes=[o.model_dump(exclude_none=True) for o in schema.expected_outcomes],
            tags=schema.tags,
            failure_class=schema.failure_class,
            use_audio_pipeline=schema.use_audio_pipeline,
        )

    def load_all(self, scenarios_dir: Path) -> list[CallScenario]:
        """Load all YAML files under scenarios_dir recursively."""
        paths = sorted(scenarios_dir.rglob("*.yaml"))
        scenarios = []
        for path in paths:
            if path.name == "index.json":
                continue
            try:
                scenarios.append(self.load(path))
            except Exception as exc:
                logger.error("Failed to load %s: %s", path, exc)
                raise
        return scenarios

    def build_index(self, scenarios_dir: Path) -> dict[str, Any]:
        """
        Build a tag index from all scenarios in scenarios_dir.
        Writes scenarios/index.json and returns the index dict.

        Structure:
            {
                "by_tag": {"ci-gate": ["scenario-id-1", ...], ...},
                "by_workflow": {"quote": [...], ...},
                "by_failure_class": {"missed_disclosure": [...], ...},
                "all_ids": [...]
            }
        """
        scenarios = self.load_all(scenarios_dir)
        index: dict[str, Any] = {
            "by_tag": {},
            "by_workflow": {},
            "by_failure_class": {},
            "all_ids": [],
        }

        for s in scenarios:
            index["all_ids"].append(s.id)

            # by_workflow
            wf = s.workflow.value
            index["by_workflow"].setdefault(wf, []).append(s.id)

            # by_tag
            for tag in s.tags:
                index["by_tag"].setdefault(tag, []).append(s.id)

            # by_failure_class
            if s.failure_class:
                index["by_failure_class"].setdefault(s.failure_class, []).append(s.id)

        # Write index.json
        index_path = scenarios_dir / "index.json"
        index_path.write_text(json.dumps(index, indent=2))
        logger.info("Built index.json: %d scenarios, %d tags",
                    len(scenarios), len(index["by_tag"]))
        return index

    @staticmethod
    def load_index(index_path: Path) -> dict[str, Any]:
        """Load an existing index.json file."""
        if not index_path.exists():
            raise FileNotFoundError(
                f"scenarios/index.json not found at {index_path}. "
                "Run `python -m harness.validate scenarios/` first."
            )
        return json.loads(index_path.read_text())

    @staticmethod
    def scenario_id_from_path(path: Path) -> str:
        """Derive the scenario ID from its file path (used for tag filtering)."""
        return path.stem  # filename without extension
