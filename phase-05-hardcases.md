# Phase 05 — Hard-Case Mining

**Goal**: Automatically pull production failures and convert them into regression scenarios.

---

## Pipeline

```
Production Calls → Ingestion → Failure Detection → Dedup → Scenario Gen → Regression Suite
```

---

## Tasks

### 5.1 Production Call Ingestion
`mining/ingest.py`

Support two input modes:

**Mode A — File drop** (MVP):
- Watch `data/production-calls/` for new JSON files
- Expected format:
```json
{
  "call_id": "prod-xyz",
  "timestamp": "2025-01-01T10:00:00Z",
  "transcript": [...],
  "tool_calls": [...],
  "outcome": "transferred | completed | abandoned",
  "metadata": {}
}
```

**Mode B — API pull** (later):
- Webhook or polling adapter (plug in your call platform)

### 5.2 Failure Detector
`mining/detector.py`

Runs the same scoring pipeline (Phase 04) on ingested calls.
Flag calls where:
- Any compliance rule fails, OR
- Hallucination judge confidence > 0.5, OR
- Outcome = `abandoned` with no escalation

```python
def detect_failures(call: ProductionCall) -> list[FailureEvent]: ...
```

### 5.3 Deduplication
`mining/dedup.py`

Avoid adding near-duplicate scenarios:
- Embed failure description with a small LLM call
- Compare cosine similarity against existing regression scenarios
- Skip if similarity > 0.85

### 5.4 Scenario Generator
`mining/generator.py`

Convert a `FailureEvent` → a new YAML scenario:

```python
def generate_scenario(failure: FailureEvent) -> CallScenario:
    # Use Gemini to:
    # 1. Summarize the failure pattern
    # 2. Create a reproducible caller persona + seed turns
    # 3. Set expected_outcomes to what SHOULD have happened
    # 4. Tag with failure class
```

Write output to `scenarios/regression/`.

### 5.5 Review Queue (Optional but recommended)
`mining/review.py`

Before auto-adding to CI suite:
- Write new scenarios to `scenarios/regression/pending/`
- Simple CLI: `python -m mining.review` shows diffs, approve/reject
- Auto-approve if failure class is already in taxonomy and score is < 0.3

### 5.6 Metrics
Track in DB:
- `new_failures_this_week`
- `scenarios_auto_added`
- `duplicate_skipped`
- `regression_catch_rate` (did the new scenario catch a re-introduced bug?)

---

## Done When
- [ ] Drop a production call JSON → failure detected → scenario written to `regression/`
- [ ] Dedup prevents identical scenarios
- [ ] Generated scenarios pass schema validation
- [ ] 3 hand-crafted production failures seed the initial regression suite
