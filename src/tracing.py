#!/usr/bin/env python3
"""
Weave Tracing Integration for Agent Hive

This module provides observability for LLM calls using Weights & Biases Weave.
Weave automatically tracks LLM calls, costs, latencies, and token usage.

Configuration:
    Environment Variables:
        WANDB_API_KEY: Your Weights & Biases API key (required for remote logging)
        WEAVE_PROJECT: Project name for Weave (default: "agent-hive")
        WEAVE_DISABLED: Set to "true" to disable Weave tracing

Usage:
    from src.tracing import init_tracing, traced_llm_call

    # Initialize at application startup
    init_tracing()

    # Use traced_llm_call for LLM API calls
    result = traced_llm_call(
        api_url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        payload=payload,
        model="anthropic/claude-haiku-4.5"
    )
"""

import os
import functools
import time
from typing import Any, Callable, Dict, Optional, TypeVar
from datetime import datetime, timezone

import requests

# Type variable for generic function wrapping
F = TypeVar("F", bound=Callable[..., Any])

# Global state for tracing
_tracing_initialized = False
_weave_available = False

# Try to import weave
try:
    import weave

    _weave_available = True
except ImportError:
    weave = None  # type: ignore
    _weave_available = False


def is_tracing_enabled() -> bool:
    """Check if Weave tracing is enabled.

    Returns:
        True if Weave is available and not explicitly disabled.
    """
    if not _weave_available:
        return False

    disabled = os.getenv("WEAVE_DISABLED", "false").lower()
    return disabled not in ("true", "1", "yes")


def init_tracing(project_name: Optional[str] = None) -> bool:
    """Initialize Weave tracing for the application.

    This should be called once at application startup. If Weave is not
    available or is disabled, this function is a no-op.

    Args:
        project_name: Optional project name. Defaults to WEAVE_PROJECT env var
                     or "agent-hive".

    Returns:
        True if tracing was initialized, False otherwise.
    """
    global _tracing_initialized  # pylint: disable=global-statement

    if _tracing_initialized:
        return True

    if not is_tracing_enabled():
        return False

    project = project_name or os.getenv("WEAVE_PROJECT", "agent-hive")

    try:
        weave.init(project)
        _tracing_initialized = True
        print(f"✓ Weave tracing initialized (project: {project})")
        return True
    except Exception as e:  # pylint: disable=broad-except
        print(f"⚠ Could not initialize Weave tracing: {e}")
        return False


def get_tracing_status() -> Dict[str, Any]:
    """Get the current status of Weave tracing.

    Returns:
        Dictionary with tracing status information.
    """
    return {
        "weave_available": _weave_available,
        "tracing_enabled": is_tracing_enabled(),
        "tracing_initialized": _tracing_initialized,
        "project": os.getenv("WEAVE_PROJECT", "agent-hive"),
        "disabled_by_env": os.getenv("WEAVE_DISABLED", "false").lower() in ("true", "1", "yes"),
    }


def trace_op(name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to trace a function with Weave.

    This is a wrapper around weave.op that gracefully degrades if Weave
    is not available or is disabled.

    Args:
        name: Optional name for the traced operation.

    Returns:
        Decorated function.

    Example:
        @trace_op("my_operation")
        def my_function():
            pass
    """

    def decorator(func: F) -> F:
        if not is_tracing_enabled():
            return func

        # Apply weave.op decorator
        traced_func = weave.op(func)
        if name:
            traced_func.name = name

        return traced_func  # type: ignore

    return decorator


class LLMCallMetadata:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """Metadata for LLM API calls.

    This is a simple data class that captures metrics from LLM API calls
    including timing, token usage, and success/failure status.
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        model: str,
        api_url: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
    ):
        self.model = model
        self.api_url = api_url
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.latency_ms = latency_ms
        self.success = success
        self.error = error
        self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "model": self.model,
            "api_url": self.api_url,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error,
            "timestamp": self.timestamp,
        }


