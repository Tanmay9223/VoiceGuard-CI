"""
mining/dedup.py
Lightweight in-memory Vector DB for deduplication.
Uses Gemini's text-embedding-004 and pure Python cosine similarity.
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.providers import LLMProvider
    from mining.models import FailureEvent

logger = logging.getLogger(__name__)

DB_PATH = Path("data/baselines/vector_db.json")


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


class VectorDB:
    def __init__(self, llm: "LLMProvider") -> None:
        self._llm = llm
        self._cache: dict[str, list[float]] = {}
        if DB_PATH.exists():
            try:
                self._cache = json.loads(DB_PATH.read_text())
            except Exception as exc:
                logger.warning("Failed to load vector DB: %s", exc)

    def _save(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DB_PATH.write_text(json.dumps(self._cache))

    def _embed(self, text: str) -> list[float]:
        # Using the new google-genai SDK embedding method
        response = self._llm._client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        # return the first embedding vector
        return response.embeddings[0].values

    def is_duplicate(self, failure: "FailureEvent", threshold: float = 0.85) -> bool:
        """
        Embeds the transcript and checks against known scenarios.
        If similarity > threshold, returns True. Otherwise saves the new embedding and returns False.
        """
        text_to_embed = failure.call_data.full_transcript()
        
        try:
            vector = self._embed(text_to_embed)
        except Exception as exc:
            logger.error("Failed to generate embedding, assuming not duplicate: %s", exc)
            return False

        max_sim = 0.0
        best_match = None

        for existing_id, existing_vec in self._cache.items():
            sim = _cosine_similarity(vector, existing_vec)
            if sim > max_sim:
                max_sim = sim
                best_match = existing_id

        logger.info("[Dedup] Max similarity: %.2f (vs %s)", max_sim, best_match or "none")

        if max_sim >= threshold:
            return True

        # It's novel! Save it so future checks catch it.
        self._cache[failure.call_id] = vector
        self._save()
        return False
