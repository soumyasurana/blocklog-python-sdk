"""Tests for BlocklogClient initialization and basic functionality."""

from unittest.mock import MagicMock, patch

import pytest

from blocklog.client import BlocklogClient
from blocklog.config import BlocklogConfig


def test_client_initialization():
    """Test that BlocklogClient initializes correctly with config."""
    config = BlocklogConfig(
        api_key="blk_test_key",
        base_url="https://api.test.com",
        timeout=15.0,
        max_retries=5,
        batch_size=50
    )
    
    client = BlocklogClient(config)
    
    assert client.config.api_key == "blk_test_key"
    assert client.config.base_url == "https://api.test.com"
    assert client.config.timeout == 15.0
    assert client.config.max_retries == 5
    assert client.config.batch_size == 50


def test_client_from_env():
    """Test BlocklogClient.from_env class method."""
    with patch.dict("os.environ", {
        "BLOCKLOG_API_KEY": "blk_env_key",
        "BLOCKLOG_BASE_URL": "https://env.api.com",
    }):
        client = BlocklogClient.from_env()
        
        assert client.config.api_key == "blk_env_key"
        assert client.config.base_url == "https://env.api.com"


def test_client_subclients_initialized():
    """Test that all Layer 2 sub-clients are initialized."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    assert hasattr(client, "decisions")
    assert hasattr(client, "incidents")
    assert hasattr(client, "approval")
    assert hasattr(client, "replay")
    assert hasattr(client, "compliance")
    assert hasattr(client, "verify")
    assert hasattr(client, "traces")


def test_client_backward_compatibility_aliases():
    """Test that backward compatibility aliases exist."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    assert client.forensics is client.replay
    assert client.hitl is client.approval


def test_client_add_hook():
    """Test that hooks can be added to the client."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    hook = lambda payload: payload
    result = client.add_hook(hook)
    
    assert result is client
    assert len(client.hooks) == 1
    assert client.hooks[0] is hook


def test_client_session_context_manager():
    """Test that session context manager is available."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    assert hasattr(client, "session")
    session = client.session(agent_id="test-agent")
    assert session is not None


def test_client_event_building():
    """Test that event building works correctly."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    event = client._build_event(
        event_type="TEST_EVENT",
        payload={"test": "data"},
        source="test-source"
    )
    
    assert event.event_type == "TEST_EVENT"
    assert event.payload == {"test": "data"}
    assert event.source == "test-source"
    assert event.idempotency_key is not None


def test_client_idempotency_key_generation():
    """Test that idempotency keys are generated deterministically."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    event1 = client._build_event(
        event_type="TEST",
        payload={"key": "value"},
        source="test"
    )
    event2 = client._build_event(
        event_type="TEST",
        payload={"key": "value"},
        source="test"
    )
    
    # Same inputs should produce same idempotency key
    assert event1.idempotency_key == event2.idempotency_key


def test_client_serialization():
    """Test that event serialization works correctly."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    
    event = client._build_event(
        event_type="TEST_EVENT",
        payload={"test": "data"},
        source="test-source"
    )
    
    serialized = client._serialize(event)
    
    assert serialized["event_type"] == "TEST_EVENT"
    assert serialized["data"] == {"test": "data"}
    assert serialized["source"] == "test-source"
    assert "timestamp" in serialized
    assert serialized["idempotency_key"] is not None


def test_client_serialization_with_signing():
    """Test that event serialization includes signature when signing_key is set."""
    config = BlocklogConfig(
        api_key="blk_test",
        signing_key="test_signing_key"
    )
    client = BlocklogClient(config)
    
    event = client._build_event(
        event_type="TEST_EVENT",
        payload={"test": "data"},
        source="test-source"
    )
    
    serialized = client._serialize(event)
    
    assert "log_signature" in serialized
    assert serialized["log_signature"] is not None


def test_client_instrumentation_methods():
    """Test that instrumentation methods return the correct handler types."""
    from blocklog.integrations.langchain import BlocklogLangChainCallbackHandler
    from blocklog.integrations.langgraph import BlocklogLangGraphCallbackHandler
    from blocklog.integrations.litellm import BlocklogLiteLLMCallbackHandler

    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)

    # LangChain — returns a handler with the standard callback interface
    result = client.instrument_langchain()
    assert isinstance(result, BlocklogLangChainCallbackHandler)
    assert hasattr(result, "on_chain_start")
    assert hasattr(result, "on_llm_start")
    assert hasattr(result, "on_tool_start")

    # LangGraph — returns a handler, not the client
    result = client.instrument_langgraph()
    assert isinstance(result, BlocklogLangGraphCallbackHandler)
    assert hasattr(result, "on_chain_start")
    assert hasattr(result, "on_node_start")

    # OpenAI — global patch path returns None (no openai_client arg);
    # the scoped path (openai_client=...) returns the patched instance
    result = client.instrument_openai_agents()
    assert result is None

    # LiteLLM — returns a handler with the CustomLogger interface
    result = client.instrument_litellm()
    assert isinstance(result, BlocklogLiteLLMCallbackHandler)
    assert hasattr(result, "log_pre_api_call")
    assert hasattr(result, "log_success_event")
    assert hasattr(result, "async_log_success_event")
    assert hasattr(result, "log_failure_event")
    assert hasattr(result, "async_log_failure_event")