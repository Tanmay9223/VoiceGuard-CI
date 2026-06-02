"""
ci/baseline.py
Baseline management — store and load EvalScore baselines per commit SHA.
Falls back to data/baselines/seed.json when no real baseline exists yet.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_BASELINES_DIR = Path("data/baselines")
_SEED_PATH = _BASELINES_DIR / "seed.json"


def _current_commit_sha() -> str:
    """Return current git SHA or 'unknown'."""
    sha = os.environ.get("GITHUB_SHA", "")
    if not sha:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, check=True,
            )
            sha = result.stdout.strip()
        except Exception:
            sha = "unknown"
    return sha


def load_baseline() -> dict:
    """
    Load the most recent baseline.
    Priority: most recent commit-sha baseline → seed.json fallback.
    """
    _BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    # Find all commit-sha baselines (exclude seed.json)
    baselines = sorted(
        [p for p in _BASELINES_DIR.glob("*.json") if p.name != "seed.json"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if baselines:
        path = baselines[0]
        logger.info("Loading baseline: %s", path)
        return json.loads(path.read_text())

    # Fall back to seed
    if _SEED_PATH.exists():
        logger.info("No commit baseline found. Using seed baseline.")
        return json.loads(_SEED_PATH.read_text())

    logger.warning("No baseline found at all. Returning empty baseline.")
    return {}


def save_baseline(scores: dict, commit_sha: str | None = None) -> Path:
    """
    Save the current run's aggregate scores as the new baseline.
    Called on merge to main.
    """
    _BASELINES_DIR.mkdir(parents=True, exist_ok=True)
    sha = commit_sha or _current_commit_sha()
    path = _BASELINES_DIR / f"{sha}.json"
    path.write_text(json.dumps(scores, indent=2))
    logger.info("Saved new baseline: %s", path)
    return path


def regression_delta(current: dict, baseline: dict) -> dict[str, float]:
    """
    Compute per-metric delta: current - baseline.
    Positive = improvement, negative = regression.
    """
    metrics = ["compliance_score", "hallucination_score", "quality_score", "tool_accuracy"]
    return {
        m: round(float(current.get(m, 0)) - float(baseline.get(m, 0)), 4)
        for m in metrics
    }
