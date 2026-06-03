"""
scoring/llm_judge.py
Gemini-powered LLM judges for quality evaluation.
Covers 3 of the 7 failure classes:
  - HallucinationJudge       → hallucinated_quote
  - ConversationQualityJudge → asr_recovery_fail
  - InterruptionHandlingJudge → bad_interruption
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.models import CallResult
    from harness.providers import LLMProvider

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM = (
    "You are an expert evaluator of insurance call center conversations. "
    "Respond ONLY with valid JSON. Do not include explanation outside the JSON."
)


def _call_judge(llm: "LLMProvider", prompt: str) -> dict[str, Any]:
    """Call the LLM judge and parse JSON response. Raises on invalid JSON."""
    raw = llm.complete(
        [{"role": "user", "content": prompt}],
        system=_JUDGE_SYSTEM,
    )
    # Strip markdown code fences if present
    raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("[Judge] Failed to parse JSON: %r", raw[:200])
        raise ValueError(f"Judge returned invalid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Hallucination Judge
# ---------------------------------------------------------------------------

class HallucinationJudge:
    """
    Flags agent claims not supported by tool results or provided context.
    Covers: hallucinated_quote.
    Returns: {"hallucinations": [...], "confidence": 0.0-1.0}
    """

    def evaluate(self, result: "CallResult", llm: "LLMProvider") -> dict[str, Any]:
        # Only pass agent utterances to keep cost down
        agent_turns = "\n".join(
            f"[AGENT]: {t.text}"
            for t in result.turns if t.speaker == "agent" and t.text
        )
        tool_results = "\n".join(
            f"[TOOL {tc.name} RESULT]: {json.dumps(tc.response)}"
            for t in result.turns for tc in t.tool_calls if tc.response
        )

        prompt = f"""\
Analyze this insurance agent transcript for hallucinations.

TOOL RESULTS PROVIDED TO THE AGENT:
{tool_results or "(none — agent made no tool calls)"}

AGENT UTTERANCES:
{agent_turns}

TASK: Flag any specific claims the agent made about coverage, prices, or policy terms
that are NOT supported by the tool results above.

Respond with JSON:
{{
  "hallucinations": ["exact quote 1", "exact quote 2"],
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}
If no hallucinations, return an empty list."""

        result_data = _call_judge(llm, prompt)
        hallucinations = result_data.get("hallucinations", [])
        if hallucinations:
            logger.warning(
                "[HallucinationJudge] %d hallucination(s) in scenario %s",
                len(hallucinations), result.scenario_id,
            )
        return result_data


# ---------------------------------------------------------------------------
# Conversation Quality Judge
# ---------------------------------------------------------------------------

class ConversationQualityJudge:
    """
    Scores overall conversation quality: clarity, empathy, error recovery.
    Covers: asr_recovery_fail (poor recovery from transcription errors).
    Returns: {"score": 1-5, "issues": [...], "reasoning": "..."}
    """

    def evaluate(self, result: "CallResult", llm: "LLMProvider") -> dict[str, Any]:
        # Pass a slice of the full transcript (last 10 turns max)
        turns_slice = result.turns[-10:]
        transcript = "\n".join(
            f"[{t.speaker.upper()}]: {t.text}"
            for t in turns_slice if t.text
        )

        prompt = f"""\
Score this insurance call center conversation.

TRANSCRIPT:
{transcript}

TASK: Score this conversation on a scale of 1–5 across:
- Clarity: Was the agent easy to understand?
- Empathy: Did the agent acknowledge the caller's emotions?
- Error recovery: Did the agent handle confusion or mis-heard input gracefully?

Respond with JSON:
{{
  "score": 1-5,
  "issues": ["issue 1", "issue 2"],
  "reasoning": "brief explanation"
}}"""

        return _call_judge(llm, prompt)


# ---------------------------------------------------------------------------
# Interruption Handling Judge
# ---------------------------------------------------------------------------

class InterruptionHandlingJudge:
    """
    Evaluates whether the agent handled caller interruptions gracefully.
    Covers: bad_interruption.
    Returns: {"handled_well": bool, "examples": [...]}
    """

    def evaluate(self, result: "CallResult", llm: "LLMProvider") -> dict[str, Any]:
        # Look for signs of interruption in caller turns
        transcript = "\n".join(
            f"[{t.speaker.upper()}]: {t.text}"
            for t in result.turns if t.text
        )

        prompt = f"""\
Did the agent handle caller interruptions gracefully?

TRANSCRIPT:
{transcript}

TASK: Check if the caller interrupted the agent at any point (e.g., cutting off mid-sentence,
changing topic suddenly, asking a new question before the agent finished).
If so, did the agent recover gracefully (stayed on track, didn't lose context)?

Respond with JSON:
{{
  "interruptions_detected": true/false,
  "handled_well": true/false,
  "examples": ["example of good/bad handling"],
  "reasoning": "brief explanation"
}}"""

        return _call_judge(llm, prompt)
