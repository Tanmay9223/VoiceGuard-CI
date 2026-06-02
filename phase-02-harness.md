# Phase 02 — Conversation Harness

**Goal**: Build the test runner that simulates full insurance calls end-to-end.

---

## Architecture

```
ScenarioLoader → index.json
CallRunner → [VoiceAgent ↔ CallerSimulator] → ResultCollector
                     ↕
              MockToolRegistry
```

- **ScenarioLoader** — reads YAML call scripts, builds tag index
- **VoiceAgent** — the actual agent under test (Gemini + tools + system prompt)
- **CallerSimulator** — synthetic caller (Gemini playing the caller persona)
- **CallRunner** — orchestrates turn-by-turn conversation
- **ResultCollector** — captures transcripts, timings, tool calls

---

## Tasks

### 2.1 Scenario Loader
`harness/loader.py`
- Load YAML from `scenarios/`
- Validate schema with Pydantic
- Support `includes:` for reusable turn snippets
- **Build `scenarios/index.json`** at load time — tag index keyed by workflow, tag, and failure class. Required for `--tags ci-gate`, `--tags compliance` CLI flags to resolve correctly.

**YAML format:**
```yaml
id: quote-intake-basic
name: Basic Auto Quote
workflow: quote
caller_persona: "Confused first-time buyer, mid-40s"
use_audio_pipeline: false   # true only for asr-noise-injection scenario
turns:
  - speaker: caller
    text: "Hi I need a quote for my car"
  - speaker: agent
    expect:
      - ask_vehicle_details
      - not: mention_competitor
expected_outcomes:
  - tool_called: get_quote
    args: {vehicle: "...", zip: "..."}  # arg schema validated by ToolCallChecker
  - disclosed: premium_disclaimer
tags: [quote, happy-path]
```

### 2.2 Voice Agent (Agent Under Test)
`harness/agent.py`

The **actual voice agent** being tested. This was missing from the original architecture.

```python
class VoiceAgent:
    """The insurance voice agent under test."""
    def __init__(self, tools: ToolRegistry, settings: Settings): ...
    def respond(self, caller_utterance: str) -> tuple[str, list[ToolCall]]: ...
    def reset(self): ...  # called between scenarios to clear conversation history
```

- Has its own Gemini connection with an insurance agent system prompt
- Maintains stateful conversation history within a single call
- Calls mock tools via `ToolRegistry` and returns tool calls as structured data
- `reset()` is called between scenarios to prevent state bleed

### 2.3 Synthetic Caller (Simulator)
`harness/simulator.py`
- LLM playing the caller role
- Receives persona + scenario context
- Responds naturally to agent turns
- Injects noise/interruptions for red-team scenarios

```python
class CallerSimulator:
    def __init__(self, persona: str, scenario: CallScenario): ...
    def respond(self, agent_utterance: str) -> str: ...
    def inject_interruption(self) -> str: ...
```

### 2.4 Call Runner
`harness/runner.py`
- Drives the `VoiceAgent` ↔ `CallerSimulator` conversation
- Enforces max turn limits
- Captures: text, audio bytes (if `use_audio_pipeline: true`), tool calls, timestamps
- For scenarios with `use_audio_pipeline: true`: routes through ElevenLabs TTS → Deepgram STT before passing to VoiceAgent

```python
class CallRunner:
    def run(self, scenario: CallScenario) -> CallResult: ...
    def _run_turn(self, speaker: str, text: str) -> TurnResult: ...
    def _audio_roundtrip(self, text: str) -> str: ...  # TTS → STT
```

### 2.5 Audio Pipeline
- TTS: convert simulator text → audio bytes (ElevenLabs)
- STT: convert audio → agent input text (Deepgram)
- Activated **per-scenario** via `use_audio_pipeline: true` in YAML (not a global flag)
- `asr-noise-injection.yaml` is the **only** scenario with this set to `true`
- All other 8 scenarios pass text directly for CI speed

### 2.6 Tool Mock Layer
`harness/tools.py`
- Mock implementations of agent tools:
  - `get_quote(vehicle, zip)` → returns fixture data
  - `lookup_policy(policy_id)` → returns fixture data
  - `route_to_agent(reason)` → logs routing decision
- Track all tool calls **and their args** per run for scoring (args needed for `ToolCallChecker` arg validation)

### 2.7 Scenario Validator
`harness/validate.py`
- CLI: `python -m harness.validate scenarios/`
- Loads every YAML, checks Pydantic schema compliance
- Verifies all `--tags` values exist in `index.json`
- Prints summary: `9 valid, 0 errors`

---

## Done When
- [ ] `runner.run(scenario)` returns a `CallResult`
- [ ] `VoiceAgent` and `CallerSimulator` complete a full conversation exchange
- [ ] Tool calls **and args** are captured and logged
- [ ] Text-only mode (no audio) works end-to-end
- [ ] `asr-noise-injection` completes the full TTS→STT round-trip
- [ ] All 9 scenarios run sequentially without error
- [ ] `python -m harness.validate scenarios/` prints `9 valid, 0 errors`
- [ ] `scenarios/index.json` generated with correct tags
