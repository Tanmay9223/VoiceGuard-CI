"""
harness/tools.py
Mock tool registry for the VoiceAgent.
All tool calls and their args are captured and attached to TurnResult for downstream scoring.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from harness.models import ToolCall

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock data fixtures
# ---------------------------------------------------------------------------

_QUOTE_FIXTURES: dict[str, dict] = {
    "default": {
        "monthly_premium": 127.50,
        "annual_premium": 1530.00,
        "coverage": "Comprehensive + Liability",
        "deductible": 500,
        "disclaimer": "This is an estimate. Final premium subject to underwriting review.",
    }
}

_POLICY_FIXTURES: dict[str, dict] = {
    "POL-001": {
        "holder": "Jane Smith",
        "vehicle": "2021 Honda Civic",
        "status": "Active",
        "expiry": "2026-12-31",
        "coverage": "Comprehensive",
    },
    "POL-999": {
        "holder": "Unknown",
        "vehicle": "N/A",
        "status": "Not Found",
        "expiry": None,
        "coverage": None,
    },
}

_ROUTING_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_quote(vehicle: str, zip_code: str) -> dict[str, Any]:
    """
    Return a mock insurance quote.
    Required args: vehicle (str), zip_code (str).
    Missing either arg → ToolCallChecker flags tool_misuse.
    """
    if not vehicle or not zip_code:
        raise ValueError("get_quote requires both 'vehicle' and 'zip_code' args.")
    fixture = _QUOTE_FIXTURES.get("default", {}).copy()
    fixture["vehicle"] = vehicle
    fixture["zip_code"] = zip_code
    logger.info("[Tool] get_quote(%r, %r) → %s/month", vehicle, zip_code, fixture["monthly_premium"])
    return fixture


def lookup_policy(policy_id: str) -> dict[str, Any]:
    """Return mock policy details for a given policy_id."""
    if not policy_id:
        raise ValueError("lookup_policy requires 'policy_id' arg.")
    result = _POLICY_FIXTURES.get(policy_id, _POLICY_FIXTURES["POL-999"])
    logger.info("[Tool] lookup_policy(%r) → status=%s", policy_id, result["status"])
    return result


def route_to_agent(reason: str) -> dict[str, Any]:
    """Log a routing decision (human escalation)."""
    if not reason:
        raise ValueError("route_to_agent requires 'reason' arg.")
    entry = {"reason": reason, "status": "routed"}
    _ROUTING_LOG.append(entry)
    logger.info("[Tool] route_to_agent(%r) → routed", reason)
    return entry


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

# Maps tool name → (callable, required_args)
_REGISTRY: dict[str, tuple] = {
    "get_quote": (get_quote, ["vehicle", "zip_code"]),
    "lookup_policy": (lookup_policy, ["policy_id"]),
    "route_to_agent": (route_to_agent, ["reason"]),
}


@dataclass
class ToolRegistry:
    """
    Wraps mock tool functions and records every call + args.
    Call history is read by ToolCallChecker in the scoring phase.
    """
    call_history: list[ToolCall] = field(default_factory=list)

    def call(self, tool_name: str, **kwargs: Any) -> Any:
        """Invoke a mock tool by name, record the call, and return the response."""
        if tool_name not in _REGISTRY:
            logger.warning("[Tool] Unknown tool called: %r", tool_name)
            tc = ToolCall(name=tool_name, args=kwargs, response=None)
            self.call_history.append(tc)
            return None

        fn, _ = _REGISTRY[tool_name]
        try:
            response = fn(**kwargs)
        except ValueError as exc:
            logger.error("[Tool] %s raised ValueError: %s", tool_name, exc)
            response = {"error": str(exc)}

        tc = ToolCall(name=tool_name, args=kwargs, response=response)
        self.call_history.append(tc)
        return response

    def reset(self) -> None:
        """Clear call history between scenarios."""
        self.call_history.clear()

    @staticmethod
    def available_tools() -> list[str]:
        return list(_REGISTRY.keys())

    @staticmethod
    def required_args(tool_name: str) -> list[str]:
        """Return the list of required arg names for a tool."""
        _, args = _REGISTRY.get(tool_name, (None, []))
        return args

    def tool_call_descriptions(self) -> str:
        """Return a string describing available tools for the agent's system prompt."""
        lines = []
        for name, (fn, req_args) in _REGISTRY.items():
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            lines.append(f"- {name}({', '.join(req_args)}): {doc}")
        return "\n".join(lines)
