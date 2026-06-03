"""
dashboard/app.py
VoiceGuard CI — Streamlit Dashboard
4 panels: Latest Run Summary | Regression Delta | Failure Tag Breakdown | Production Mining Feed (stub)

Run with: streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import json
from datetime import datetime

# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="VoiceGuard CI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2a2a3e 100%);
        border: 1px solid #3a3a5c;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 8px;
    }
    .metric-label { color: #8888aa; font-size: 12px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
    .metric-value { color: #ffffff; font-size: 28px; font-weight: 700; margin-top: 4px; }
    .metric-delta-pos { color: #4ade80; font-size: 13px; }
    .metric-delta-neg { color: #f87171; font-size: 13px; }

    .decision-ship   { background: linear-gradient(135deg, #064e3b, #065f46); border: 1px solid #34d399; border-radius: 12px; padding: 16px 24px; }
    .decision-warn   { background: linear-gradient(135deg, #451a03, #78350f); border: 1px solid #fbbf24; border-radius: 12px; padding: 16px 24px; }
    .decision-block  { background: linear-gradient(135deg, #450a0a, #7f1d1d); border: 1px solid #f87171; border-radius: 12px; padding: 16px 24px; }
    .decision-text   { color: #ffffff; font-size: 18px; font-weight: 700; }
    .decision-reason { color: #cccccc; font-size: 13px; margin-top: 4px; }

    .stub-panel {
        background: #1a1a2e;
        border: 2px dashed #3a3a5c;
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        color: #666688;
    }

    .stDataFrame { border-radius: 8px; overflow: hidden; }
    h1, h2, h3 { color: #e0e0ff !important; }
    .block-container { padding-top: 1rem; }
    
    /* Hide the default Streamlit deploy button and header */
    .stDeployButton { display: none !important; }
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

RESULTS_DIR = Path("data/results")
BASELINES_DIR = Path("data/baselines")


@st.cache_data(ttl=30)
def load_runs(n: int = 10) -> list[dict]:
    """Load the N most recent run result JSONs."""
    if not RESULTS_DIR.exists():
        return []
    paths = sorted(RESULTS_DIR.glob("run-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    runs = []
    for path in paths[:n]:
        try:
            runs.append(json.loads(path.read_text()))
        except Exception:
            pass
    return runs


@st.cache_data(ttl=30)
def load_baseline() -> dict:
    """Load the most recent baseline (falls back to seed.json)."""
    from ci.baseline import load_baseline as _lb
    return _lb()


def _decision_badge(decision: str) -> str:
    icons = {"ship": "✅ SHIP", "ship_with_warnings": "⚠️ WARN", "block_merge": "🚫 BLOCK"}
    return icons.get(decision, decision.upper())


def _decision_class(decision: str) -> str:
    classes = {"ship": "decision-ship", "ship_with_warnings": "decision-warn", "block_merge": "decision-block"}
    return classes.get(decision, "decision-ship")


def _score_color(val: float, threshold: float) -> str:
    return "🟢" if val >= threshold else "🔴"


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("# 🛡️ VoiceGuard CI")
st.markdown("*Real-time insurance voice agent — CI/CD dashboard*")
st.divider()

# ---------------------------------------------------------------------------
# Sidebar — run selector
# ---------------------------------------------------------------------------

runs = load_runs(n=20)

if not runs:
    st.warning("No run results found in `data/results/`. Run `python -m harness.run --all` first.")
    st.stop()

run_labels = [f"Run {r.get('run_id', '?')} — {r.get('timestamp', '')[:16]}" for r in runs]
selected_idx = st.sidebar.selectbox("Select Run", range(len(runs)), format_func=lambda i: run_labels[i])
run = runs[selected_idx]
baseline = load_baseline()

# ---------------------------------------------------------------------------
# Panel 1 — Latest Run Summary
# ---------------------------------------------------------------------------

st.markdown("## 📊 Panel 1 — Latest Run Summary")

run_id = run.get("run_id", "?")
timestamp = run.get("timestamp", "")[:19].replace("T", " ")
total = run.get("total", 0)
passed = run.get("passed", 0)
failed = run.get("failed", 0)
decision = run.get("release_decision", "ship")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Run ID</div>
        <div class="metric-value" style="font-size:22px;">{run_id}</div>
        <div class="metric-label" style="margin-top:4px;">{timestamp}</div>
    </div>""", unsafe_allow_html=True)
