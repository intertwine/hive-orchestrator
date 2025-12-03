"""Tests for the Weave tracing integration module."""

# pylint: disable=unused-argument,import-error,wrong-import-position,protected-access

import sys
import os
import json
from unittest.mock import Mock, patch

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tracing import (
    is_tracing_enabled,
    init_tracing,
    get_tracing_status,
    trace_op,
    traced_llm_call,
    LLMCallMetadata,
    _extract_token_usage,
    _sanitize_headers,
    print_tracing_status,
    _weave_available,
)


class TestTracingEnabled:
    """Test the is_tracing_enabled function."""

    def test_tracing_enabled_when_weave_available(self, monkeypatch):
        """Test tracing is enabled when weave is available and not disabled."""
        monkeypatch.delenv("WEAVE_DISABLED", raising=False)

        # Should be enabled since weave is installed
        if _weave_available:
            assert is_tracing_enabled() is True

    def test_tracing_disabled_by_env_true(self, monkeypatch):
        """Test tracing disabled when WEAVE_DISABLED=true."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        assert is_tracing_enabled() is False

    def test_tracing_disabled_by_env_1(self, monkeypatch):
        """Test tracing disabled when WEAVE_DISABLED=1."""
        monkeypatch.setenv("WEAVE_DISABLED", "1")
        assert is_tracing_enabled() is False

    def test_tracing_disabled_by_env_yes(self, monkeypatch):
        """Test tracing disabled when WEAVE_DISABLED=yes."""
        monkeypatch.setenv("WEAVE_DISABLED", "yes")
        assert is_tracing_enabled() is False

    def test_tracing_enabled_with_false_value(self, monkeypatch):
        """Test tracing enabled when WEAVE_DISABLED=false."""
        monkeypatch.setenv("WEAVE_DISABLED", "false")
        if _weave_available:
            assert is_tracing_enabled() is True


class TestGetTracingStatus:
    """Test the get_tracing_status function."""

    def test_status_contains_required_fields(self):
        """Test that status contains all required fields."""
        status = get_tracing_status()

        assert "weave_available" in status
        assert "tracing_enabled" in status
        assert "tracing_initialized" in status
        assert "project" in status
        assert "disabled_by_env" in status

    def test_status_default_project(self, monkeypatch):
        """Test default project name."""
        monkeypatch.delenv("WEAVE_PROJECT", raising=False)
        status = get_tracing_status()
        assert status["project"] == "agent-hive"

    def test_status_custom_project(self, monkeypatch):
        """Test custom project name from environment."""
        monkeypatch.setenv("WEAVE_PROJECT", "my-custom-project")
        status = get_tracing_status()
        assert status["project"] == "my-custom-project"

    def test_disabled_by_env_true(self, monkeypatch):
        """Test disabled_by_env reflects environment."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        status = get_tracing_status()
        assert status["disabled_by_env"] is True

    def test_disabled_by_env_false(self, monkeypatch):
        """Test disabled_by_env when not disabled."""
        monkeypatch.delenv("WEAVE_DISABLED", raising=False)
        status = get_tracing_status()
        assert status["disabled_by_env"] is False


class TestLLMCallMetadata:
    """Test the LLMCallMetadata class."""

    def test_metadata_initialization(self):
        """Test metadata can be initialized with basic values."""
        metadata = LLMCallMetadata(
            model="test-model",
            api_url="https://api.test.com",
        )

        assert metadata.model == "test-model"
        assert metadata.api_url == "https://api.test.com"
        assert metadata.success is True
        assert metadata.error is None
        assert metadata.timestamp is not None

    def test_metadata_with_all_fields(self):
        """Test metadata with all fields populated."""
        metadata = LLMCallMetadata(
            model="anthropic/claude-haiku-4.5",
            api_url="https://openrouter.ai/api/v1/chat/completions",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=1234.5,
            success=True,
            error=None,
        )

        assert metadata.prompt_tokens == 100
        assert metadata.completion_tokens == 50
        assert metadata.total_tokens == 150
        assert metadata.latency_ms == 1234.5

    def test_metadata_to_dict(self):
        """Test metadata serialization to dictionary."""
        metadata = LLMCallMetadata(
            model="test-model",
            api_url="https://api.test.com",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            latency_ms=500.0,
            success=True,
        )

        result = metadata.to_dict()

        assert result["model"] == "test-model"
        assert result["api_url"] == "https://api.test.com"
        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["latency_ms"] == 500.0
        assert result["success"] is True
        assert result["error"] is None
        assert "timestamp" in result

    def test_metadata_with_error(self):
        """Test metadata with error status."""
        metadata = LLMCallMetadata(
            model="test-model",
            api_url="https://api.test.com",
            success=False,
            error="Connection timeout",
        )

        assert metadata.success is False
        assert metadata.error == "Connection timeout"


