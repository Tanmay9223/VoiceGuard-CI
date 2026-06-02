"""
ci/gate.py
Release decision logic.
Determines ship / warn / block based on eval scores vs baseline.

Usage:
    python -m ci.gate --run-id <id> --fail-on block
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from ci.baseline import load_baseline, regression_delta
from harness.models import ReleaseDecision

logger = logging.getLogger(__name__)
console = Console()


def decide(run_summary: dict, settings) -> tuple[ReleaseDecision, str]:
    """
    Apply thresholds to produce a release decision.
    Returns (decision, reason).
    """
    results = run_summary.get("results", [])

    # --- Compliance check: zero tolerance ---
    compliance_failures = [
        r for r in results
        if any(tag in r.get("failure_tags", [])
               for tag in ("missed_disclosure", "compliance_violation"))
    ]
    if compliance_failures:
        scenarios = [r["scenario_id"] for r in compliance_failures]
        return (
            ReleaseDecision.BLOCK,
            f"Compliance violation in {len(compliance_failures)} scenario(s): {scenarios}",
        )

    # --- Hallucination check: zero tolerance ---
    hallucination_failures = [
        r for r in results
        if "hallucinated_quote" in r.get("failure_tags", [])
    ]
    if hallucination_failures:
        scenarios = [r["scenario_id"] for r in hallucination_failures]
        return (
            ReleaseDecision.BLOCK,
            f"Hallucination detected in {len(hallucination_failures)} scenario(s): {scenarios}",
        )

    # --- Regression check vs baseline ---
    baseline = load_baseline()
    if baseline:
        # Compute aggregate scores from this run
        current = _aggregate_run_scores(run_summary)
        deltas = regression_delta(current, baseline)
        regressions = {k: v for k, v in deltas.items() if v < -settings.regression_tolerance}
        if regressions:
            return (
                ReleaseDecision.WARN,
                f"Quality regression vs baseline: {regressions}",
            )

    return ReleaseDecision.SHIP, "All checks passed."


def _aggregate_run_scores(run_summary: dict) -> dict:
    """Compute mean scores across all results in a run summary."""
    results = run_summary.get("results", [])
    if not results:
        return {}
    metric_keys = ["compliance_score", "hallucination_score", "quality_score", "tool_accuracy"]
    aggregated = {}
    for key in metric_keys:
        vals = [float(r.get("scores", {}).get(key, 0)) for r in results if "scores" in r]
        aggregated[key] = sum(vals) / len(vals) if vals else 0.0
    return aggregated


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceGuard CI gate decision.")
    parser.add_argument("--run-id", required=True, help="The run ID to evaluate.")
    parser.add_argument("--fail-on", choices=["block", "warn", "any"], default="block",
                        help="Exit code 1 when decision is at or worse than this level.")
    parser.add_argument("--results-dir", default="data/results",
                        help="Directory containing run-{id}.json files.")
    args = parser.parse_args()

    result_path = Path(args.results_dir) / f"run-{args.run_id}.json"
    if not result_path.exists():
        console.print(f"[red]Run result not found: {result_path}[/red]")
        sys.exit(1)

    from config.settings import get_settings
    settings = get_settings()
    run_summary = json.loads(result_path.read_text())

    decision, reason = decide(run_summary, settings)

    # Display
    color = {"ship": "green", "ship_with_warnings": "yellow", "block_merge": "red"}[decision.value]
    console.print(Panel(
        f"[bold {color}]{decision.value.upper()}[/bold {color}]\n{reason}",
        title="CI Gate Decision",
        border_style=color,
    ))

    # Exit code logic
    should_fail = (
        (args.fail_on == "block" and decision == ReleaseDecision.BLOCK) or
        (args.fail_on == "warn" and decision in (ReleaseDecision.BLOCK, ReleaseDecision.WARN)) or
        (args.fail_on == "any" and decision != ReleaseDecision.SHIP)
    )
    sys.exit(1 if should_fail else 0)


if __name__ == "__main__":
    main()
