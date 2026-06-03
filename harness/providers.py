"""
harness/providers.py
Protocol interfaces and concrete adapters for LLM, STT, and TTS providers.
Also contains MockLLMProvider for CI / offline testing.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol interfaces
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, messages: list[dict[str, str]], system: str = "") -> str:
        """Send a chat-style message list and return the model's text response."""
        ...


@runtime_checkable
class STTProvider(Protocol):
    def transcribe(self, audio: bytes) -> str:
        """Convert audio bytes to a text transcript."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    def synthesize(self, text: str) -> bytes:
        """Convert text to audio bytes (WAV or MP3)."""
        ...


# ---------------------------------------------------------------------------
# Gemini LLM adapter
# ---------------------------------------------------------------------------

class GeminiLLMProvider:
    """Real Gemini adapter using google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite") -> None:
        try:
            # pyrefly: ignore [missing-import]
            from google import genai
            # pyrefly: ignore [missing-import]
            from google.genai import types
            self._client = genai.Client(api_key=api_key)
            self._types = types
        except ImportError:
            raise ImportError("Install google-genai: pip install google-genai")
        self._model_name = model

    def complete(self, messages: list[dict[str, str]], system: str = "") -> str:
        # Build a conversation history for the Gemini SDK
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append(
                self._types.Content(role=role, parts=[self._types.Part.from_text(text=msg["content"])])
            )

        config = self._types.GenerateContentConfig()
        if system:
            config.system_instruction = system

        chat = self._client.chats.create(model=self._model_name, config=config, history=history)
        last = messages[-1]["content"]
        
        import time
        for attempt in range(6):
            try:
                response = chat.send_message(last)
                return response.text.strip()
            except Exception as e:
                if "429" in str(e) and attempt < 5:
                    delay = (attempt + 1) * 6  # 6s, 12s, 18s...
                    import logging
                    logging.getLogger(__name__).warning(f"Rate limited (429). Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                raise e


# ---------------------------------------------------------------------------
# Deepgram STT adapter
# ---------------------------------------------------------------------------

class DeepgramSTTProvider:
    """STT adapter using Deepgram nova-2."""

    def __init__(self, api_key: str, model: str = "nova-2") -> None:
        try:
            # pyrefly: ignore [missing-import]
            from deepgram import DeepgramClient, PrerecordedOptions
            self._client = DeepgramClient(api_key)
            self._options = PrerecordedOptions(model=model, smart_format=True)
        except ImportError:
            raise ImportError("Install deepgram-sdk: pip install deepgram-sdk")

    def transcribe(self, audio: bytes) -> str:
        # pyrefly: ignore [missing-import]
        from deepgram import FileSource
        source: FileSource = {"buffer": audio}
        response = self._client.listen.prerecorded.v("1").transcribe_file(
            source, self._options
        )
        return response.results.channels[0].alternatives[0].transcript


# ---------------------------------------------------------------------------
# ElevenLabs TTS adapter
# ---------------------------------------------------------------------------

class ElevenLabsTTSProvider:
    """TTS adapter using ElevenLabs."""

    def __init__(self, api_key: str, voice_id: str = "Rachel") -> None:
        try:
            # pyrefly: ignore [missing-import]
            from elevenlabs.client import ElevenLabs
            self._client = ElevenLabs(api_key=api_key)
            self._voice_id = voice_id
        except ImportError:
            raise ImportError("Install elevenlabs: pip install elevenlabs")

    def synthesize(self, text: str) -> bytes:
        audio_generator = self._client.generate(
            text=text,
            voice=self._voice_id,
            model="eleven_monolingual_v1",
        )
        return b"".join(audio_generator)


# ---------------------------------------------------------------------------
# MockLLMProvider — for CI / offline testing
# ---------------------------------------------------------------------------

# Pre-recorded fixture responses keyed by the first word of the last user message.
# The runner uses this when MOCK_LLM=true so no real Gemini calls are made.
_FIXTURE_RESPONSES: dict[str, str] = {
    # Agent responses (insurance persona)
    "hi": "Hello! Thank you for calling InsureCo. My name is Alex. How can I help you today?",
    "hello": "Hello! Thank you for calling InsureCo. My name is Alex. How can I help you today?",
    "quote": "I'd be happy to help you get a quote. Could you please provide your vehicle's make, model, year, and ZIP code?",
    "renew": "I can help you with your renewal. Could you please provide your policy number?",
    "claim": "I'm sorry to hear you need to file a claim. I'll help you through the process. Could you describe what happened?",
    # Hallucination judge
    "you": json.dumps({"hallucinations": [], "confidence": 0.95}),
    # Quality judge
    "score": json.dumps({"score": 4.2, "issues": [], "reasoning": "Agent was clear and empathetic."}),
    # Interruption judge
    "did": json.dumps({"handled_well": True, "examples": []}),
    # Default fallback
    "_default": (
        "I understand. Let me assist you with that. "
        "Before we proceed, I need to let you know that this call may be recorded for quality assurance. "
        "Do you agree to continue?"
    ),
}


class MockLLMProvider:
    """
    Fixture-backed LLM provider for CI and offline testing.
    Returns pre-recorded responses — no Gemini API calls are made.
    Activated via MOCK_LLM=true env var or --mock-llm CLI flag.
    """

    def complete(self, messages: list[dict[str, str]], system: str = "") -> str:
        if not messages:
            return _FIXTURE_RESPONSES["_default"]
        last_content = messages[-1].get("content", "").strip()
        first_word = last_content.split()[0].lower() if last_content else "_default"
        response = _FIXTURE_RESPONSES.get(first_word, _FIXTURE_RESPONSES["_default"])
        logger.debug("[MockLLM] Returning fixture for key=%r", first_word)
        return response


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def build_llm_provider(settings: Any) -> LLMProvider:
    """Return the correct LLM provider based on settings."""
    if settings.mock_llm:
        logger.info("MockLLMProvider active — no Gemini API calls will be made.")
        return MockLLMProvider()
    return GeminiLLMProvider(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )


def build_stt_provider(settings: Any) -> STTProvider:
    return DeepgramSTTProvider(
        api_key=settings.deepgram_api_key,
        model=settings.deepgram_model,
    )


def build_tts_provider(settings: Any) -> TTSProvider:
    return ElevenLabsTTSProvider(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
    )
