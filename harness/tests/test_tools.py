import pytest
from harness.tools import ToolRegistry
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
