"""
harness/simulator.py
CallerSimulator — Gemini playing the caller role.
Receives a persona + scenario context, responds naturally to agent turns,
and can inject interruptions for red-team scenarios.
"""
from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

from harness.models import CallScenario, Turn

if TYPE_CHECKING:
    from harness.providers import LLMProvider

logger = logging.getLogger(__name__)

_SIMULATOR_SYSTEM = """\
You are simulating a caller to an insurance company.

PERSONA: {persona}

SCENARIO GOAL: {goal}

BEHAVIOR RULES:
- Stay in character as the caller — do NOT break the fourth wall.
- Respond naturally and conversationally. Keep responses short (1-3 sentences).
- You are on a phone call, so respond as you would speak, not write.
- If the scenario includes frustration or confusion, express it naturally.
- Do NOT volunteer information the agent hasn't asked for yet.
- When the agent asks for information, provide it naturally.

IMPORTANT: Respond ONLY as the caller. Do not include agent dialogue.
"""

# Interruption phrases injected for red-team / edge-case scenarios
_INTERRUPTIONS = [
    "Wait, wait — sorry to interrupt, but —",
    "Actually, hold on —",
    "Sorry, I didn't catch that. Can you repeat?",
    "One second, my kid is yelling — okay, sorry, go ahead.",
    "Wait, you said what? The premium is HOW much?",
]


class CallerSimulator:
    """
    Simulates a caller using an LLM playing a persona.
    Used by CallRunner to generate caller utterances turn-by-turn.
    """

    def __init__(
        self,
        llm: "LLMProvider",
        scenario: CallScenario,
        inject_interruptions: bool = False,
        interrupt_probability: float = 0.2,
    ) -> None:
        self._llm = llm
        self._scenario = scenario
        self._inject_interruptions = inject_interruptions
        self._interrupt_probability = interrupt_probability
        self._history: list[dict[str, str]] = []
        self._scripted_turns = [
            turn.text for turn in scenario.turns 
            if turn.speaker == "caller" and turn.text
        ]
        self._turn_index = 0

        # Build a goal string from expected_outcomes for the simulator's context
        goal_parts = []
        for outcome in scenario.expected_outcomes:
            if "tool_called" in outcome:
                goal_msg = f"get the agent to call {outcome['tool_called']}"
                if "args" in outcome:
                    goal_msg += f" using these exact details: {outcome['args']}"
                goal_parts.append(goal_msg)
            if "disclosed" in outcome:
                goal_parts.append(f"receive disclosure: {outcome['disclosed']}")
        self._goal = "; ".join(goal_parts) if goal_parts else "complete your insurance inquiry"

        self._system = _SIMULATOR_SYSTEM.format(
            persona=scenario.caller_persona,
            goal=self._goal,
        )

    def opening_line(self) -> str:
        """Return the first caller utterance (seeded from scenario or generated)."""
        if self._turn_index < len(self._scripted_turns):
            text = self._scripted_turns[self._turn_index]
            self._turn_index += 1
            self._history.append({"role": "assistant", "content": text})
            return text

        # Otherwise generate one
        prompt = [{"role": "user", "content": "Start the call. Say your opening line."}]
        response = self._llm.complete(prompt, system=self._system)
        self._history.append({"role": "assistant", "content": response})
        return response

    def respond(self, agent_utterance: str) -> str:
        """Generate the caller's next utterance in response to the agent."""
        self._history.append({"role": "user", "content": f"[AGENT]: {agent_utterance}"})

        if self._turn_index < len(self._scripted_turns):
            response = self._scripted_turns[self._turn_index]
            self._turn_index += 1
        else:
            response = self._llm.complete(self._history, system=self._system)

        self._history.append({"role": "assistant", "content": response})

        # Optionally inject an interruption prefix
        if self._inject_interruptions and random.random() < self._interrupt_probability:
            interruption = random.choice(_INTERRUPTIONS)
            response = f"{interruption} {response}"
            logger.debug("[Simulator] Injected interruption: %r", interruption)

        return response.strip()

    def inject_interruption(self) -> str:
        """Return a random interruption phrase (used explicitly in red-team turns)."""
        return random.choice(_INTERRUPTIONS)

    def reset(self) -> None:
        self._history.clear()
        self._turn_index = 0
