# Phase 04 — Scoring Engine

**Goal**: Hybrid evaluation — deterministic rules for compliance, LLM judges for quality.

---

## Failure Taxonomy

Tag every `CallResult` with zero or more failure classes:

| Tag | Type | Evaluator | Description |
|-----|------|-----------|-------------|
| `hallucinated_quote` | LLM | `HallucinationJudge` | Agent stated coverage/price not in context |
| `missed_disclosure` | Rule | `DisclosureChecker` | Required legal disclosure not made |
| `compliance_violation` | Rule | `DisclosureChecker` | Violated a policy rule (e.g. recorded consent) |
| `wrong_routing` | Rule | `RoutingChecker` | Should have escalated but didn't |
| `bad_interruption` | LLM | `InterruptionHandlingJudge` | Lost coherence after caller cut in |
| `asr_recovery_fail` | LLM | `ConversationQualityJudge` | Didn't handle transcription error gracefully |
| `tool_misuse` | Rule | `ToolCallChecker` | Wrong tool called OR called with bad/missing args |

**Coverage**: 4 rule-based (`DisclosureChecker` ×2, `RoutingChecker`, `ToolCallChecker`) + 3 LLM judges = **all 7 classes covered**.

---

## Tasks

### 4.1 Rule-Based Evaluators
`scoring/rules.py`

Each evaluator: takes `CallResult` → returns `RuleScore(passed: bool, detail: str)`.

```python
class DisclosureChecker:
    """Verify required disclosures appear in transcript.
    Covers: missed_disclosure + compliance_violation"""
    REQUIRED = ["recording consent", "premium disclaimer", "coverage limitations"]
    def evaluate(self, result: CallResult) -> RuleScore: ...

class ToolCallChecker:
    """Two-part check: (1) correct tool called, (2) args match expected schema.
    Covers: tool_misuse (both wrong-tool AND bad-arg cases)
    Example: get_quote called without 'zip' arg → tool_misuse even if tool name is correct."""
    def evaluate(self, result: CallResult, scenario: CallScenario) -> RuleScore: ...

class RoutingChecker:
    """Verify escalation happened when required.
    Covers: wrong_routing"""
    def evaluate(self, result: CallResult) -> RuleScore: ...
```

### 4.2 LLM-as-Judge
`scoring/llm_judge.py`

Use Gemini as the evaluator. One judge per quality dimension:

```python
class HallucinationJudge:
    system = """You are evaluating an insurance agent transcript.
    Flag any claims the agent made that are NOT supported by the provided context.
    Return JSON: {"hallucinations": [], "confidence": 0.0-1.0}"""

class ConversationQualityJudge:
    system = """Score the conversation on: clarity, empathy, recovery from errors.
    Return JSON: {"score": 1-5, "issues": [], "reasoning": "..."}"""

class InterruptionHandlingJudge:
    system = """Did the agent handle interruptions gracefully?
    Return JSON: {"handled_well": bool, "examples": []}"""
```

Keep judge prompts short. Pass only the relevant transcript slice, not the full call.

### 4.3 Score Aggregator
`scoring/aggregator.py`

```python
@dataclass
class EvalScore:
    compliance_score: float      # 0–1, rule-based
    hallucination_score: float   # 0–1, LLM judge
    quality_score: float         # 1–5, LLM judge
    tool_accuracy: float         # 0–1, rule-based
    failure_tags: list[str]
    overall_pass: bool

def aggregate(result: CallResult, scenario: CallScenario) -> EvalScore: ...
```

### 4.4 Thresholds (in `config/settings.py`)
```python
COMPLIANCE_PASS_RATE = 1.0        # zero tolerance
HALLUCINATION_CAP = 0.0           # zero tolerance
MIN_QUALITY_SCORE = 3.0           # out of 5
TOOL_ACCURACY_FLOOR = 0.90
```

### 4.5 Scoring CLI
```bash
python -m scoring.run --result results/run-abc123.json
# Output: compliance ✅  hallucination ✅  quality 4.1/5  tools 95%
```

---

## Done When
- [ ] All **7 failure classes** have a mapped evaluator (4 rule-based + 3 LLM judges)
- [ ] `ToolCallChecker` catches both wrong-tool AND bad-arg cases
- [ ] LLM judges return structured JSON reliably
- [ ] `aggregate()` produces a valid `EvalScore`
- [ ] Thresholds enforced — a seeded bad result causes failure
- [ ] `scoring/tests/test_seeded_failure.py` passes with `pytest -v`
