"""Public top-level Hive MCP package for installed distributions."""

from importlib import import_module

_core = import_module("src.hive_mcp")

__version__ = getattr(_core, "__version__", "0.1.0")
__all__ = ["__version__"]
__path__ = _core.__path__
