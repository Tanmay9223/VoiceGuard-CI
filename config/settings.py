"""
config/settings.py
Central configuration using pydantic-settings.
All values are loaded from environment variables (or .env file).
"""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"          # agent + judge model
    gemini_judge_model: str = "gemini-2.0-flash"    # can override to use a different judge

    # --- STT ---
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"

    # --- TTS ---
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "Rachel"              # default caller voice

    # --- Database ---
    database_url: str = "sqlite:///data/eval.db"

    # --- Audio pipeline ---
    # Global kill-switch. Even if use_audio_pipeline=true in a scenario YAML,
    # the audio round-trip is skipped when this is False.
    use_audio_pipeline: bool = False

    # --- Mock LLM ---
    # When True, MockLLMProvider is injected — no real Gemini calls are made.
    # Used in GitHub Actions CI to keep runs fast and free.
    mock_llm: bool = False

    # --- Scoring thresholds ---
    # Zero tolerance on compliance and hallucination — any failure blocks.
    compliance_pass_rate: float = 1.0    # all calls must pass compliance checks
    hallucination_cap: float = 0.0       # zero hallucinations allowed
    min_quality_score: float = 3.0       # out of 5
    tool_accuracy_floor: float = 0.90    # 90% of tool calls must be correct

    # --- Regression ---
    # How much quality can drop vs baseline before triggering a WARN.
    regression_tolerance: float = 0.2   # 0.2 point drop on quality_score triggers warn

    # --- Runner ---
    max_turns_per_call: int = 20        # safety limit to prevent infinite loops
    scenario_timeout_seconds: int = 120  # per-scenario timeout


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance. Import this everywhere."""
    return Settings()
