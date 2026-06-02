"""
scoring/rules.py
Deterministic rule-based evaluators.
Covers 4 of the 7 failure classes:
  - DisclosureChecker  → missed_disclosure, compliance_violation
  - ToolCallChecker    → tool_misuse (wrong tool OR bad/missing args)
  - RoutingChecker     → wrong_routing
"""
from __future__ import annotations

import logging
from typing import Any

from harness.models import CallResult, CallScenario, RuleScore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required disclosure phrases (case-insensitive substring match)
# ---------------------------------------------------------------------------
_REQUIRED_DISCLOSURES: dict[str, list[str]] = {
    "recording consent": [
        "this call may be recorded",
        "call may be recorded",
        "recorded for quality",
        "recording for quality",
    ],
    "premium disclaimer": [
        "this is an estimate",
        "estimate",
        "subject to underwriting",
        "final premium",
    ],
    "coverage limitations": [
        "coverage limitations",
        "coverage may vary",
        "limitations apply",
        "subject to policy terms",
        "terms and conditions",
    ],
}


class DisclosureChecker:
    """
    Verify required disclosures appear somewhere in the agent's turns.
    Covers: missed_disclosure + compliance_violation.

    A disclosure is considered present if ANY of its variant phrases appears
    in ANY agent utterance (case-insensitive).
    """

    def evaluate(self, result: CallResult, scenario: CallScenario) -> RuleScore:
        # Collect required disclosures from scenario's expected_outcomes
        required: list[str] = []
        for outcome in scenario.expected_outcomes:
            if "disclosed" in outcome:
                required.append(outcome["disclosed"])

        # Collect all agent text
        agent_text = " ".join(
            t.text.lower() for t in result.turns if t.speaker == "agent" and t.text
        )

        missing: list[str] = []
        for disclosure_key in required:
            variants = _REQUIRED_DISCLOSURES.get(disclosure_key, [disclosure_key.lower()])
            found = any(v in agent_text for v in variants)
            if not found:
                missing.append(disclosure_key)
                logger.warning(
                    "[DisclosureChecker] Missing disclosure %r in scenario %s",
                    disclosure_key, result.scenario_id,
                )

        if missing:
            tag = "compliance_violation" if "recording consent" in missing else "missed_disclosure"
            return RuleScore(
                passed=False,
                detail=f"Missing required disclosures: {missing}",
                failure_tag=tag,
            )
        return RuleScore(passed=True, detail="All required disclosures present.")


class ToolCallChecker:
    """
    Two-part check: (1) correct tool was called, (2) args match expected schema.
    Covers: tool_misuse (both wrong-tool AND bad-arg cases).

    Example: calling get_quote without 'zip_code' → tool_misuse,
             even if the tool name is correct.
    """

    def evaluate(self, result: CallResult, scenario: CallScenario) -> RuleScore:
        # Build expected tool calls from scenario outcomes
        expected_calls: list[dict[str, Any]] = [
            o for o in scenario.expected_outcomes if "tool_called" in o
        ]

        if not expected_calls:
            return RuleScore(passed=True, detail="No tool calls expected for this scenario.")

        actual_calls = result.all_tool_calls()
        actual_names = {tc.name for tc in actual_calls}

        issues: list[str] = []

        for expected in expected_calls:
            tool_name = expected["tool_called"]
            expected_args: dict[str, Any] = expected.get("args", {})

            # Part 1: Was the tool called at all?
            matching = [tc for tc in actual_calls if tc.name == tool_name]
            if not matching:
                issues.append(f"Expected tool {tool_name!r} was never called.")
                continue

            # Part 2: Were required args present in any call to this tool?
            arg_ok = False
            for tc in matching:
                arg_issues = []
                for arg_key, expected_val in expected_args.items():
                    actual_val = tc.args.get(arg_key)
                    if actual_val is None:
                        arg_issues.append(f"missing arg {arg_key!r}")
                    elif expected_val and str(actual_val).strip() != str(expected_val).strip():
                        # Only check value if expected_val is not empty/wildcard
                        if expected_val not in ("...", "*", ""):
                            arg_issues.append(
                                f"arg {arg_key!r}: expected {expected_val!r}, got {actual_val!r}"
                            )
                if not arg_issues:
                    arg_ok = True
                    break

            if not arg_ok:
                issues.append(
                    f"Tool {tool_name!r} was called but with incorrect/missing args. "
                    f"Expected args: {expected_args}"
                )

        if issues:
            return RuleScore(
                passed=False,
                detail="; ".join(issues),
                failure_tag="tool_misuse",
            )
        return RuleScore(passed=True, detail="All required tools called with correct args.")


class RoutingChecker:
    """
    Verify escalation to a human agent happened when required.
    Covers: wrong_routing.
    """

    def evaluate(self, result: CallResult, scenario: CallScenario) -> RuleScore:
        # Check if scenario expects routing
        routing_expected = any(
            o.get("routed") is True for o in scenario.expected_outcomes
        )

        if not routing_expected:
            return RuleScore(passed=True, detail="No routing required for this scenario.")

        # Check if route_to_agent was actually called
        routed = any(tc.name == "route_to_agent" for tc in result.all_tool_calls())

        if not routed:
            return RuleScore(
                passed=False,
                detail="Expected escalation to human agent but route_to_agent was never called.",
                failure_tag="wrong_routing",
            )
        return RuleScore(passed=True, detail="Correctly escalated to human agent.")
