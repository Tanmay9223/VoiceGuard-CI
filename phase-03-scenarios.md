# Phase 03 — Scenario Library

**Goal**: Write 20–30 call scenarios covering happy paths, edge cases, and red-team attacks.

---

## Scenario Categories

### A. Happy Path (8 scenarios)
Standard workflows with cooperative callers.

| ID | Workflow | Description |
|----|----------|-------------|
| `quote-auto-basic` | Quote | New auto quote, all info provided |
| `quote-home-basic` | Quote | Home insurance quote |
| `quote-multi-policy` | Quote | Bundle auto + home |
| `renewal-accept` | Renewal | Policy up for renewal, caller accepts |
| `renewal-question` | Renewal | Caller asks about rate increase |
| `claim-fnol` | Claims | First notice of loss, auto |
| `claim-status-check` | Claims | Follow-up on existing claim |
| `lead-qualification` | Lead | Inbound lead, fully qualifies |

### B. Edge Cases (8 scenarios)
Realistic friction without adversarial intent.

| ID | Description |
|----|-------------|
| `quote-missing-vin` | Caller doesn't have VIN handy |
| `quote-bad-zip` | Caller gives wrong zip, corrects later |
| `renewal-cancel-request` | Caller wants to cancel mid-flow |
| `claim-third-party` | Third party calling on behalf of insured |
| `lead-not-ready` | Lead interested but not ready to buy |
| `multilingual-mix` | Caller mixes languages mid-call |
| `elderly-repeat` | Caller asks same question 3x |
| `background-noise` | ASR-confusing input simulation |

### C. Red-Team / Adversarial (8 scenarios)
Designed to break the agent.

| ID | Failure Class Targeted |
|----|------------------------|
| `jailbreak-quote-discount` | Prompt injection via caller input |
| `hostile-claim-denial` | Aggressive caller, escalating |
| `compliance-trap-recording` | Caller tries to waive disclosure |
| `hallucination-bait` | Asks about policy features not in context |
| `bad-interruption` | Constant interruptions during disclosure |
| `wrong-routing-test` | Complex case that should escalate |
| `pii-extraction-attempt` | Probing for other customers' data |
| `tool-abuse-loop` | Triggers repeated tool calls |

### D. Regression / Hard Cases (Dynamic)
Seeded from production failures via Phase 05 mining pipeline. Start with 3–5 hand-crafted examples.

---

## YAML File Structure

```
scenarios/
├── happy-path/
│   ├── quote-auto-basic.yaml
│   └── ...
├── edge-cases/
│   └── ...
├── red-team/
│   └── ...
└── regression/
    └── ...        ← auto-populated by mining pipeline
```

---

## Tasks

### 3.1 Write all 20+ YAML scenarios
Follow the schema from Phase 02. Each scenario needs:
- `id`, `name`, `workflow`, `tags`
- `caller_persona` (1–2 sentence description)
- `turns` (seed turns; simulator fills the rest)
- `expected_outcomes` (tool calls, disclosures, routing)
- `failure_class` (for red-team scenarios)

### 3.2 Scenario Validation CLI
```bash
python -m harness.validate scenarios/
# Output: 24 valid, 0 errors
```

### 3.3 Tag Index
Build `scenarios/index.json` at load time:
- By workflow, by tag, by failure class
- Used by CI to run subsets: `--tags compliance`

---

## Done When
- [ ] 20+ scenarios written and validated
- [ ] All 4 workflow types covered
- [ ] At least 5 red-team scenarios
- [ ] Tag index generated correctly
