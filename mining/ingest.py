"""
mining/ingest.py
CLI entrypoint to ingest production call logs, detect failures,
deduplicate, and generate regression scenarios.

Usage:
    python -m mining.ingest --input data/production-calls/
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from config.settings import get_settings
from harness.providers import build_llm_provider
from mining.dedup import VectorDB
from mining.detector import detect_failures
from mining.generator import generate_scenario
from mining.models import ProductionCall, ProductionTurn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_file(path: Path, llm, vector_db: VectorDB) -> None:
    logger.info("Ingesting %s", path.name)
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        logger.error("Failed to parse JSON %s: %s", path.name, exc)
        return

    # For MVP, we read the exact JSON format output by harness.run
    # which has {"results": [{"scenario_id": ..., "turns": [...]}]}
    results = data.get("results", [])
    if not results:
        logger.warning("No results array found in %s. Skipping.", path.name)
        return

    for r in results:
        raw_turns = r.get("turns", [])
        if not raw_turns:
            continue
            
        call_id = data.get("run_id", "unknown") + "-" + r.get("scenario_id", "unknown")
        
        # Build proxy model
        turns = [
            ProductionTurn(
                speaker=t.get("speaker", "unknown"),
                text=t.get("text", ""),
                tool_calls=t.get("tool_calls", [])
            )
            for t in raw_turns
        ]
        
        call = ProductionCall(call_id=call_id, turns=turns)
        
        # 1. Detect
        failure = detect_failures(call, llm)
        if not failure:
            continue
            
        # 2. Dedup
        if vector_db.is_duplicate(failure, threshold=0.85):
            logger.info("Skipping %s — duplicate failure detected.", call_id)
            continue
            
        # 3. Generate
        logger.info("Novel failure %s detected. Generating scenario...", call_id)
        generate_scenario(failure, llm)


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceGuard CI Production Ingestion")
    parser.add_argument("--input", required=True, help="Directory containing JSON logs")
    args = parser.parse_args()

    input_dir = Path(args.input)
    if not input_dir.exists() or not input_dir.is_dir():
        logger.error("Input directory %s does not exist.", input_dir)
        return

    settings = get_settings()
    llm = build_llm_provider(settings)
    vector_db = VectorDB(llm)

    for path in input_dir.glob("*.json"):
        ingest_file(path, llm, vector_db)

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    main()
