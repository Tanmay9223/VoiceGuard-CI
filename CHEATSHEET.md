# Quick Reference — Antigravity Cheat Sheet

## Key Commands

```bash
# Validate all scenarios (checks schema + tag index)
python -m harness.validate scenarios/

# Run full eval suite
python -m harness.run --all

# Run by tag
python -m harness.run --tags compliance
python -m harness.run --tags red-team
python -m harness.run --tags ci-gate

# Run with mock LLM (no API calls, for CI / offline testing)
python -m harness.run --all --mock-llm

# Score a specific result
python -m scoring.run --result results/run-abc123.json

# Run model comparison
python -m comparison.runner --config config/providers.yaml --tags happy-path

# Check CI gate decision
python -m ci.gate --run-id <id> --fail-on block

# Ingest production failures
python -m mining.ingest --input data/production-calls/

# Review pending regression scenarios
python -m mining.review

# Launch dashboard
streamlit run dashboard/app.py
```

---

## File Locations

| What | Where |
|------|-------|
| Scenarios | `scenarios/{happy-path,edge-cases,red-team,regression}/` |
| Run results | `data/results/run-{id}.json` |
| Baselines | `data/baselines/{sha}.json` |
| Pending scenarios | `scenarios/regression/pending/` |
| Suggestions | `data/suggestions/` |
| Current stack | `config/current-stack.yaml` |

---

## Failure Classes Reference

| Tag | Tolerance |
|-----|-----------|
| `missed_disclosure` | 0 — always blocks |
| `compliance_violation` | 0 — always blocks |
| `hallucinated_quote` | 0 — always blocks |
| `wrong_routing` | < 5% warns |
| `bad_interruption` | < 10% warns |
| `asr_recovery_fail` | < 15% warns |
| `tool_misuse` | < 10% warns |

---

## Environment Variables

```bash
# Required for real runs and demos
GEMINI_API_KEY=
DEEPGRAM_API_KEY=
ELEVENLABS_API_KEY=

# Database
DATABASE_URL=sqlite:///data/eval.db

# Audio: set true to enable TTS→STT round-trip on asr-noise-injection scenario
USE_AUDIO_PIPELINE=false

# Mock LLM: set true in CI to skip API calls (uses fixture responses)
MOCK_LLM=false
```

> Copy `.env.example` to `.env` and fill in your keys before running locally.
