"""Static wrapper module for the public ``hive.cli.main`` import path."""

from src.hive.cli.main import main
from src.hive.scaffold import starter_task_specs

__all__ = ["main", "starter_task_specs"]
