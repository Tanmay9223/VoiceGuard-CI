import pytest
from unittest.mock import patch, MagicMock

from ci.gate import decide, _aggregate_run_scores
from harness.models import ReleaseDecision

def test_decide_compliance_violation():
    run_summary = {
        "results": [
            {
                "scenario_id": "test_1",
                "failure_tags": ["compliance_violation"]
            }
        ]
    }
    settings = MagicMock()
    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.BLOCK
    assert "Compliance violation" in reason
    assert "test_1" in reason

def test_decide_missed_disclosure():
    run_summary = {
        "results": [
            {
                "scenario_id": "test_2",
                "failure_tags": ["missed_disclosure"]
            }
        ]
    }
    settings = MagicMock()
    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.BLOCK
    assert "Compliance violation" in reason

def test_decide_hallucinated_quote():
    run_summary = {
        "results": [
            {
                "scenario_id": "test_3",
                "failure_tags": ["hallucinated_quote"]
            }
        ]
    }
    settings = MagicMock()
    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.BLOCK
    assert "Hallucination detected" in reason

@patch('ci.gate.load_baseline')
def test_decide_regression_warn(mock_load_baseline):
    mock_load_baseline.return_value = {
        "quality_score": 5.0
    }
    run_summary = {
        "results": [
            {
                "scores": {
                    "quality_score": 4.0
                }
            }
        ]
    }
    settings = MagicMock()
    settings.regression_tolerance = 0.5

    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.WARN
    assert "Quality regression vs baseline" in reason

@patch('ci.gate.load_baseline')
def test_decide_no_regression_ship(mock_load_baseline):
    mock_load_baseline.return_value = {
        "quality_score": 4.5
    }
    run_summary = {
        "results": [
            {
                "scores": {
                    "quality_score": 4.2
                }
            }
        ]
    }
    settings = MagicMock()
    settings.regression_tolerance = 0.5

    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.SHIP
    assert reason == "All checks passed."

@patch('ci.gate.load_baseline')
def test_decide_no_baseline_ship(mock_load_baseline):
    mock_load_baseline.return_value = {}
    run_summary = {
        "results": [
            {
                "scores": {
                    "quality_score": 4.0
                }
            }
        ]
    }
    settings = MagicMock()

    decision, reason = decide(run_summary, settings)
    assert decision == ReleaseDecision.SHIP
    assert reason == "All checks passed."

def test_aggregate_run_scores():
    run_summary = {
        "results": [
            {
                "scores": {
                    "compliance_score": 1.0,
                    "quality_score": 5.0,
                    "hallucination_score": 0.0,
                    "tool_accuracy": 1.0
                }
            },
            {
                "scores": {
                    "compliance_score": 0.0,
                    "quality_score": 3.0,
                    "hallucination_score": 0.2,
                    "tool_accuracy": 0.8
                }
            }
        ]
    }

    aggregated = _aggregate_run_scores(run_summary)
    assert aggregated["compliance_score"] == 0.5
    assert aggregated["quality_score"] == 4.0
    assert aggregated["hallucination_score"] == pytest.approx(0.1)
    assert aggregated["tool_accuracy"] == 0.9

def test_aggregate_run_scores_empty():
    run_summary = {"results": []}
    assert _aggregate_run_scores(run_summary) == {}