class TestSanitizeHeaders:
    """Test the _sanitize_headers function."""

    def test_sanitize_authorization_header(self):
        """Test that Authorization header is redacted."""
        headers = {
            "Authorization": "Bearer sk-secret-key-12345",
            "Content-Type": "application/json",
        }
        result = _sanitize_headers(headers)
        assert result["Authorization"] == "***REDACTED***"
        assert result["Content-Type"] == "application/json"

    def test_sanitize_api_key_header(self):
        """Test that API-Key header is redacted."""
        headers = {
            "API-Key": "my-secret-api-key",
            "Accept": "application/json",
        }
        result = _sanitize_headers(headers)
        assert result["API-Key"] == "***REDACTED***"
        assert result["Accept"] == "application/json"

    def test_sanitize_x_api_key_header(self):
        """Test that X-API-Key header is redacted."""
        headers = {
            "X-API-Key": "my-secret-api-key",
        }
        result = _sanitize_headers(headers)
        assert result["X-API-Key"] == "***REDACTED***"

    def test_sanitize_case_insensitive(self):
        """Test that header name comparison is case-insensitive."""
        headers = {
            "AUTHORIZATION": "Bearer token",
            "authorization": "Bearer token2",
        }
        result = _sanitize_headers(headers)
        assert result["AUTHORIZATION"] == "***REDACTED***"
        assert result["authorization"] == "***REDACTED***"

    def test_sanitize_preserves_safe_headers(self):
        """Test that non-sensitive headers are preserved."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://example.com",
            "X-Title": "My App",
        }
        result = _sanitize_headers(headers)
        assert result == headers

    def test_sanitize_empty_headers(self):
        """Test sanitizing empty headers dictionary."""
        result = _sanitize_headers({})
        assert result == {}


class TestExtractTokenUsage:
    """Test the _extract_token_usage function."""

    def test_extract_from_valid_response(self):
        """Test extracting tokens from valid response."""
        response = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }

        result = _extract_token_usage(response)

        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] == 50
        assert result["total_tokens"] == 150

    def test_extract_from_empty_usage(self):
        """Test extracting tokens when usage is empty."""
        response = {"usage": {}}

        result = _extract_token_usage(response)

        assert result["prompt_tokens"] is None
        assert result["completion_tokens"] is None
        assert result["total_tokens"] is None

    def test_extract_from_missing_usage(self):
        """Test extracting tokens when usage is missing."""
        response = {}

        result = _extract_token_usage(response)

        assert result["prompt_tokens"] is None
        assert result["completion_tokens"] is None
        assert result["total_tokens"] is None

    def test_extract_partial_usage(self):
        """Test extracting tokens with partial usage data."""
        response = {
            "usage": {
                "prompt_tokens": 100,
                # completion_tokens missing
                "total_tokens": 150,
            }
        }

        result = _extract_token_usage(response)

        assert result["prompt_tokens"] == 100
        assert result["completion_tokens"] is None
        assert result["total_tokens"] == 150


class TestTracedLLMCall:
    """Test the traced_llm_call function."""

    def test_traced_call_success(self, monkeypatch):
        """Test successful traced LLM call."""
        # Disable tracing for simpler testing
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
        mock_response.raise_for_status = Mock()

        with patch("tracing.requests.post", return_value=mock_response):
            result = traced_llm_call(
                api_url="https://api.test.com",
                headers={"Authorization": "Bearer test"},
                payload={"model": "test", "messages": []},
                model="test-model",
            )

        assert result["response"] is not None
        assert result["metadata"].success is True
        assert result["metadata"].model == "test-model"
        assert result["metadata"].latency_ms is not None
        assert result["metadata"].total_tokens == 15

    def test_traced_call_network_error(self, monkeypatch):
        """Test traced LLM call with network error."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        import requests

        with patch("tracing.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

            result = traced_llm_call(
                api_url="https://api.test.com",
                headers={"Authorization": "Bearer test"},
                payload={"model": "test", "messages": []},
                model="test-model",
            )

        assert result["response"] is None
        assert result["metadata"].success is False
        assert "Failed to connect" in result["metadata"].error

    def test_traced_call_timeout(self, monkeypatch):
        """Test traced LLM call with timeout."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        import requests

        with patch("tracing.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

            result = traced_llm_call(
                api_url="https://api.test.com",
                headers={"Authorization": "Bearer test"},
                payload={"model": "test", "messages": []},
                model="test-model",
                timeout=30,
            )

        assert result["response"] is None
        assert result["metadata"].success is False
        assert "timed out" in result["metadata"].error

    def test_traced_call_captures_latency(self, monkeypatch):
        """Test that traced call captures latency."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        mock_response = Mock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "Hi"}}]}
        mock_response.raise_for_status = Mock()

        with patch("tracing.requests.post", return_value=mock_response):
            result = traced_llm_call(
                api_url="https://api.test.com",
                headers={},
                payload={},
                model="test",
            )

        # Latency should be captured (very small in tests but > 0)
        assert result["metadata"].latency_ms is not None
        assert result["metadata"].latency_ms >= 0


class TestTraceOpDecorator:
    """Test the trace_op decorator."""

    def test_decorator_returns_function_when_disabled(self, monkeypatch):
        """Test decorator returns original function when tracing disabled."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        @trace_op("test_func")
        def my_function(x):
            return x * 2

        # Should still work
        assert my_function(5) == 10

    def test_decorator_without_name(self, monkeypatch):
        """Test decorator works without explicit name."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        @trace_op()
        def another_function():
            return "result"

        assert another_function() == "result"


class TestInitTracing:
    """Test the init_tracing function."""

    def test_init_when_disabled(self, monkeypatch):
        """Test init returns False when tracing disabled."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        result = init_tracing()
        assert result is False

    def test_init_with_custom_project(self, monkeypatch):
        """Test init uses custom project name."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")  # Disable for test

        # Even when disabled, should return False
        result = init_tracing(project_name="custom-project")
        assert result is False