with col2:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Scenarios</div>
        <div class="metric-value">{total}</div>
        <div class="metric-label" style="margin-top:4px; color: #4ade80">{passed} passed</div>
    </div>""", unsafe_allow_html=True)
with col3:
    st.markdown(f"""<div class="metric-card">
        <div class="metric-label">Failed</div>
        <div class="metric-value" style="color: {'#f87171' if failed > 0 else '#4ade80'}">{failed}</div>
    </div>""", unsafe_allow_html=True)
with col4:
    dc = _decision_class(decision)
    badge = _decision_badge(decision)
    reason = run.get("decision_reason", "")
    st.markdown(f"""<div class="{dc}">
        <div class="decision-text">{badge}</div>
        <div class="decision-reason">{reason or "—"}</div>
    </div>""", unsafe_allow_html=True)

# Per-scenario table
st.markdown("#### Scenario Results")
results_data = run.get("results", [])
if results_data:
    rows = []
    for r in results_data:
        scores = r.get("scores", {})
        rows.append({
            "Scenario": r.get("scenario_id", "?"),
            "Status": "✅ Pass" if r.get("passed") else "❌ Fail",
            "Compliance": f"{scores.get('compliance_score', 0):.0%}",
            "Hallucination": f"{scores.get('hallucination_score', 0):.0%}",
            "Quality": f"{scores.get('quality_score', 0):.1f}/5",
            "Tool Acc.": f"{scores.get('tool_accuracy', 0):.0%}",
            "Failure Tags": ", ".join(r.get("failure_tags", [])) or "—",
            "Error": r.get("error") or "—",
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Panel 2 — Regression Delta
# ---------------------------------------------------------------------------

st.markdown("## 📈 Panel 2 — Regression Delta vs Baseline")

if not baseline:
    st.info("No baseline available. Run a full suite on `main` to establish one.")
else:
    from ci.baseline import regression_delta as _rd

    # Aggregate current run scores
    all_results = run.get("results", [])
    metrics = ["compliance_score", "hallucination_score", "quality_score", "tool_accuracy"]
    current_agg = {}
    for m in metrics:
        vals = [float(r.get("scores", {}).get(m, 0)) for r in all_results if "scores" in r]
        current_agg[m] = sum(vals) / len(vals) if vals else 0.0

    deltas = _rd(current_agg, baseline)

    labels = {
        "compliance_score": "Compliance",
        "hallucination_score": "Hallucination (clean rate)",
        "quality_score": "Quality Score",
        "tool_accuracy": "Tool Accuracy",
    }
    thresholds = {
        "compliance_score": 1.0,
        "hallucination_score": 1.0,
        "quality_score": 0.6,   # normalized
        "tool_accuracy": 0.90,
    }

    col_names = ["Metric", "Baseline", "Current", "Delta", "Status"]
    rows = []
    for m, label in labels.items():
        base_val = float(baseline.get(m, 0))
        cur_val = current_agg.get(m, 0)
        delta = deltas.get(m, 0)
        delta_str = f"{'▲' if delta >= 0 else '▼'} {abs(delta):.3f}"
        status = "🔴 Regression" if delta < -0.05 else ("🟢 OK" if delta >= 0 else "🟡 Minor")
        # Format quality_score differently (1-5 scale)
        fmt = (lambda v: f"{v:.1f}/5") if m == "quality_score" else (lambda v: f"{v:.1%}")
        rows.append({
            "Metric": label,
            "Baseline": fmt(base_val),
            "Current": fmt(cur_val),
            "Delta": delta_str,
            "Status": status,
        })

    delta_df = pd.DataFrame(rows)
    st.dataframe(delta_df, use_container_width=True, hide_index=True)

    baseline_note = baseline.get("commit_sha", "seed")
    st.caption(f"Baseline: `{baseline_note}` — {baseline.get('timestamp', '')[:10]}")

st.divider()

# ---------------------------------------------------------------------------
# Panel 3 — Failure Tag Breakdown
# ---------------------------------------------------------------------------

st.markdown("## 🏷️ Panel 3 — Failure Tag Breakdown")

# Aggregate failure tags across all loaded runs
all_tags: dict[str, int] = {}
tag_to_scenarios: dict[str, list[str]] = {}

for r_run in runs[:5]:  # last 5 runs
    for r in r_run.get("results", []):
        for tag in r.get("failure_tags", []):
            all_tags[tag] = all_tags.get(tag, 0) + 1
            tag_to_scenarios.setdefault(tag, []).append(r.get("scenario_id", "?"))

if not all_tags:
    st.success("🎉 No failure tags detected across the last 5 runs!")
else:
    tag_df = pd.DataFrame(
        sorted(all_tags.items(), key=lambda x: -x[1]),
        columns=["Failure Tag", "Count"],
    )
    st.bar_chart(tag_df.set_index("Failure Tag"))

    selected_tag = st.selectbox(
        "Click a tag to see affected scenarios:",
        options=["(none)"] + list(all_tags.keys()),
    )
    if selected_tag != "(none)":
        affected = tag_to_scenarios.get(selected_tag, [])
        st.markdown(f"**Scenarios with `{selected_tag}` ({len(affected)} occurrences):**")
        for sid in set(affected):
            st.markdown(f"- `{sid}`")

st.divider()

# ---------------------------------------------------------------------------
# Panel 4 — Production Mining Feed (Planned stub)
# ---------------------------------------------------------------------------

st.markdown("## 🔬 Panel 4 — Production Mining Feed")
st.markdown("""
<div class="stub-panel">
    <div style="font-size: 48px; margin-bottom: 16px;">🔜</div>
    <div style="font-size: 20px; font-weight: 600; color: #9999bb; margin-bottom: 8px;">Planned: Phase 05</div>
    <div style="font-size: 14px; color: #666688; max-width: 480px; margin: 0 auto;">
        The production mining pipeline will automatically ingest real call failures,
        de-duplicate them, and surface them here as pending regression scenarios.
        <br><br>
        <strong>Hook:</strong> <code>python -m mining.ingest --input data/production-calls/</code>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    "<div style='text-align:center; color: #555577; font-size:12px; margin-top: 16px;'>"
    "VoiceGuard CI · Built with Gemini · Phases 05 & 06 planned"
    "</div>",
    unsafe_allow_html=True,
)
