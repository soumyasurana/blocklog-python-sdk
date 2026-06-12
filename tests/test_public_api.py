"""Tests for public API imports and exports."""

import pytest

# Test that the main package can be imported
def test_import_blocklog():
    """Test that blocklog can be imported."""
    import blocklog
    assert blocklog is not None


def test_blocklog_version():
    """Test that blocklog has a version attribute."""
    import blocklog
    assert hasattr(blocklog, "__version__")
    assert blocklog.__version__ == "0.2.0"


def test_public_api_exports():
    """Test that public API exports are available."""
    import blocklog
    
    # Tier 1 exports
    assert hasattr(blocklog, "init")
    assert hasattr(blocklog, "agent")
    assert hasattr(blocklog, "tool")
    assert hasattr(blocklog, "decision")
    assert hasattr(blocklog, "DecisionContext")
    
    # Tier 2 exports
    assert hasattr(blocklog, "approval")
    assert hasattr(blocklog, "replay")


def test_public_api_backward_compatibility():
    """Test that backward compatibility exports work via __getattr__."""
    import blocklog
    
    # These should be accessible via __getattr__ even if not in __all__
    assert hasattr(blocklog, "BlocklogClient")
    assert hasattr(blocklog, "AsyncBlocklogClient")
    assert hasattr(blocklog, "BlocklogConfig")


def test_init_function():
    """Test that init function is callable."""
    import blocklog
    assert callable(blocklog.init)


def test_agent_decorator():
    """Test that agent decorator is callable."""
    import blocklog
    assert callable(blocklog.agent)


def test_tool_decorator():
    """Test that tool decorator is callable."""
    import blocklog
    assert callable(blocklog.tool)


def test_decision_context_manager():
    """Test that decision context manager is callable."""
    import blocklog
    assert callable(blocklog.decision)


def test_approval_module():
    """Test that approval module has expected functions."""
    import blocklog.approval as approval
    
    assert hasattr(approval, "request")
    assert hasattr(approval, "reject")
    assert hasattr(approval, "escalate")
    assert hasattr(approval, "list_overrides")
    assert hasattr(approval, "audit_trail")


def test_replay_module():
    """Test that replay module has expected functions."""
    import blocklog.replay as replay
    
    # replay is a function, not an attribute
    assert callable(replay)


def test_compliance_module():
    """Test that compliance module has expected functions."""
    import blocklog.compliance as compliance
    
    assert hasattr(compliance, "generate")
    assert hasattr(compliance, "get")
    assert hasattr(compliance, "list")
    assert hasattr(compliance, "dashboard")
    assert hasattr(compliance, "share")
    assert hasattr(compliance, "export")


def test_incident_module():
    """Test that incident module has expected functions."""
    import blocklog.incident as incident
    
    assert hasattr(incident, "create")
    assert hasattr(incident, "get")
    assert hasattr(incident, "list_all")


def test_verify_module():
    """Test that verify module has expected functions."""
    import blocklog.verify as verify
    
    assert hasattr(verify, "log")
    assert hasattr(verify, "batch")
    assert hasattr(verify, "decision")


def test_submodule_imports():
    """Test that submodules can be imported directly."""
    from blocklog import BlocklogClient, AsyncBlocklogClient, BlocklogConfig
    from blocklog import init, agent, tool, decision
    from blocklog import DecisionContext
    from blocklog import approval, replay
    
    # Verify they are the expected types
    assert callable(init)
    assert callable(agent)
    assert callable(tool)
    assert callable(decision)
    assert callable(approval.request)
    assert callable(replay)


def test_config_import():
    """Test that BlocklogConfig can be imported."""
    from blocklog.config import BlocklogConfig
    
    config = BlocklogConfig(api_key="test")
    assert config.api_key == "test"


def test_client_import():
    """Test that BlocklogClient can be imported."""
    from blocklog.client import BlocklogClient
    from blocklog.config import BlocklogConfig
    
    config = BlocklogConfig(api_key="test")
    client = BlocklogClient(config)
    assert client.config.api_key == "test"


def test_context_imports():
    """Test that context modules can be imported."""
    from blocklog.context.managers import agent_session
    from blocklog.context.vars import get_context, set_context
    
    assert callable(agent_session)
    assert callable(get_context)
    assert callable(set_context)


def test_models_imports():
    """Test that models can be imported."""
    from blocklog.models.events import EventEnvelope, SessionContext
    from blocklog.models.responses import IngestResponse
    
    event = EventEnvelope(event_type="TEST", payload={})
    assert event.event_type == "TEST"
    
    session = SessionContext()
    assert session.trace_id is not None


def test_signing_imports():
    """Test that signing module can be imported."""
    from blocklog.signing.ed25519 import hash_sign, pseudo_sign
    
    # Both should be available (pseudo_sign is backward compat alias)
    assert callable(hash_sign)
    assert callable(pseudo_sign)
    assert hash_sign is pseudo_sign


def test_transport_imports():
    """Test that transport modules can be imported."""
    from blocklog.transport.auth import build_headers
    from blocklog.transport.httpx_sync import SyncTransport
    from blocklog.transport.retry import RetryPolicy
    
    assert callable(build_headers)
    assert RetryPolicy is not None
    assert SyncTransport is not None


def test_api_imports():
    """Test that API clients can be imported."""
    from blocklog.api.decisions import DecisionsClient
    from blocklog.api.approval import ApprovalClient
    from blocklog.api.replay import ReplayClient
    from blocklog.api.compliance import ComplianceClient
    from blocklog.api.incidents import IncidentsClient
    from blocklog.api.verify import VerifyClient
    from blocklog.api.traces import TracesClient
    
    assert DecisionsClient is not None
    assert ApprovalClient is not None
    assert ReplayClient is not None
    assert ComplianceClient is not None
    assert IncidentsClient is not None
    assert VerifyClient is not None
    assert TracesClient is not None
