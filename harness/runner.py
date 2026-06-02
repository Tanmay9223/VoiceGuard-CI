"""
harness/runner.py
CallRunner — orchestrates a full VoiceAgent ↔ CallerSimulator conversation.
Captures text, optional audio bytes (TTS→STT), tool calls, and timestamps per turn.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from harness.agent import VoiceAgent
from harness.models import CallResult, CallScenario, ToolCall, TurnResult
from harness.simulator import CallerSimulator
from harness.tools import ToolRegistry

if TYPE_CHECKING:
    from config.settings import Settings
    from harness.providers import LLMProvider, STTProvider, TTSProvider

logger = logging.getLogger(__name__)


class CallRunner:
    """
    Drives a full insurance call between VoiceAgent and CallerSimulator.
    Supports text-only mode (default) and TTS→STT round-trip for flagged scenarios.
    """

    def __init__(
        self,
        llm: "LLMProvider",
        settings: "Settings",
        stt: "STTProvider | None" = None,
        tts: "TTSProvider | None" = None,
    ) -> None:
        self._llm = llm
        self._settings = settings
        self._stt = stt
        self._tts = tts

    def run(self, scenario: CallScenario, run_id: str | None = None) -> CallResult:
        """
        Execute a full scenario and return a CallResult.

        For scenarios with use_audio_pipeline=True AND USE_AUDIO_PIPELINE env=True,
        the caller text is passed through TTS→STT before reaching the agent.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())[:8]

        tool_registry = ToolRegistry()
        agent = VoiceAgent(llm=self._llm, tools=tool_registry, settings=self._settings)

        # Determine if interruption injection should be active
        inject_interruptions = any(
            tag in ("red-team", "edge-case", "interruption") for tag in scenario.tags
        )
        simulator = CallerSimulator(
            llm=self._llm,
            scenario=scenario,
            inject_interruptions=inject_interruptions,
        )

        use_audio = (
            scenario.use_audio_pipeline
            and self._settings.use_audio_pipeline
            and self._tts is not None
            and self._stt is not None
        )
        if scenario.use_audio_pipeline and not use_audio:
            logger.info(
                "Scenario %s requests audio pipeline but USE_AUDIO_PIPELINE=false. "
                "Running in text-only mode.",
                scenario.id,
            )

        turn_results: list[TurnResult] = []
        error: str | None = None

        try:
            # --- Turn 0: Caller opens the call ---
            opening = simulator.opening_line()
            t0 = self._run_caller_turn(opening, use_audio)
            turn_results.append(t0)

            caller_text = t0.text  # may be ASR transcript if audio pipeline ran

            # --- Alternating turns: agent → caller → agent → ... ---
            for turn_num in range(self._settings.max_turns_per_call):
                # Agent responds to caller
                t_start = time.time()
                agent_text, agent_tool_calls = agent.respond(caller_text)
                agent_latency = (time.time() - t_start) * 1000

                agent_turn = TurnResult(
                    speaker="agent",
                    text=agent_text,
                    tool_calls=agent_tool_calls,
                    latency_ms=agent_latency,
                )
                turn_results.append(agent_turn)
                logger.debug("[Turn %d][Agent]: %s", turn_num, agent_text[:80])

                # Check if agent routed to human — end call
                if any(tc.name == "route_to_agent" for tc in agent_tool_calls):
                    logger.info("Call ended: agent routed to human.")
                    break

                # Caller responds
                caller_raw = simulator.respond(agent_text)
                t_caller = self._run_caller_turn(caller_raw, use_audio)
                turn_results.append(t_caller)
                caller_text = t_caller.text
                logger.debug("[Turn %d][Caller]: %s", turn_num, caller_text[:80])

                # Simple end-of-call heuristic
                if any(phrase in caller_text.lower() for phrase in
                       ("thank you, goodbye", "thanks, bye", "okay, bye", "that's all")):
                    logger.info("Call ended: caller signed off.")
                    break

        except Exception as exc:
            error = str(exc)
            logger.exception("Scenario %s raised an exception: %s", scenario.id, exc)

        return CallResult(
            scenario_id=scenario.id,
            run_id=run_id,
            turns=turn_results,
            failure_tags=[],
            passed=False,   # scoring phase sets this
            error=error,
            timestamp=datetime.utcnow(),
        )

    def _run_caller_turn(self, text: str, use_audio: bool) -> TurnResult:
        """
        Process a caller turn.
        If use_audio=True: text → TTS (bytes) → STT → transcript.
        If use_audio=False: pass text directly.
        """
        audio_bytes: bytes | None = None
        transcript = text

        if use_audio and self._tts and self._stt:
            t_start = time.time()
            audio_bytes = self._tts.synthesize(text)
            transcript = self._stt.transcribe(audio_bytes)
            latency = (time.time() - t_start) * 1000
            logger.info(
                "[Audio pipeline] TTS→STT in %.0fms | Original: %r | Transcript: %r",
                latency, text[:60], transcript[:60],
            )
        else:
            latency = 0.0

        return TurnResult(
            speaker="caller",
            text=transcript,
            audio_bytes=audio_bytes,
            latency_ms=latency,
        )
