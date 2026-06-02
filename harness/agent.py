"""
harness/agent.py
VoiceAgent — the insurance voice agent under test.
Receives caller utterances, calls tools via ToolRegistry, returns response text.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from harness.models import ToolCall
from harness.tools import ToolRegistry

if TYPE_CHECKING:
    from config.settings import Settings
    from harness.providers import LLMProvider

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are Alex, a professional insurance voice agent at InsureCo.

RESPONSIBILITIES:
- Help callers with auto and home insurance quotes, policy renewals, and claims (FNOL).
- Collect required information politely and efficiently.
- Always disclose: (1) recording consent at the start of every call, (2) premium disclaimer when quoting, (3) coverage limitations when relevant.
- Escalate to a human agent when: caller is upset, situation is complex, or caller explicitly requests it.

TOOLS AVAILABLE:
{tool_descriptions}

TOOL USAGE RULES:
- Call get_quote ONLY when you have BOTH vehicle description AND zip code from the caller.
- Call lookup_policy ONLY when you have a policy_id from the caller.
- Call route_to_agent when escalation is needed, always include a clear reason.
- Never hallucinate coverage details, premiums, or policy terms not returned by tools.

COMPLIANCE RULES (ZERO TOLERANCE):
- Always say "This call may be recorded for quality assurance" at the start.
- Always say "This is an estimate. Final premium subject to underwriting review." when quoting.
- Never promise specific coverage terms not returned by the tool.

Respond naturally and conversationally. Keep responses concise — this is a voice call.
"""

_TOOL_CALL_INSTRUCTION = """\

When you need to call a tool, output ONLY a JSON object on its own line:
{"tool": "<tool_name>", "args": {<arg_key>: <arg_value>, ...}}

After the tool runs, I will provide the result and you continue the conversation.
Do NOT call tools unless you have all required args from the caller.
"""


class VoiceAgent:
    """
    The insurance voice agent under test.
    Wraps an LLMProvider + ToolRegistry and maintains conversation history.
    """

    def __init__(self, llm: "LLMProvider", tools: ToolRegistry, settings: "Settings") -> None:
        self._llm = llm
        self._tools = tools
        self._settings = settings
        self._history: list[dict[str, str]] = []
        self._system = _SYSTEM_PROMPT.format(
            tool_descriptions=tools.tool_call_descriptions()
        ) + _TOOL_CALL_INSTRUCTION

    def reset(self) -> None:
        """Clear conversation history and tool call history. Call between scenarios."""
        self._history.clear()
        self._tools.reset()

    def respond(self, caller_utterance: str) -> tuple[str, list[ToolCall]]:
        """
        Process a caller utterance and return (agent_response_text, tool_calls_made).
        May make one or more tool calls internally before returning the final response.
        """
        tool_calls_this_turn: list[ToolCall] = []
        self._history.append({"role": "user", "content": caller_utterance})

        # Allow up to 3 tool-call loops per turn
        for _ in range(3):
            raw = self._llm.complete(self._history, system=self._system)

            # Check if the response contains a tool call JSON
            tool_call_json = self._extract_tool_call(raw)
            if tool_call_json is None:
                # Normal text response — done
                self._history.append({"role": "assistant", "content": raw})
                return raw, tool_calls_this_turn

            # Execute the tool call
            tool_name = tool_call_json.get("tool", "")
            tool_args = tool_call_json.get("args", {})
            logger.info("[Agent] Tool call: %s(%s)", tool_name, tool_args)
            tool_result = self._tools.call(tool_name, **tool_args)
            tool_calls_this_turn.extend(
                [tc for tc in self._tools.call_history if tc.name == tool_name][-1:]
            )

            # Feed tool result back into the conversation
            tool_result_msg = f"[Tool result for {tool_name}]: {json.dumps(tool_result)}"
            self._history.append({"role": "assistant", "content": raw})
            self._history.append({"role": "user", "content": tool_result_msg})

        # Fallback if we somehow exit the loop
        final = self._llm.complete(self._history, system=self._system)
        self._history.append({"role": "assistant", "content": final})
        return final, tool_calls_this_turn

    @staticmethod
    def _extract_tool_call(text: str) -> dict | None:
        """
        Check if the LLM output contains a JSON tool call directive.
        Returns the parsed dict or None if it's a regular text response.
        """
        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("{") and '"tool"' in line:
                try:
                    data = json.loads(line)
                    if "tool" in data:
                        return data
                except json.JSONDecodeError:
                    pass
        return None
