"""Tests for transport layer (sync and async)."""

from unittest.mock import MagicMock, patch

import pytest

from blocklog.transport.auth import build_headers
from blocklog.transport.httpx_sync import SyncTransport
from blocklog.transport.retry import RetryPolicy


def test_build_headers_basic():
    """Test basic header building."""
    headers = build_headers("blk_test_key")
    
    assert headers["Content-Type"] == "application/json"
    assert headers["X-API-Key"] == "blk_test_key"


def test_build_headers_with_extra():
    """Test header building with extra headers."""
    headers = build_headers("blk_test_key", extra={"Custom-Header": "value"})
    
    assert headers["Content-Type"] == "application/json"
    assert headers["X-API-Key"] == "blk_test_key"
    assert headers["Custom-Header"] == "value"


def test_sync_transport_initialization():
    """Test SyncTransport initialization."""
    transport = SyncTransport(
        base_url="https://api.test.com",
        api_key="blk_test_key",
        timeout=15.0
    )
    
    assert transport.base_url == "https://api.test.com"
    assert transport.api_key == "blk_test_key"
    assert transport.timeout == 15.0


def test_sync_transport_base_url_trimming():
    """Test that SyncTransport trims trailing slash from base_url."""
    transport = SyncTransport(
        base_url="https://api.test.com/",
        api_key="blk_test_key",
        timeout=10.0
    )
    
    assert transport.base_url == "https://api.test.com"


def test_retry_policy_initialization():
    """Test RetryPolicy initialization."""
    policy = RetryPolicy(max_retries=5, base_delay=0.5)
    
    assert policy.max_retries == 5
    assert policy.base_delay == 0.5


def test_retry_policy_default_values():
    """Test RetryPolicy default values."""
    policy = RetryPolicy()
    
    assert policy.max_retries == 3
    assert policy.base_delay == 0.25


def test_retry_policy_backoff():
    """Test that backoff increases with attempts."""
    policy = RetryPolicy()
    
    delay1 = policy.backoff(0)
    delay2 = policy.backoff(1)
    delay3 = policy.backoff(2)
    
    # Backoff should increase exponentially
    assert delay2 > delay1
    assert delay3 > delay2


def test_retry_policy_success():
    """Test that retry policy returns immediately on success."""
    policy = RetryPolicy(max_retries=3)
    
    def success_fn():
        return "success"
    
    result = policy.run(success_fn)
    assert result == "success"


def test_retry_policy_failure():
    """Test that retry policy retries on failure."""
    policy = RetryPolicy(max_retries=3)
    call_count = 0
    
    def failing_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"
    
    result = policy.run(failing_fn)
    assert result == "success"
    assert call_count == 3


def test_retry_policy_exhausted():
    """Test that retry policy raises after max retries."""
    policy = RetryPolicy(max_retries=2)
    
    def always_failing_fn():
        raise ValueError("Persistent error")
    
    with pytest.raises(ValueError, match="Persistent error"):
        policy.run(always_failing_fn)


@patch("blocklog.transport.httpx_sync.httpx")
def test_sync_transport_request_with_httpx(mock_httpx):
    """Test SyncTransport.request with httpx available."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.request.return_value = mock_response
    mock_httpx.Client.return_value = mock_client
    mock_httpx.Client.timeout = 10.0
    
    transport = SyncTransport(
        base_url="https://api.test.com",
        api_key="blk_test_key",
        timeout=10.0
    )
    
    result = transport.request("POST", "/test", json={"data": "value"})
    
    assert result == {"result": "success"}
    mock_client.request.assert_called_once()
    call_args = mock_client.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "https://api.test.com/test"
    assert call_args[1]["json"] == {"data": "value"}


@patch("blocklog.transport.httpx_sync.httpx", None)
@patch("blocklog.transport.httpx_sync.requests")
def test_sync_transport_request_with_requests_fallback(mock_requests):
    """Test SyncTransport.request falls back to requests when httpx unavailable."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": "success"}
    mock_response.raise_for_status = MagicMock()
    mock_requests.request.return_value = mock_response
    
    transport = SyncTransport(
        base_url="https://api.test.com",
        api_key="blk_test_key",
        timeout=10.0
    )
    
    result = transport.request("POST", "/test", json={"data": "value"})
    
    assert result == {"result": "success"}
    mock_requests.request.assert_called_once()
