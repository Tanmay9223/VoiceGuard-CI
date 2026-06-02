# Phase 01 — Setup & Infrastructure

**Goal**: Scaffold the repo, define core data models, and wire up config.

---

## Tasks

### 1.1 Repo Structure
```
voice-agent-ci/
├── harness/          # call simulation engine
├── scenarios/        # YAML call scripts
├── scoring/          # evaluators & judges
├── mining/           # production replay
├── comparison/       # model benchmarking
├── dashboard/        # UI
├── ci/               # GitHub Actions
├── data/             # db + fixtures
└── config/           # env + provider configs
```

### 1.2 Core Data Models
Create `harness/models.py`:

```python
@dataclass
class CallScenario:
    id: str
    name: str
    workflow: str        # quote | renewal | claims | lead
    turns: list[Turn]
    expected_outcomes: list[str]
    tags: list[str]

@dataclass
class CallResult:
    scenario_id: str
    run_id: str
    turns: list[TurnResult]
    scores: dict[str, float]
    failure_tags: list[str]
    passed: bool
    timestamp: datetime

@dataclass
class EvalRun:
    run_id: str
    trigger: str         # push | scheduled | manual
    commit_sha: str
    results: list[CallResult]
    release_decision: str   # ship | warn | block
```

### 1.3 Config
Create `config/settings.py` using `pydantic-settings`:
- LLM provider + model
- STT provider + model
- TTS provider + voice
- Thresholds: `compliance_pass_rate`, `hallucination_cap`
- Database URL

### 1.4 Provider Abstractions
Create `harness/providers.py` with interfaces:
```python
class STTProvider(Protocol):
    def transcribe(self, audio: bytes) -> str: ...

class TTSProvider(Protocol):
    def synthesize(self, text: str) -> bytes: ...

class LLMProvider(Protocol):
    def complete(self, messages: list, system: str) -> str: ...
```
Implement one concrete adapter each for Deepgram, ElevenLabs, and Gemini.

### 1.5 Database
- Init SQLite with Alembic migrations
- Tables: `scenarios`, `call_results`, `eval_runs`, `failure_events`

---

## Done When
- [ ] `python -m harness.run --dry-run` executes without error
- [ ] All provider adapters load from env vars
- [ ] DB migrations run cleanly
- [ ] Models serialize to/from JSON
- [ ] `.env.example` committed with all required keys

---

## Dependencies
```
google-genai
deepgram-sdk
elevenlabs
pydantic-settings
sqlalchemy
alembic
pytest
pyyaml
```

## New Files (Phase 01)
| File | Purpose |
|------|---------|
| `harness/models.py` | Core dataclasses |
| `harness/providers.py` | LLM/STT/TTS adapters + `MockLLMProvider` |
| `config/settings.py` | pydantic-settings config |
| `data/migrations/` | Alembic SQLite schema |
| `.env.example` | Env var template for demo + CI setup |