class TestPrintTracingStatus:
    """Test the print_tracing_status function."""

    def test_prints_status(self, capsys, monkeypatch):
        """Test that status is printed correctly."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")
        monkeypatch.setenv("WEAVE_PROJECT", "test-project")

        print_tracing_status()

        captured = capsys.readouterr()
        assert "WEAVE TRACING STATUS" in captured.out
        assert "Weave Available" in captured.out
        assert "Tracing Enabled" in captured.out
        assert "Initialized" in captured.out
        assert "Project" in captured.out


class TestCortexIntegration:
    """Test Cortex integration with tracing."""

    def test_cortex_call_llm_with_tracing_disabled(
        self, temp_hive_dir, mock_env_vars, sample_api_response, monkeypatch
    ):
        """Test Cortex.call_llm works with tracing disabled."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        from cortex import Cortex

        cortex = Cortex(temp_hive_dir)

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = sample_api_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            result = cortex.call_llm("Test prompt")

            assert result is not None
            assert "summary" in result

    def test_cortex_call_llm_prints_metrics(
        self, temp_hive_dir, mock_env_vars, capsys, monkeypatch
    ):
        """Test Cortex.call_llm prints latency and token metrics."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        from cortex import Cortex

        cortex = Cortex(temp_hive_dir)

        response_with_usage = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "summary": "Test",
                                "blocked_tasks": [],
                                "state_updates": [],
                                "new_projects": [],
                                "notes": "",
                            }
                        )
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }

        with patch("tracing.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = response_with_usage
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            cortex.call_llm("Test prompt")

            captured = capsys.readouterr()
            assert "Latency" in captured.out
            assert "Tokens" in captured.out
            assert "150" in captured.out

    def test_cortex_call_llm_handles_api_error(
        self, temp_hive_dir, mock_env_vars, monkeypatch
    ):
        """Test Cortex.call_llm handles API errors gracefully."""
        monkeypatch.setenv("WEAVE_DISABLED", "true")

        from cortex import Cortex

        import requests

        cortex = Cortex(temp_hive_dir)

        with patch("tracing.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

            result = cortex.call_llm("Test prompt")

            assert result is None


class TestWeaveIntegration:
    """Test actual Weave integration when available."""

    @pytest.mark.skipif(not _weave_available, reason="Weave not available")
    def test_weave_op_decorator_applied(self, monkeypatch):
        """Test that weave.op is properly applied when enabled."""
        monkeypatch.delenv("WEAVE_DISABLED", raising=False)

        # Import fresh to ensure decorator is applied
        import importlib
        import tracing

        importlib.reload(tracing)

        # The _traced_llm_call_impl should have weave attributes
        assert hasattr(tracing._traced_llm_call_impl, "__wrapped__") or hasattr(
            tracing._traced_llm_call_impl, "name"
        )
