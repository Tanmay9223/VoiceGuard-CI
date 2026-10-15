import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from mining.generator import generate_scenario
from mining.models import FailureEvent, ProductionCall, ProductionTurn

@pytest.fixture
def mock_failure():
    call = ProductionCall(
        call_id="call-123",
        turns=[
            ProductionTurn(speaker="caller", text="Hello"),
            ProductionTurn(speaker="agent", text="Hi, how can I help?")
        ]
    )
    return FailureEvent(
        call_id="call-123",
        failure_tags=["hallucination"],
        call_data=call
    )

@pytest.fixture
def mock_llm_provider():
    provider = Mock()
    return provider

def test_generate_scenario_malformed_json_returns_none(mock_failure, mock_llm_provider):
    mock_llm_provider.complete.return_value = "invalid json {[[[]]}"

    with patch("mining.generator.logger") as mock_logger:
        result = generate_scenario(mock_failure, mock_llm_provider)

        assert result is None
        mock_logger.error.assert_called_once()
        args, _ = mock_logger.error.call_args
        assert "[Generator] Failed to generate scenario from LLM: %s" == args[0]

def test_generate_scenario_valid_json_returns_path(mock_failure, mock_llm_provider, tmp_path):
    import json
    valid_json = {
        "workflow": "quote",
        "caller_persona": "A user",
        "opening_line": "Hello",
        "expected_outcomes": []
    }
    mock_llm_provider.complete.return_value = json.dumps(valid_json)

    with patch("mining.generator.Path") as mock_path_class:
        mock_out_dir = MagicMock()
        mock_path_class.return_value = mock_out_dir

        mock_out_path = MagicMock()
        mock_out_dir.__truediv__.return_value = mock_out_path

        mock_file = Mock()
        mock_out_path.open.return_value.__enter__.return_value = mock_file

        result = generate_scenario(mock_failure, mock_llm_provider)

        assert result is mock_out_path
        mock_out_path.open.assert_called_once_with("w")
