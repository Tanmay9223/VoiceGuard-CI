"""
scoring/run.py
CLI entrypoint for scoring a single run result.

Usage:
    python -m scoring.run --result data/results/run-abc123.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a VoiceGuard CI run result.")
    parser.add_argument("--result", required=True, type=Path,
                        help="Path to a run-{id}.json result file.")
    parser.add_argument("--mock-llm", action="store_true",
                        help="Use MockLLMProvider for judge calls.")
    args = parser.parse_args()

    if not args.result.exists():
        console.print(f"[red]Result file not found: {args.result}[/red]")
        sys.exit(1)

    if args.mock_llm:
        import os
        os.environ["MOCK_LLM"] = "true"
        from config.settings import get_settings
        get_settings.cache_clear()

    from config.settings import get_settings
    from harness.providers import build_llm_provider

    settings = get_settings()
    llm = build_llm_provider(settings)

    raw = json.loads(args.result.read_text())
    console.print(f"\n[bold]Run ID:[/bold] {raw.get('run_id', 'unknown')}")
    console.print(f"[bold]Timestamp:[/bold] {raw.get('timestamp', 'unknown')}")
    console.print(f"[bold]Total:[/bold] {raw.get('total', 0)} scenarios\n")

    table = Table(title="Scenario Results", show_lines=True)
    table.add_column("Scenario", style="cyan")
    table.add_column("Passed", style="bold")
    table.add_column("Failure Tags", style="red")
    table.add_column("Error", style="yellow")

    all_passed = True
    for r in raw.get("results", []):
        passed = r.get("passed", False)
        if not passed:
            all_passed = False
        table.add_row(
            r.get("scenario_id", "—"),
            "[green]✅[/green]" if passed else "[red]❌[/red]",
            ", ".join(r.get("failure_tags", [])) or "—",
            r.get("error") or "—",
        )

    console.print(table)

    overall = "[green]PASSED[/green]" if all_passed else "[red]FAILED[/red]"
    console.print(f"\nOverall: {overall}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
