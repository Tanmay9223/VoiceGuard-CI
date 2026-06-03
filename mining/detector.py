"""
mining/detector.py
Runs quality and hallucination checks on production calls.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from harness.models import CallResult, TurnResult, ToolCall
from mining.models import ProductionCall, FailureEvent
from scoring.llm_judge import ConversationQualityJudge, HallucinationJudge

if TYPE_CHECKING:
    from harness.providers import LLMProvider

logger = logging.getLogger(__name__)


def detect_failures(call: ProductionCall, llm: "LLMProvider") -> FailureEvent | None:
    """
    Evaluate a ProductionCall using the scoring judges.
    Returns a FailureEvent if it fails thresholds, else None.
    """
    # 1. Convert ProductionCall to a proxy CallResult for the judges
    proxy_turns = []
    for t in call.turns:
        tcs = [ToolCall(name=tc["name"], args=tc.get("args", {}), response=tc.get("response")) for tc in t.tool_calls]
        proxy_turns.append(TurnResult(speaker=t.speaker, text=t.text, tool_calls=tcs))
        
    proxy_result = CallResult(
        scenario_id="prod-proxy",
        run_id=call.call_id,
        turns=proxy_turns
    )

    failure_tags = []

    # 2. Hallucination Check
    hallucination_data = HallucinationJudge().evaluate(proxy_result, llm)
    if hallucination_data.get("hallucinations"):
        failure_tags.append("hallucinated_quote")

    # 3. Quality / Recovery Check
    quality_data = ConversationQualityJudge().evaluate(proxy_result, llm)
    if float(quality_data.get("score", 3.0)) < 4.0:
        failure_tags.append("poor_quality")
        
    # 4. Routing check
    # If the caller asks for a human but route_to_agent is never called
    transcript_lower = proxy_result.full_transcript().lower()
    if ("human" in transcript_lower or "agent" in transcript_lower or "representative" in transcript_lower):
        if not any(tc.name == "route_to_agent" for tc in proxy_result.all_tool_calls()):
            failure_tags.append("missed_routing")

    if failure_tags:
        logger.warning("[Detector] Call %s failed with tags: %s", call.call_id, failure_tags)
        return FailureEvent(call_id=call.call_id, failure_tags=failure_tags, call_data=call)
    
    logger.info("[Detector] Call %s passed all checks.", call.call_id)
    return None
