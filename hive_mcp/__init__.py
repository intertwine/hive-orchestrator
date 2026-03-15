"""Public top-level Hive MCP package for installed distributions."""

from importlib import import_module
import sys

_core = import_module("src.hive_mcp")
sys.modules[__name__] = _core
