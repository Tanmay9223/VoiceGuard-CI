import pytest
from harness.tools import route_to_agent, _ROUTING_LOG

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
