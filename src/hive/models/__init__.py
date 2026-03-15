"""Data models for Hive 2.0."""

from src.hive.models.program import ProgramRecord
from src.hive.models.project import ProjectRecord
from src.hive.models.run import RunRecord
from src.hive.models.task import TaskRecord

Program = ProgramRecord
Project = ProjectRecord
Task = TaskRecord

__all__ = [
    "Program",
    "ProgramRecord",
    "Project",
    "ProjectRecord",
    "RunRecord",
    "Task",
    "TaskRecord",
]
