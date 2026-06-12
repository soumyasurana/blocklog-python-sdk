"""Tests for BlocklogConfig configuration loading and validation."""

import os
from unittest.mock import patch

import pytest

from blocklog.config import BlocklogConfig


def test_config_default_values():
    """Test that BlocklogConfig has correct default values."""
    config = BlocklogConfig()
    
    assert config.base_url == "http://127.0.0.1:8000/api/v1"
    assert config.api_key == ""
    assert config.signing_key == ""
    assert config.timeout == 10.0
    assert config.max_retries == 3
    assert config.batch_size == 100
    assert config.flush_interval == 2.0


def test_config_from_env():
    """Test that BlocklogConfig loads values from environment variables."""
    with patch.dict(os.environ, {
        "BLOCKLOG_BASE_URL": "https://api.blockloghq.com",
        "BLOCKLOG_API_KEY": "blk_test_key",
        "BLOCKLOG_SDK_SIGNING_KEY": "test_signing_key",
        "BLOCKLOG_TIMEOUT": "30",
        "BLOCKLOG_MAX_RETRIES": "5",
        "BLOCKLOG_BATCH_SIZE": "200",
        "BLOCKLOG_FLUSH_INTERVAL": "5",
    }):
        config = BlocklogConfig()
        
        assert config.base_url == "https://api.blockloghq.com"
        assert config.api_key == "blk_test_key"
        assert config.signing_key == "test_signing_key"
        assert config.timeout == 30.0
        assert config.max_retries == 5
        assert config.batch_size == 200
        assert config.flush_interval == 5.0


def test_config_explicit_values_override_env():
    """Test that explicit config values override environment variables."""
    with patch.dict(os.environ, {
        "BLOCKLOG_API_KEY": "blk_env_key",
        "BLOCKLOG_TIMEOUT": "30",
    }):
        config = BlocklogConfig(api_key="blk_explicit_key", timeout=15.0)
        
        assert config.api_key == "blk_explicit_key"
        assert config.timeout == 15.0


def test_config_from_env_classmethod():
    """Test the from_env class method."""
    with patch.dict(os.environ, {
        "BLOCKLOG_API_KEY": "blk_test_key",
        "BLOCKLOG_BASE_URL": "https://test.api.com",
    }):
        config = BlocklogConfig.from_env()
        
        assert config.api_key == "blk_test_key"
        assert config.base_url == "https://test.api.com"


def test_config_pydantic_validation():
    """Test that Pydantic validates config fields."""
    # Valid config
    config = BlocklogConfig(
        api_key="blk_test",
        timeout=20.0,
        max_retries=5
    )
    assert config.api_key == "blk_test"
    assert config.timeout == 20.0
    assert config.max_retries == 5


def test_config_base_url_trailing_slash():
    """Test that base_url can have trailing slash (transport layer should handle)."""
    config = BlocklogConfig(base_url="https://api.example.com/")
    assert config.base_url == "https://api.example.com/"
