import pytest
from unittest import mock
from harness.tools import ToolRegistry, _REGISTRY
from harness.models import ToolCall

def test_tool_registry_unknown_tool():
    """Test that ToolRegistry handles unknown tool calls correctly."""
    registry = ToolRegistry()

    # Call with an unknown tool name
    result = registry.call("some_unknown_tool_name", param1="value1", param2=123)

    # Assert return value is None
    assert result is None

    # Assert call_history recorded the tool call correctly
    assert len(registry.call_history) == 1

    call_record = registry.call_history[0]
    assert call_record.name == "some_unknown_tool_name"
    assert call_record.args == {"param1": "value1", "param2": 123}
    assert call_record.response is None

def test_tool_registry_execution():
    """Test that ToolRegistry successfully executes a tool and records it."""

    def mock_fn(**kwargs):
        return {"status": "success", "data": kwargs}

    with mock.patch.dict("harness.tools._REGISTRY", {"mock_tool": (mock_fn, [])}):
        registry = ToolRegistry()
        result = registry.call("mock_tool", arg1="test", arg2=42)

        assert result == {"status": "success", "data": {"arg1": "test", "arg2": 42}}
        assert len(registry.call_history) == 1

        call_record = registry.call_history[0]
        assert call_record.name == "mock_tool"
        assert call_record.args == {"arg1": "test", "arg2": 42}
        assert call_record.response == {"status": "success", "data": {"arg1": "test", "arg2": 42}}

def test_tool_registry_error_handling():
    """Test that ToolRegistry handles ValueErrors raised by tools."""

    def mock_fn_error(**kwargs):
        raise ValueError("Missing required arguments")

    with mock.patch.dict("harness.tools._REGISTRY", {"mock_error_tool": (mock_fn_error, [])}):
        registry = ToolRegistry()
        result = registry.call("mock_error_tool", arg1="test")

        assert result == {"error": "Missing required arguments"}
        assert len(registry.call_history) == 1

        call_record = registry.call_history[0]
        assert call_record.name == "mock_error_tool"
        assert call_record.args == {"arg1": "test"}
        assert call_record.response == {"error": "Missing required arguments"}
