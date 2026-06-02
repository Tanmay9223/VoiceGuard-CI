# Phase 06 — Model/Provider Comparison

**Goal**: Benchmark multiple STT, TTS, and LLM combos against the same scenario suite and surface the best stack.

---

## Tasks

### 6.1 Provider Matrix Config
`config/providers.yaml`

```yaml
llm:
  - id: gemini-pro
    provider: google
    model: gemini-1.5-pro
  - id: gpt-4o
    provider: openai
    model: gpt-4o

stt:
  - id: deepgram-nova
    provider: deepgram
    model: nova-3
  - id: whisper-large
    provider: openai
    model: whisper-1

tts:
  - id: elevenlabs-rachel
    provider: elevenlabs
    voice_id: 21m00Tcm4TlvDq8ikWAM
  - id: cartesia-default
    provider: cartesia
    voice: default
```

### 6.2 Comparison Runner
`comparison/runner.py`

Run the full scenario suite for each provider combination:

```python
@dataclass
class ComparisonJob:
    llm_id: str
    stt_id: str
    tts_id: str
    scenario_tags: list[str]   # e.g. ["happy-path", "compliance"]

def run_comparison(jobs: list[ComparisonJob]) -> ComparisonReport: ...
```

Parallelize across jobs (use `asyncio` or `ThreadPoolExecutor`).

### 6.3 Metrics Per Stack
Capture for each combination:

| Metric | Source |
|--------|--------|
| `compliance_pass_rate` | Rule evaluator |
| `hallucination_rate` | LLM judge |
| `avg_quality_score` | LLM judge |
| `tool_accuracy` | Rule evaluator |
| `p50_turn_latency_ms` | Timing |
| `p95_turn_latency_ms` | Timing |
| `stt_wer_estimate` | Word error rate proxy |
| `cost_per_call_usd` | Token + API cost estimate |

### 6.4 Comparison Report
`comparison/report.py`

Output a ranked table:

```
Stack                          Compliance  Halluc  Quality  Latency(p95)  Cost/call
gemini-pro + deepgram-nova     100%        0.0%    4.3/5    1.2s          $0.04
gpt-4o + deepgram-nova         98%         1.2%    4.1/5    1.4s          $0.07
gemini-pro + whisper           100%        0.2%    4.2/5    2.1s          $0.05
```

Add a `recommended:` flag to the top-scoring stack that meets all thresholds.

### 6.5 Stack Pinning
After a comparison run:
- Write the recommended stack to `config/current-stack.yaml`
- CI uses this file to decide which provider to run tests against

---

## Done When
- [ ] 2+ LLM providers configured and runnable
- [ ] Comparison table generated from a real run
- [ ] `cost_per_call` estimate included
- [ ] `current-stack.yaml` written after a run
- [ ] Text-only mode (skip TTS/STT) works for fast LLM-only comparisons
