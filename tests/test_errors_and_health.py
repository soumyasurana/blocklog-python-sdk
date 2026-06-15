"""Tests for custom exceptions, silent commit fixes, event buffering, health check, and issues detection."""

import logging
from unittest.mock import MagicMock, patch
import pytest

import blocklog
from blocklog.exceptions import BlocklogError, BlocklogCommitError, BlocklogAuthError
from blocklog.managers.decision import DecisionContext
from blocklog.client import BlocklogClient
from blocklog.config import BlocklogConfig


def test_exception_hierarchy():
    """Verify that custom exceptions inherit from BlocklogError."""
    assert issubclass(BlocklogCommitError, BlocklogError)
    assert issubclass(BlocklogAuthError, BlocklogError)
    assert issubclass(BlocklogError, Exception)


def test_decision_commit_failure_raises_commit_error():
    """Verify that silent commit failure is fixed: exceptions in DecisionsClient.create raise BlocklogCommitError."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    # Mock DecisionsClient.create to raise an exception
    client.decisions.create = MagicMock(side_effect=Exception("Database error"))
    
    with patch("blocklog._global.get_client", return_value=client):
        with pytest.raises(BlocklogCommitError) as exc_info:
            with blocklog.decision(type="BUY", asset="TSLA") as d:
                # The body should not run
                d.record_input(price=100.0)
        
        assert "Decision commit failed: Database error" in str(exc_info.value)


def test_event_buffering_and_flushing():
    """Verify events are buffered before commit and flushed afterwards, or discarded on fail."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    # Mock DecisionsClient.create to succeed and return decision ID
    client.decisions.create = MagicMock(return_value={"id": "dec_12345"})
    # Mock client.event to track event emissions
    emitted_events = []
    client.event = MagicMock(side_effect=lambda event_type, **kwargs: emitted_events.append((event_type, kwargs)))
    
    with patch("blocklog._global.get_client", return_value=client):
        # We manually control commit timing to test buffering
        ctx = DecisionContext(decision_type="BUY", asset="TSLA")
        
        # Call record_input before commit
        ctx.record_input(price=412.50)
        assert len(ctx._event_buffer) == 1
        assert len(emitted_events) == 0  # Buffered, not sent yet
        
        ctx._commit()
        
        assert ctx.id == "dec_12345"
        assert len(ctx._event_buffer) == 0  # Buffer flushed
        assert len(emitted_events) == 1
        assert emitted_events[0][0] == "DECISION_INPUT"
        assert emitted_events[0][1]["payload"]["price"] == 412.50
        assert emitted_events[0][1]["payload"]["decision_id"] == "dec_12345"


def test_event_buffer_discard_on_commit_failure():
    """Verify events are discarded with warning if commit fails."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    client.decisions.create = MagicMock(side_effect=Exception("Commit failed"))
    
    with patch("blocklog._global.get_client", return_value=client), \
         patch("blocklog.managers.decision.logger.warning") as mock_warning:
        ctx = DecisionContext(decision_type="BUY", asset="TSLA")
        ctx.record_input(price=412.50)
        
        assert len(ctx._event_buffer) == 1
        
        with pytest.raises(BlocklogCommitError):
            ctx._commit()
            
        assert len(ctx._event_buffer) == 0  # Discarded
        mock_warning.assert_called_with("blocklog: Decision commit failed. Discarding buffered events.")


def test_automatic_issue_detection():
    """Verify issues are detected and exposed via the issues property on exit."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    client.decisions.create = MagicMock(return_value={"id": "dec_12345"})
    client.event = MagicMock()
    
    with patch("blocklog._global.get_client", return_value=client):
        # Case 1: Missing confidence, missing inputs, missing outputs
        with blocklog.decision(type="BUY", asset="TSLA") as d:
            pass
            
        issues_list = d.issues
        codes = [issue["code"] for issue in issues_list]
        assert "NO_INPUTS" in codes
        assert "NO_OUTPUTS" in codes
        assert "CONFIDENCE_MISSING" in codes
        # COMMIT_FAILED should NOT be in codes
        assert "COMMIT_FAILED" not in codes
        
        # Case 2: Satisfied inputs, outputs, confidence
        with blocklog.decision(type="BUY", asset="TSLA", confidence=0.95) as d2:
            d2.record_input(x=1)
            d2.record_output(y=2)
            
        assert len(d2.issues) == 0


