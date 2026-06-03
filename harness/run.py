"""
harness/run.py
Main entrypoint for the harness.

Usage:
    python -m harness.run --dry-run
    python -m harness.run --all
    python -m harness.run --tags ci-gate
    python -m harness.run --tags compliance --mock-llm
    python -m harness.run --scenario scenarios/happy-path/auto-quote-basic.yaml
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VoiceGuard CI — harness runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true",
                       help="Validate config and providers without running any scenarios.")
    group.add_argument("--all", action="store_true",
                       help="Run all scenarios in the scenarios/ directory.")
    group.add_argument("--tags", nargs="+", metavar="TAG",
                       help="Run scenarios matching any of the given tags.")
    group.add_argument("--scenario", metavar="PATH",
                       help="Run a single scenario YAML file.")
    parser.add_argument("--mock-llm", action="store_true",
                        help="Override MOCK_LLM=true for this run (no Gemini API calls).")
    parser.add_argument("--output-dir", default="data/results",
                        help="Directory to write run result JSON files.")
    return parser.parse_args()


def _dry_run() -> None:
    """Validate that all providers and config load correctly."""
    from config.settings import get_settings
    from harness.providers import build_llm_provider

    logger.info("=== DRY RUN ===")
    settings = get_settings()
    logger.info("Settings loaded OK")
    logger.info("  gemini_model       = %s", settings.gemini_model)
    logger.info("  database_url       = %s", settings.database_url)
    logger.info("  use_audio_pipeline = %s", settings.use_audio_pipeline)
    logger.info("  mock_llm           = %s", settings.mock_llm)
    logger.info("  compliance_pass_rate  = %.2f", settings.compliance_pass_rate)
    logger.info("  hallucination_cap     = %.2f", settings.hallucination_cap)
    logger.info("  min_quality_score     = %.2f", settings.min_quality_score)
    logger.info("  tool_accuracy_floor   = %.2f", settings.tool_accuracy_floor)

    llm = build_llm_provider(settings)
    logger.info("LLM provider loaded: %s", type(llm).__name__)

    # Quick smoke-test — if mock, this should never fail
    test_resp = llm.complete(
        [{"role": "user", "content": "hello"}],
        system="You are a test agent.",
    )
    logger.info("LLM smoke-test response: %r", test_resp[:80])
    logger.info("=== DRY RUN PASSED ===")


def _run_scenarios(scenario_paths: list[Path], output_dir: Path) -> list[dict]:
    """Run a list of scenario files and return serialised results."""
    from harness.loader import ScenarioLoader
    from harness.runner import CallRunner
    from config.settings import get_settings
    from harness.providers import build_llm_provider, build_stt_provider, build_tts_provider

    settings = get_settings()
    llm = build_llm_provider(settings)
    stt = build_stt_provider(settings) if settings.use_audio_pipeline else None
    tts = build_tts_provider(settings) if settings.use_audio_pipeline else None

    loader = ScenarioLoader()
    runner = CallRunner(llm=llm, stt=stt, tts=tts, settings=settings)

    run_id = str(uuid.uuid4())[:8]
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    from scoring.aggregator import aggregate

    for path in scenario_paths:
        scenario = loader.load(path)
        logger.info("Running scenario: %s", scenario.id)
        result = runner.run(scenario, run_id=run_id)
        
        # Run scoring engine
        aggregate(result, scenario, llm, settings)
        
        results.append(result)
        logger.info(
            "  %s — pass=%s  tags=%s",
            scenario.id,
            result.passed,
            result.failure_tags or "none",
        )

    # Write run summary
    summary = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [
            {
                "scenario_id": r.scenario_id,
                "passed": r.passed,
                "failure_tags": r.failure_tags,
                "error": r.error,
                "scores": getattr(r, "scores", {}),
                "turns": [
                    {
                        "speaker": t.speaker,
                        "text": t.text,
                        "tool_calls": [{"name": tc.name, "args": tc.args} for tc in t.tool_calls]
                    }
                    for t in r.turns
                ],
            }
            for r in results
        ],
    }
    out_path = output_dir / f"run-{run_id}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    logger.info("Results written to %s", out_path)
    return results


def main() -> None:
    args = _parse_args()

    # Allow --mock-llm flag to override the env var
    if args.mock_llm:
        import os
        os.environ["MOCK_LLM"] = "true"
        # Bust the settings cache so the new env var is picked up
        from config.settings import get_settings
        get_settings.cache_clear()

    if args.dry_run:
        _dry_run()
        return

    from harness.loader import ScenarioLoader
    scenarios_root = Path("scenarios")

    if args.all:
        paths = sorted(scenarios_root.rglob("*.yaml"))
    elif args.tags:
        loader = ScenarioLoader()
        index = loader.load_index(scenarios_root / "index.json")
        matched_ids: set[str] = set()
        for tag in args.tags:
            matched_ids.update(index.get("by_tag", {}).get(tag, []))
        paths = [
            p for p in scenarios_root.rglob("*.yaml")
            if ScenarioLoader.scenario_id_from_path(p) in matched_ids
        ]
        if not paths:
            logger.warning("No scenarios matched tags: %s", args.tags)
            sys.exit(0)
    elif args.scenario:
        paths = [Path(args.scenario)]
    else:
        logger.error("Specify --dry-run, --all, --tags, or --scenario")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    results = _run_scenarios(paths, output_dir)

    failed = [r for r in results if not r.passed]
    if failed:
        logger.warning("%d scenario(s) failed.", len(failed))
        sys.exit(1)
    else:
        logger.info("All %d scenarios passed.", len(results))


if __name__ == "__main__":
    main()
