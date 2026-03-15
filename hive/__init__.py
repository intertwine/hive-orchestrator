"""Public top-level Hive package for installed distributions."""

from importlib import import_module
import sys

_core = import_module("src.hive")
sys.modules[__name__] = _core
