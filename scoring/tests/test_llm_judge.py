import json
import logging
from unittest.mock import Mock
import pytest

from scoring.llm_judge import _call_judge, _JUDGE_SYSTEM
from harness.providers import LLMProvider

def test_call_judge_valid_json():
    # Arrange
    llm_mock = Mock(spec=LLMProvider)
    expected_dict = {"score": 5, "issues": [], "reasoning": "Good"}
    llm_mock.complete.return_value = json.dumps(expected_dict)
    prompt = "Test prompt"

    # Act
    result = _call_judge(llm_mock, prompt)

    # Assert
    assert result == expected_dict
    llm_mock.complete.assert_called_once_with([{"role": "user", "content": prompt}], system=_JUDGE_SYSTEM)

def test_call_judge_invalid_json(caplog):
    # Arrange
    llm_mock = Mock(spec=LLMProvider)
    llm_mock.complete.return_value = "invalid json string"
    prompt = "Test prompt"

    # Act & Assert
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ValueError, match="Judge returned invalid JSON"):
            _call_judge(llm_mock, prompt)

    assert "[Judge] Failed to parse JSON: 'invalid json string'" in caplog.text
