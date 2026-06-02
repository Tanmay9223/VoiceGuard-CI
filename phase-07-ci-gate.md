# Phase 07 — CI Gate & Dashboard

**Goal**: Block bad merges automatically. Show regression deltas clearly.

---

## CI Gate

### 7.1 GitHub Actions Workflow
`.github/workflows/eval.yml`

```yaml
name: Voice Agent Eval
on:
  pull_request:
  push:
    branches: [main]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run eval suite
        run: python -m harness.run --tags ci-gate
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DEEPGRAM_API_KEY: ${{ secrets.DEEPGRAM_API_KEY }}

      - name: Check release decision
        run: python -m ci.gate --run-id $RUN_ID --fail-on block
```

### 7.2 Release Decision Logic
`ci/gate.py`

```python
def decide(scores: list[EvalScore], baseline: EvalScore) -> Decision:
    if any_compliance_failure(scores):
        return Decision.BLOCK, "Compliance violation detected"

    if hallucination_rate(scores) > HALLUCINATION_CAP:
        return Decision.BLOCK, "Hallucination threshold exceeded"

    if regression_delta(scores, baseline) > REGRESSION_TOLERANCE:
        return Decision.WARN, "Quality regression vs baseline"

    return Decision.SHIP, "All checks passed"
```

Outputs: `ship` | `ship_with_warnings` | `block_merge`

### 7.3 Baseline Management
- On merge to `main`, store `EvalScore` summary as the new baseline in `data/baselines/{commit_sha}.json`
- PRs compare against this baseline
- **Seed baseline**: `data/baselines/seed.json` is committed to the repo with realistic hand-crafted scores (compliance 1.0, hallucination 0.0, quality 4.0, tool accuracy 0.95). `baseline.py` falls back to `seed.json` when no commit-sha baseline exists. Prevents the regression delta panel from crashing on the very first run/demo.
- Once a real merge to `main` happens, `seed.json` is superseded by the real baseline.

---

## Dashboard

### 7.4 Streamlit App
`dashboard/app.py` — single-page, 4 panels:

**Panel 1 — Latest Run Summary**
- Pass/fail per scenario
- Overall compliance, hallucination, quality scores
- Release decision badge (green/yellow/red)

**Panel 2 — Regression Delta**
- Compare current run vs baseline
- Show ▲▼ per metric
- Highlight any regressions in red

**Panel 3 — Failure Tag Breakdown**
- Bar chart: failure class frequency over last N runs
- Click a bar → see call transcripts with that tag

**Panel 4 — Production Mining Feed**
- Recent failures auto-added from production
- Status: pending review / added to suite / deduplicated

### 7.5 Run the Dashboard
```bash
streamlit run dashboard/app.py
```

---

## MockLLMProvider (CI Cost Control)
`harness/providers.py` — `MockLLMProvider` class

Activated by `MOCK_LLM=true` env var (or `--mock-llm` CLI flag). Returns fixture-backed responses without any Gemini API call. Used in GitHub Actions to keep CI fast and free.

```yaml
# In eval.yml
- name: Run eval suite
  run: python -m harness.run --tags ci-gate --mock-llm
  env:
    MOCK_LLM: "true"
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}  # still set, but not called
```

Real Gemini is used for local dev runs and live demos. The `MockLLMProvider` lives in `harness/providers.py` (not `ci/`) so the runner can inject it via the standard `LLMProvider` protocol.

---

## Self-Healing Suggestions (Bonus)
`ci/suggestions.py`

When a failure pattern repeats 3+ times across runs, auto-generate:
- A suggested prompt edit (via Gemini)
- A suggested tool schema fix
- The new regression scenario

Write to `data/suggestions/` as markdown files for human review.

---

## Done When
- [ ] GitHub Action runs on every PR
- [ ] `block_merge` decision fails the CI check
- [ ] Dashboard loads and shows last 5 runs
- [ ] Regression delta panel highlights degraded metrics in red
- [ ] Regression delta works on first run (using `seed.json` baseline)
- [ ] Baseline updates on merge to main
- [ ] `MOCK_LLM=true` produces deterministic output with no API calls
