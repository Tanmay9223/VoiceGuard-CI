# Voice Agent CI — Insurance Calls

> CI/CD for real-time insurance voice agents. Every change is benchmarked, red-teamed, and scored before it ships.

---

## One-liner
*"A CI system that benchmarks every model change, red-teams failure modes, and converts production mistakes into new eval cases — automatically."*

---

## Project Phases

| Phase | Name | Focus | Status |
|-------|------|-------|--------|
| [01](./phase-01-setup.md) | Setup & Infrastructure | Repo, env, core interfaces | ✅ Built |
| [02](./phase-02-harness.md) | Conversation Harness | Scenario runner & call simulation | ✅ Built |
| [03](./phase-03-scenarios.md) | Scenario Library | 9 insurance call scripts | ✅ Built |
| [04](./phase-04-scoring.md) | Scoring Engine | Failure taxonomy + hybrid evaluation | ✅ Built |
| [05](./phase-05-hardcases.md) | Hard-Case Mining | Production replay pipeline | 🔜 Planned |
| [06](./phase-06-comparison.md) | Model/Provider Comparison | STT, TTS, LLM benchmarking | 🔜 Planned |
| [07](./phase-07-ci-gate.md) | CI Gate & Dashboard | Release decisions + regression UI | ✅ Built |

---

## Stack
- **Runtime**: Python 3.11+
- **LLM**: Gemini (judge + agent)
- **STT**: Deepgram (nova-2)
- **TTS**: ElevenLabs
- **DB**: SQLite (dev) → Postgres (prod)
- **Dashboard**: Streamlit
- **CI**: GitHub Actions

---

## MVP Scope (4 Phases)

> A tight MVP is more impressive than a sprawling incomplete system.

**Built:**
1. **Phase 01** — Setup (foundation, can't skip)
2. **Phase 02** — Conversation Harness (the core engine)
3. **Phase 04** — Scoring Engine (the differentiator)
4. **Phase 07** — CI Gate + Dashboard (the "wow" moment)

**Planned (Phase 05 & 06):** Provider comparison and hard-case mining are next milestones.

---

## MVP Definition
- [x] 9 call scenarios (happy-path, edge-cases, red-team)
- [x] 7 failure classes with evaluators (4 rule-based + 3 LLM judges)
- [x] Regression delta dashboard (Streamlit)
- [x] CI gate blocks on compliance/hallucination failures
- [x] `--mock-llm` flag for CI (no API costs)
- [ ] Auto-ingestion of production failures *(Phase 05 — planned)*

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy env template and fill in your API keys
cp .env.example .env

# 3. Run DB migrations
alembic upgrade head

# 4. Validate scenarios
python -m harness.validate scenarios/

# 5. Dry-run (use --mock-llm to avoid network calls)
python -m harness.run --dry-run --mock-llm

# 6. Run all scenarios (use --mock-llm for local/free testing)
python -m harness.run --all --mock-llm

# 7. Launch dashboard
streamlit run dashboard/app.py
```