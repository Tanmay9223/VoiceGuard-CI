"""
comparison/report.py
Generates a ranked terminal report comparing LLM providers.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
import yaml

try:
    # pyrefly: ignore [missing-import]
    from rich.console import Console
    # pyrefly: ignore [missing-import]
    from rich.table import Table
except ImportError:
    Console = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def generate_report() -> None:
    manifest_path = Path("data/results/comparison_latest.json")
    if not manifest_path.exists():
        logger.error("No comparison manifest found. Run `python -m comparison.runner` first.")
        return

    reports = json.loads(manifest_path.read_text())
    
    rows = []
    
    for report_path in reports:
        path = Path(report_path)
        if not path.exists():
            continue
            
        data = json.loads(path.read_text())
        total = data.get("total", 0)
        passed = data.get("passed", 0)
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # Calculate avg hallucination and quality
        qualities = []
        hallucs = []
        total_input_tokens = 0
        total_output_tokens = 0
        
        for r in data.get("results", []):
            scores = r.get("scores", {})
            qualities.append(scores.get("quality", 0))
            hallucs.append(scores.get("halluc", 0))
            
            # Rough token estimate: 1 word = 1.3 tokens
            turns = r.get("turns", [])
            for turn in turns:
                if turn.get("speaker") == "agent":
                    total_output_tokens += len(turn.get("text", "").split()) * 1.3
                else:
                    total_input_tokens += len(turn.get("text", "").split()) * 1.3
        
        avg_qual = sum(qualities) / len(qualities) if qualities else 0
        avg_halluc = sum(hallucs) / len(hallucs) if hallucs else 0
        
        cost_input = data.get("cost_input", 0)
        cost_output = data.get("cost_output", 0)
        
        # Estimated cost per call
        total_cost = (total_input_tokens / 1000 * cost_input) + (total_output_tokens / 1000 * cost_output)
        avg_cost_per_call = (total_cost / total) if total > 0 else 0
        
        rows.append({
            "provider_id": data.get("provider_id", "unknown"),
            "pass_rate": pass_rate,
            "avg_qual": avg_qual,
            "avg_halluc": avg_halluc,
            "latency": data.get("p95_latency", 0),
            "cost_per_call": avg_cost_per_call
        })
        
    if not rows:
        logger.error("No valid reports found.")
        return
        
    # Sort by pass rate (desc), then quality (desc), then cost (asc)
    rows.sort(key=lambda r: (r["pass_rate"], r["avg_qual"], -r["cost_per_call"]), reverse=True)
    
    # Save the winner
    winner = rows[0]
    out_path = Path("config/current-stack.yaml")
    out_path.write_text(yaml.dump({"llm_provider": winner["provider_id"]}))
    
    if Console:
        console = Console()
        table = Table(title="Provider Comparison Results")
        table.add_column("Rank", justify="right", style="cyan", no_wrap=True)
        table.add_column("Stack (LLM)", style="magenta")
        table.add_column("Pass Rate", justify="right", style="green")
        table.add_column("Quality", justify="right")
        table.add_column("Hallucination", justify="right")
        table.add_column("Latency (p95)", justify="right")
        table.add_column("Est. Cost / Call", justify="right")
        
        for idx, r in enumerate(rows):
            rank = str(idx + 1)
            if idx == 0:
                rank += " 🏆"
            table.add_row(
                rank,
                r["provider_id"],
                f"{r['pass_rate']:.1f}%",
                f"{r['avg_qual']:.1f}/5.0",
                f"{r['avg_halluc']*100:.1f}%",
                f"{r['latency']:.2f}s",
                f"${r['cost_per_call']:.4f}",
            )
            
        console.print(table)
        console.print(f"\n✅ Recommended stack [bold green]{winner['provider_id']}[/bold green] pinned to config/current-stack.yaml")
    else:
        logger.info("=== Provider Comparison Results ===")
        for idx, r in enumerate(rows):
            logger.info(
                "#%d %s: Pass: %.1f%%, Qual: %.1f, Cost: $%.4f",
                idx + 1, r["provider_id"], r["pass_rate"], r["avg_qual"], r["cost_per_call"]
            )
        logger.info("Pinned %s to config/current-stack.yaml", winner["provider_id"])


if __name__ == "__main__":
    generate_report()
