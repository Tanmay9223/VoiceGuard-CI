"""
harness/validate.py
Scenario validator CLI.
Loads every YAML in scenarios/, checks schema compliance, and verifies tag index integrity.

Usage:
    python -m harness.validate scenarios/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def validate(scenarios_dir: Path) -> bool:
    """
    Validate all YAML scenarios and rebuild index.json.
    Returns True if all pass, False if any fail.
    """
    from harness.loader import ScenarioLoader

    loader = ScenarioLoader()
    yaml_paths = sorted(scenarios_dir.rglob("*.yaml"))

    if not yaml_paths:
        console.print(f"[yellow]No .yaml files found in {scenarios_dir}[/yellow]")
        return False

    table = Table(title=f"Scenario Validation — {scenarios_dir}", show_lines=True)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("ID", style="white")
    table.add_column("Workflow", style="magenta")
    table.add_column("Tags", style="blue")
    table.add_column("Audio", style="yellow")
    table.add_column("Status", style="bold")

    errors: list[tuple[str, str]] = []

    for path in yaml_paths:
        rel = path.relative_to(scenarios_dir.parent)
        try:
            scenario = loader.load(path)
            audio_flag = "✓ TTS→STT" if scenario.use_audio_pipeline else "text-only"
            table.add_row(
                str(rel),
                scenario.id,
                scenario.workflow.value,
                ", ".join(scenario.tags) or "—",
                audio_flag,
                "[green]✅ PASS[/green]",
            )
        except Exception as exc:
            table.add_row(str(rel), "—", "—", "—", "—", "[red]❌ FAIL[/red]")
            errors.append((str(rel), str(exc)))

    console.print(table)

    if errors:
        console.print(f"\n[bold red]{len(errors)} error(s):[/bold red]")
        for path, msg in errors:
            console.print(f"  [red]{path}[/red]: {msg}")
        return False

    # Rebuild index.json
    console.print("\nBuilding scenarios/index.json ...")
    try:
        index = loader.build_index(scenarios_dir)
        total = len(index["all_ids"])
        tags = sorted(index["by_tag"].keys())
        console.print(f"[green]✅ {total} valid, 0 errors[/green]")
        console.print(f"   Tags indexed: {', '.join(tags)}")
    except Exception as exc:
        console.print(f"[red]Failed to build index: {exc}[/red]")
        return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate VoiceGuard CI scenarios.")
    parser.add_argument("scenarios_dir", type=Path, help="Path to scenarios/ directory")
    args = parser.parse_args()

    ok = validate(args.scenarios_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
