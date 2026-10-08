import pytest
from unittest.mock import Mock
from scoring.aggregator import _safe_judge
from harness.models import CallResult

def test_safe_judge_returns_default_on_exception():
    # Arrange
    class MockJudgeClass:
        def judge(self, result, llm):
            raise Exception("Test exception")

    mock_judge = MockJudgeClass().judge

    mock_result = Mock(spec=CallResult)
    mock_llm = Mock()
    default_return = {"test": "default"}

    # Act
    result = _safe_judge(mock_judge, mock_result, mock_llm, default_return)

    # Assert
    assert result == default_return

def test_safe_judge_returns_success():
    # Arrange
    success_return = {"test": "success"}

    class MockJudgeClass:
        def judge(self, result, llm):
            return success_return

    mock_judge = MockJudgeClass().judge

    mock_result = Mock(spec=CallResult)
    mock_llm = Mock()
    default_return = {"test": "default"}

    # Act
    result = _safe_judge(mock_judge, mock_result, mock_llm, default_return)

    # Assert
    assert result == success_return