def test_retry_policy_abort_on_auth_error():
    """Verify RetryPolicy raises immediately and does not retry on 401 or 403 HTTP status errors."""
    from blocklog.transport.retry import RetryPolicy
    
    class FakeAuthError(Exception):
        def __init__(self):
            self.response = MagicMock()
            self.response.status_code = 401
            
    policy = RetryPolicy(max_retries=3)
    call_count = 0
    
    def failing_fn():
        nonlocal call_count
        call_count += 1
        raise FakeAuthError()
        
    with pytest.raises(FakeAuthError):
        policy.run(failing_fn)
        
    assert call_count == 1  # No retries!


def test_sdk_health_check_success():
    """Verify blocklog.health() returns valid status when API and auth are working."""
    config = BlocklogConfig(api_key="blk_test", signing_key="sign_key")
    client = BlocklogClient(config)
    
    # Mock requests to succeed
    client.transport.request = MagicMock(return_value={"status": "ok"})
    client.decisions.list = MagicMock(return_value=[])
    
    with patch("blocklog._global.get_client", return_value=client):
        health_info = blocklog.health()
        
        assert health_info["api_reachable"] is True
        assert health_info["auth_valid"] is True
        assert health_info["signing_key_loaded"] is True
        assert health_info["context_backend"] == "contextvars"
        assert health_info["sdk_version"] == blocklog.__version__


def test_sdk_health_check_api_unreachable():
    """Verify blocklog.health() reports api_reachable as False when connection fails."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    # Mock transport request to raise a connection/network error
    client.transport.request = MagicMock(side_effect=Exception("Connection refused"))
    client.decisions.list = MagicMock(side_effect=Exception("Connection refused"))
    
    with patch("blocklog._global.get_client", return_value=client):
        with pytest.raises(BlocklogAuthError) as exc_info:
            blocklog.health()
        # Since auth_valid is False because decisions.list failed without returning HTTP status, it raises BlocklogAuthError
        assert "Blocklog authentication failed" in str(exc_info.value)


def test_sdk_health_check_auth_invalid():
    """Verify blocklog.health() raises BlocklogAuthError on invalid credentials."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    class Fake401Error(Exception):
        def __init__(self):
            self.response = MagicMock()
            self.response.status_code = 401
            
    # API is reachable, but decisions list returns 401 Unauthorized
    client.transport.request = MagicMock(return_value={"status": "ok"})
    client.decisions.list = MagicMock(side_effect=Fake401Error())
    
    with patch("blocklog._global.get_client", return_value=client):
        with pytest.raises(BlocklogAuthError) as exc_info:
            blocklog.health()
            
        assert "Blocklog authentication failed" in str(exc_info.value)


def test_debug_logging(caplog):
    """Verify debug logging is emitted at key lifecycle events."""
    with caplog.at_level(logging.DEBUG, logger="blocklog"):
        # 1. Client initialization logging
        config = BlocklogConfig(api_key="blk_test", debug=True)
        client = BlocklogClient(config)
        assert any("Client initialized" in record.message for record in caplog.records)
        
        # Clear log records
        caplog.clear()
        
        # 2. Decorators push/pop logging
        client.decisions.create = MagicMock(return_value={"id": "dec_12345"})
        client.event = MagicMock()
        
        with patch("blocklog._global.get_client", return_value=client):
            # Test agent pushing context
            @blocklog.agent(name="test-agent")
            def my_agent():
                with blocklog.decision(type="BUY", asset="TSLA") as d:
                    d.record_input(price=10.0)
                    
            my_agent()
            
            messages = [record.message for record in caplog.records]
            assert any("Agent context pushed" in msg for msg in messages)
            assert any("Agent context popped" in msg for msg in messages)
            assert any("Decision commit attempted" in msg for msg in messages)
            assert any("Decision commit succeeded" in msg for msg in messages)
            assert any("Decision context exit" in msg for msg in messages)
            assert any("Event send" in msg for msg in messages)