def _sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Sanitize headers for tracing by redacting sensitive values.

    This prevents API keys and other secrets from being logged to Weave traces.

    Args:
        headers: The original headers dictionary.

    Returns:
        A new dictionary with sensitive values redacted.
    """
    sensitive_keys = {"authorization", "api-key", "x-api-key", "bearer"}
    return {
        k: "***REDACTED***" if k.lower() in sensitive_keys else v
        for k, v in headers.items()
    }


def _extract_token_usage(response_json: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """Extract token usage from API response.

    Args:
        response_json: The JSON response from the LLM API.

    Returns:
        Dictionary with prompt_tokens, completion_tokens, total_tokens.
    """
    # Check if response_json is a dictionary before calling .get()
    if not isinstance(response_json, dict):
        return {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }

    usage = response_json.get("usage", {})
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def traced_llm_call(
    api_url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    model: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Make a traced LLM API call.

    This function wraps the HTTP call to an LLM API with Weave tracing,
    capturing request/response details, token usage, and latency.

    Args:
        api_url: The URL of the LLM API endpoint.
        headers: HTTP headers for the request.
        payload: The JSON payload for the request.
        model: The model identifier being called.
        timeout: Request timeout in seconds.

    Returns:
        Dictionary with:
            - response: The parsed JSON response (or None on error)
            - metadata: LLMCallMetadata instance with call details
            - raw_response: The raw requests.Response object

    Raises:
        Does not raise exceptions - errors are captured in metadata.
    """
    # If tracing is enabled, use the traced version with sanitized headers for logging
    if is_tracing_enabled() and _tracing_initialized:
        # Sanitize headers for tracing to avoid logging API keys
        sanitized_headers = _sanitize_headers(headers)
        return _traced_llm_call_impl(
            api_url, sanitized_headers, payload, model, timeout, _original_headers=headers
        )
    return _untraced_llm_call_impl(api_url, headers, payload, model, timeout)


def _untraced_llm_call_impl(
    api_url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    model: str,
    timeout: int = 60,
) -> Dict[str, Any]:
    """Implementation of LLM call without tracing."""
    start_time = time.time()
    response = None
    response_json = None
    error_msg = None
    success = True

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        response_json = response.json()
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        success = False
    except Exception as e:  # pylint: disable=broad-except
        error_msg = str(e)
        success = False

    latency_ms = (time.time() - start_time) * 1000

    # Extract token usage if available
    token_usage = _extract_token_usage(response_json) if response_json else {}

    metadata = LLMCallMetadata(
        model=model,
        api_url=api_url,
        prompt_tokens=token_usage.get("prompt_tokens"),
        completion_tokens=token_usage.get("completion_tokens"),
        total_tokens=token_usage.get("total_tokens"),
        latency_ms=latency_ms,
        success=success,
        error=error_msg,
    )

    return {
        "response": response_json,
        "metadata": metadata,
        "raw_response": response,
    }


# Create the traced implementation only if weave is available
if _weave_available:

    @weave.op(name="llm_call")
    def _traced_llm_call_impl(
        api_url: str,
        headers: Dict[str, str],  # Sanitized headers for tracing (logged by Weave)
        payload: Dict[str, Any],
        model: str,
        timeout: int = 60,
        _original_headers: Optional[Dict[str, str]] = None,  # Original headers for actual request
    ) -> Dict[str, Any]:
        """Traced implementation of LLM call.

        Note: The 'headers' parameter contains sanitized headers (API keys redacted)
        which is what Weave will log. The '_original_headers' contains the actual
        headers used for the API request.
        """
        # Use original headers for the actual request, fall back to sanitized if not provided
        actual_headers = _original_headers if _original_headers else headers
        return _untraced_llm_call_impl(api_url, actual_headers, payload, model, timeout)
else:
    # Fallback if weave is not available
    def _traced_llm_call_impl(
        api_url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        model: str,
        timeout: int = 60,
        _original_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Fallback implementation when weave is not available."""
        actual_headers = _original_headers if _original_headers else headers
        return _untraced_llm_call_impl(api_url, actual_headers, payload, model, timeout)


def traced_cortex_run(func: F) -> F:
    """Decorator to trace a full Cortex run.

    This decorator wraps the Cortex.run() method to provide end-to-end
    tracing of the orchestration cycle.

    Args:
        func: The function to trace.

    Returns:
        Traced function.
    """
    if not is_tracing_enabled():
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _tracing_initialized and _weave_available:
            # Use weave.op for the wrapper
            traced = weave.op(func)
            traced.name = "cortex_run"
            return traced(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper  # type: ignore


def traced_analysis(func: F) -> F:
    """Decorator to trace analysis prompt building.

    Args:
        func: The function to trace.

    Returns:
        Traced function.
    """
    if not is_tracing_enabled():
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _tracing_initialized and _weave_available:
            traced = weave.op(func)
            traced.name = "build_analysis_prompt"
            return traced(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper  # type: ignore


# Convenience function to check status
def print_tracing_status():
    """Print the current tracing status to stdout."""
    status = get_tracing_status()
    print("=" * 40)
    print("WEAVE TRACING STATUS")
    print("=" * 40)
    print(f"  Weave Available: {status['weave_available']}")
    print(f"  Tracing Enabled: {status['tracing_enabled']}")
    print(f"  Initialized:     {status['tracing_initialized']}")
    print(f"  Project:         {status['project']}")
    print(f"  Disabled by Env: {status['disabled_by_env']}")
    print("=" * 40)
