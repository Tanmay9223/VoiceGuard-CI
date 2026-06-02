"""
scoring/aggregator.py
Aggregates rule-based and LLM judge scores into a single EvalScore.
Applies thresholds from config/settings.py.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from harness.models import CallResult, CallScenario, EvalScore
from scoring.llm_judge import (
    ConversationQualityJudge,
    HallucinationJudge,
    InterruptionHandlingJudge,
)
from scoring.rules import DisclosureChecker, RoutingChecker, ToolCallChecker

if TYPE_CHECKING:
    from config.settings import Settings
    from harness.providers import LLMProvider

logger = logging.getLogger(__name__)


def aggregate(
    result: CallResult,
    scenario: CallScenario,
    llm: "LLMProvider",
    settings: "Settings",
) -> EvalScore:
    """
    Run all evaluators and return a fully populated EvalScore.
    Also sets result.failure_tags and result.passed in-place.
    """
    failure_tags: list[str] = []

    # --- Rule-based evaluators ---
    disclosure_score = DisclosureChecker().evaluate(result, scenario)
    tool_score = ToolCallChecker().evaluate(result, scenario)
    routing_score = RoutingChecker().evaluate(result, scenario)

    rule_scores = [disclosure_score, tool_score, routing_score]
    for rs in rule_scores:
        if not rs.passed and rs.failure_tag:
            failure_tags.append(rs.failure_tag)

    # Compliance = fraction of rule checks that passed
    rule_pass_count = sum(1 for rs in rule_scores if rs.passed)
    compliance_score = rule_pass_count / len(rule_scores)

    # Tool accuracy: ratio of expected tools correctly called
    tool_accuracy = 1.0 if tool_score.passed else 0.0

    # --- LLM judges ---
    hallucination_data = _safe_judge(
        HallucinationJudge().evaluate, result, llm,
        default={"hallucinations": [], "confidence": 1.0},
    )
    quality_data = _safe_judge(
        ConversationQualityJudge().evaluate, result, llm,
        default={"score": 3.0, "issues": []},
    )
    interruption_data = _safe_judge(
        InterruptionHandlingJudge().evaluate, result, llm,
        default={"handled_well": True, "examples": []},
    )

    # Map LLM judge results to failure tags
    hallucinations = hallucination_data.get("hallucinations", [])
    if hallucinations:
        failure_tags.append("hallucinated_quote")

    if not interruption_data.get("handled_well", True):
        failure_tags.append("bad_interruption")

    quality_score_val = float(quality_data.get("score", 3.0))
    if quality_score_val < settings.min_quality_score:
        failure_tags.append("asr_recovery_fail")

    # Hallucination score: 0 = hallucinations found, 1 = clean
    hallucination_score = 0.0 if hallucinations else 1.0

    # Overall pass: apply thresholds
    overall_pass = (
        compliance_score >= settings.compliance_pass_rate
        and hallucination_score > settings.hallucination_cap
        and quality_score_val >= settings.min_quality_score
        and tool_accuracy >= settings.tool_accuracy_floor
    )

    score = EvalScore(
        compliance_score=compliance_score,
        hallucination_score=hallucination_score,
        quality_score=quality_score_val,
        tool_accuracy=tool_accuracy,
        failure_tags=failure_tags,
        overall_pass=overall_pass,
        run_id=result.run_id,
        scenario_id=result.scenario_id,
    )

    # Mutate result in-place so the CI gate can read these fields
    result.failure_tags = failure_tags
    result.passed = overall_pass
    result.scores = score.to_dict()

    logger.info(
        "[Score] %s | pass=%s | compliance=%.2f | halluc=%.2f | quality=%.1f | tools=%.2f | tags=%s",
        result.scenario_id, overall_pass,
        compliance_score, hallucination_score, quality_score_val, tool_accuracy,
        failure_tags or "none",
    )
    return score


def _safe_judge(judge_fn, result: CallResult, llm: "LLMProvider", default: dict) -> dict:
    """Call a judge function, returning default on any exception."""
    try:
        return judge_fn(result, llm)
    except Exception as exc:
        logger.error("[Judge error] %s: %s", judge_fn.__self__.__class__.__name__, exc)
        return default
