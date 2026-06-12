"""Tests for @agent and @tool decorators."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from blocklog import agent, tool
from blocklog._global import set_client
from blocklog.client import BlocklogClient
from blocklog.config import BlocklogConfig
from blocklog.context.vars import get_context


@pytest.fixture
def mock_client():
    """Fixture that provides a mock client and sets it as global."""
    config = BlocklogConfig(api_key="blk_test")
    client = BlocklogClient(config)
    # Mock the event method to avoid actual HTTP calls
    client.event = MagicMock()
    set_client(client)
    yield client
    # Clean up
    set_client(None)


def test_tool_decorator_sync(mock_client):
    """Test that @tool decorator works with sync functions."""
    @tool
    def my_function(x: int) -> int:
        return x * 2
    
    result = my_function(5)
    assert result == 10
    # Verify event was emitted
    assert mock_client.event.called


def test_tool_decorator_with_name(mock_client):
    """Test that @tool decorator accepts custom name."""
    @tool(name="custom-tool-name")
    def my_function(x: int) -> int:
        return x * 2
    
    result = my_function(5)
    assert result == 10
    assert mock_client.event.called


def test_tool_decorator_with_metadata(mock_client):
    """Test that @tool decorator accepts metadata."""
    @tool(tags=["external-api"], schema={"input": "int"})
    def my_function(x: int) -> int:
        return x * 2
    
    result = my_function(5)
    assert result == 10
    assert mock_client.event.called


def test_tool_decorator_async(mock_client):
    """Test that @tool decorator works with async functions."""
    @tool
    async def my_async_function(x: int) -> int:
        return x * 2
    
    result = asyncio.run(my_async_function(5))
    assert result == 10
    assert mock_client.event.called


def test_tool_decorator_error_handling(mock_client):
    """Test that @tool decorator handles errors correctly."""
    @tool
    def failing_function():
        raise ValueError("Test error")
    
    with pytest.raises(ValueError, match="Test error"):
        failing_function()
    
    # Verify error event was emitted
    assert mock_client.event.called


def test_agent_decorator_sync(mock_client):
    """Test that @agent decorator works with sync functions."""
    @agent(name="test-agent")
    def my_agent():
        return "agent result"
    
    result = my_agent()
    assert result == "agent result"
    # Verify agent events were emitted
    assert mock_client.event.call_count >= 2  # START and COMPLETE


def test_agent_decorator_with_options(mock_client):
    """Test that @agent decorator accepts options."""
    @agent(name="custom-agent", version="2.0", tags=["prod"])
    def my_agent():
        return "agent result"
    
    result = my_agent()
    assert result == "agent result"
    assert mock_client.event.called


def test_agent_decorator_async(mock_client):
    """Test that @agent decorator works with async functions."""
    @agent(name="async-agent")
    async def my_async_agent():
        return "async agent result"
    
    result = asyncio.run(my_async_agent())
    assert result == "async agent result"
    assert mock_client.event.call_count >= 2


def test_agent_decorator_error_handling(mock_client):
    """Test that @agent decorator handles errors correctly."""
    @agent(name="failing-agent")
    def failing_agent():
        raise RuntimeError("Agent error")
    
    with pytest.raises(RuntimeError, match="Agent error"):
        failing_agent()
    
    # Verify error event was emitted
    assert mock_client.event.call_count >= 2  # START and ERROR


def test_agent_decorator_class(mock_client):
    """Test that @agent decorator works with classes."""
    @agent(name="class-agent")
    class MyAgent:
        def run(self):
            return "class agent result"
    
    agent_instance = MyAgent()
    result = agent_instance.run()
    assert result == "class agent result"
    # Verify agent start event was emitted
    assert mock_client.event.called


def test_tool_without_agent_context(mock_client):
    """Test that @tool works without @agent context."""
    @tool
    def standalone_tool(x: int) -> int:
        return x * 2
    
    result = standalone_tool(5)
    assert result == 10
    assert mock_client.event.called


def test_agent_context_propagation(mock_client):
    """Test that @agent context propagates to @tool calls."""
    @tool
    def helper_tool(x: int) -> int:
        return x * 2
    
    @agent(name="parent-agent")
    def parent_agent():
        return helper_tool(5)
    
    result = parent_agent()
    assert result == 10
    # Both agent and tool events should be emitted
    assert mock_client.event.call_count >= 3  # AGENT_START, TOOL_CALL, AGENT_COMPLETE


def test_decorator_no_args_syntax(mock_client):
    """Test that decorators work without parentheses."""
    @agent
    def simple_agent():
        return "result"
    
    @tool
    def simple_tool(x: int) -> int:
        return x * 2
    
    assert simple_agent() == "result"
    assert simple_tool(5) == 10
