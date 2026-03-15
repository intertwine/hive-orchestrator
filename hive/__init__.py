"""Public top-level Hive package for installed distributions."""

from importlib import import_module

_core = import_module("src.hive")

HIVE_VERSION = _core.HIVE_VERSION
__version__ = _core.__version__
__all__ = getattr(_core, "__all__", ["HIVE_VERSION", "__version__"])
__path__ = _core.__path__
