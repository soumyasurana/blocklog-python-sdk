from blocklog.context.managers import agent_session
from blocklog.context.vars import get_context


def test_agent_session_sets_context():
    assert get_context() is None
    with agent_session(agent_id="agent-1", source="test"):
        context = get_context()
        assert context is not None
        assert context.agent_id == "agent-1"
        assert context.source == "test"
    assert get_context() is None
