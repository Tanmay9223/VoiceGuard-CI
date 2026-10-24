import pytest
from harness.tools import ToolRegistry, route_to_agent, _ROUTING_LOG
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

def test_route_to_agent_success():
    """Test that route_to_agent returns correct entry and appends to _ROUTING_LOG."""
    initial_len = len(_ROUTING_LOG)
    reason = "complex claim"

    result = route_to_agent(reason)

    assert result == {"reason": reason, "status": "routed"}
    assert len(_ROUTING_LOG) == initial_len + 1
    assert _ROUTING_LOG[-1] == result

def test_route_to_agent_empty_reason():
    """Test that route_to_agent raises ValueError when reason is empty."""
    with pytest.raises(ValueError, match="route_to_agent requires 'reason' arg."):
        route_to_agent("")

def test_route_to_agent_none_reason():
    """Test that route_to_agent raises ValueError when reason is None."""
    with pytest.raises(ValueError, match="route_to_agent requires 'reason' arg."):
        route_to_agent(None)

@pytest.fixture(autouse=True)
def clear_routing_log():
    """Clear the _ROUTING_LOG before and after each test."""
    _ROUTING_LOG.clear()
    yield
    _ROUTING_LOG.clear()
