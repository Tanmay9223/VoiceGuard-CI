"""
mining/generator.py
Uses Gemini to automatically author a new YAML regression scenario
from a detected production failure.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from harness.providers import LLMProvider
    from mining.models import FailureEvent

logger = logging.getLogger(__name__)


def generate_scenario(failure: "FailureEvent", llm: "LLMProvider") -> Path | None:
    """
    Generates a regression scenario YAML file from the given failure.
    """
    transcript = failure.call_data.full_transcript()
    
    prompt = f"""\
You are an expert QA automation engineer for an insurance voice agent.
A production call failed with these tags: {failure.failure_tags}

TRANSCRIPT:
{transcript}

Your task is to create a regression scenario to prevent this failure in the future.
Extract the context and provide a JSON response with these exact keys:
1. "workflow": Must be one of ["quote", "renewal", "claims", "lead"]. Guess based on transcript.
2. "caller_persona": A 2-sentence description of the caller's persona and goal (e.g., "A frustrated customer trying to file a claim for a rear-end collision").
3. "opening_line": The exact first thing the caller says.
4. "expected_outcomes": A list of dictionaries representing what the agent SHOULD have done. For example: {{"disclosed": "premium disclaimer"}} or {{"tool_called": "route_to_agent"}}

Respond ONLY with raw JSON, no markdown formatting.
"""

    try:
        raw_json = llm.complete([{"role": "user", "content": prompt}], system="Respond ONLY with valid JSON.")
        # Strip markdown if Gemini ignores instructions
        import re
        raw_json = re.sub(r"```json\s*|\s*```", "", raw_json).strip()
        data = json.loads(raw_json)
    except Exception as exc:
        logger.error("[Generator] Failed to generate scenario from LLM: %s", exc)
        return None

    # Construct YAML structure
    scenario_dict = {
        "id": f"regression-{failure.call_id}",
        "name": f"Regression: {failure.failure_tags[0]}",
        "workflow": data.get("workflow", "quote"),
        "caller_persona": data.get("caller_persona", "A standard caller."),
        "tags": ["regression"] + failure.failure_tags,
        "failure_class": failure.failure_tags[0],
        "turns": [
            {
                "speaker": "caller",
                "text": data.get("opening_line", "Hello.")
            }
        ],
        "expected_outcomes": data.get("expected_outcomes", [])
    }

    out_dir = Path("scenarios/regression/pending")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / f"{scenario_dict['id']}.yaml"
    
    with out_path.open("w") as f:
        yaml.dump(scenario_dict, f, sort_keys=False, default_flow_style=False)
        
    logger.info("[Generator] Created regression scenario: %s", out_path)
    return out_path
