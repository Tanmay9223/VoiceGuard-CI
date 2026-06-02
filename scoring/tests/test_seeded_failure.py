"""
scoring/tests/test_seeded_failure.py
Seeded failure tests — inject known-bad CallResults and assert
the evaluators correctly tag and fail them.

Run with: pytest scoring/tests/test_seeded_failure.py -v
"""
from __future__ import annotations

import pytest

from harness.models import (
    CallResult, CallScenario, EvalScore, TurnResult, Workflow, ToolCall
)
from harness.tools import ToolRegistry
from scoring.rules import DisclosureChecker, ToolCallChecker, RoutingChecker
from config.settings import Settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        gemini_api_key="test", deepgram_api_key="test",
        elevenlabs_api_key="test", mock_llm=True,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _make_scenario(expected_outcomes=None, tags=None) -> CallScenario:
    return CallScenario(
        id="test-scenario",
        name="Test Scenario",
        workflow=Workflow.QUOTE,
        caller_persona="Test caller",
        turns=[],
        expected_outcomes=expected_outcomes or [],
        tags=tags or ["quote"],
    )


def _make_result(turns=None, run_id="test-run") -> CallResult:
    return CallResult(
        scenario_id="test-scenario",
        run_id=run_id,
        turns=turns or [],
    )


# ---------------------------------------------------------------------------
# DisclosureChecker tests
# ---------------------------------------------------------------------------

class TestDisclosureChecker:

    def test_missing_recording_consent_fails(self):
        """Agent never mentioned recording consent → compliance_violation."""
        scenario = _make_scenario(expected_outcomes=[{"disclosed": "recording consent"}])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="Hello, how can I help you today?"),
        ])
        score = DisclosureChecker().evaluate(result, scenario)
        assert not score.passed
        assert score.failure_tag == "compliance_violation"
        assert "recording consent" in score.detail

    def test_missing_premium_disclaimer_fails(self):
        """Agent gave a quote without the premium disclaimer → missed_disclosure."""
        scenario = _make_scenario(expected_outcomes=[{"disclosed": "premium disclaimer"}])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="Your monthly premium is $127."),
        ])
        score = DisclosureChecker().evaluate(result, scenario)
        assert not score.passed
        assert score.failure_tag == "missed_disclosure"

    def test_all_disclosures_present_passes(self):
        """All required disclosures present → pass."""
        scenario = _make_scenario(expected_outcomes=[
            {"disclosed": "recording consent"},
            {"disclosed": "premium disclaimer"},
        ])
        result = _make_result(turns=[
            TurnResult(
                speaker="agent",
                text=(
                    "This call may be recorded for quality assurance. "
                    "Your monthly is $127. This is an estimate, subject to underwriting review."
                ),
            ),
        ])
        score = DisclosureChecker().evaluate(result, scenario)
        assert score.passed

    def test_no_disclosures_required_always_passes(self):
        """Scenario with no expected disclosures → always pass."""
        scenario = _make_scenario(expected_outcomes=[])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="Hello!"),
        ])
        score = DisclosureChecker().evaluate(result, scenario)
        assert score.passed


# ---------------------------------------------------------------------------
# ToolCallChecker tests
# ---------------------------------------------------------------------------

class TestToolCallChecker:

    def test_missing_tool_call_fails(self):
        """get_quote was expected but never called → tool_misuse."""
        scenario = _make_scenario(expected_outcomes=[
            {"tool_called": "get_quote", "args": {"vehicle": "...", "zip_code": "..."}}
        ])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="Let me look that up.", tool_calls=[]),
        ])
        score = ToolCallChecker().evaluate(result, scenario)
        assert not score.passed
        assert score.failure_tag == "tool_misuse"
        assert "get_quote" in score.detail

    def test_correct_tool_call_passes(self):
        """get_quote called with correct args → pass."""
        scenario = _make_scenario(expected_outcomes=[
            {"tool_called": "get_quote", "args": {"vehicle": "2022 Toyota Camry", "zip_code": "60601"}}
        ])
        result = _make_result(turns=[
            TurnResult(
                speaker="agent",
                text="Here is your quote.",
                tool_calls=[ToolCall(name="get_quote", args={"vehicle": "2022 Toyota Camry", "zip_code": "60601"})],
            ),
        ])
        score = ToolCallChecker().evaluate(result, scenario)
        assert score.passed

    def test_tool_called_with_missing_arg_fails(self):
        """get_quote called without zip_code → tool_misuse (bad arg case)."""
        scenario = _make_scenario(expected_outcomes=[
            {"tool_called": "get_quote", "args": {"vehicle": "2022 Toyota Camry", "zip_code": "60601"}}
        ])
        result = _make_result(turns=[
            TurnResult(
                speaker="agent",
                text="Here is your quote.",
                tool_calls=[ToolCall(name="get_quote", args={"vehicle": "2022 Toyota Camry"})],  # missing zip_code
            ),
        ])
        score = ToolCallChecker().evaluate(result, scenario)
        assert not score.passed
        assert score.failure_tag == "tool_misuse"
        assert "zip_code" in score.detail or "incorrect" in score.detail


# ---------------------------------------------------------------------------
# RoutingChecker tests
# ---------------------------------------------------------------------------

class TestRoutingChecker:

    def test_routing_expected_but_not_done_fails(self):
        """Scenario expects escalation but agent never called route_to_agent → wrong_routing."""
        scenario = _make_scenario(expected_outcomes=[{"routed": True}])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="I'll try to handle this myself.", tool_calls=[]),
        ])
        score = RoutingChecker().evaluate(result, scenario)
        assert not score.passed
        assert score.failure_tag == "wrong_routing"

    def test_routing_done_correctly_passes(self):
        """route_to_agent was called → pass."""
        scenario = _make_scenario(expected_outcomes=[{"routed": True}])
        result = _make_result(turns=[
            TurnResult(
                speaker="agent",
                text="I'll transfer you to a specialist.",
                tool_calls=[ToolCall(name="route_to_agent", args={"reason": "complex claim"})],
            ),
        ])
        score = RoutingChecker().evaluate(result, scenario)
        assert score.passed

    def test_routing_not_required_always_passes(self):
        """No routing in expected_outcomes → always pass regardless of tool calls."""
        scenario = _make_scenario(expected_outcomes=[])
        result = _make_result(turns=[
            TurnResult(speaker="agent", text="Here is your quote.", tool_calls=[]),
        ])
        score = RoutingChecker().evaluate(result, scenario)
        assert score.passed
