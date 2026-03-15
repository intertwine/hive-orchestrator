"""Projection helpers."""

from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md


def sync_all(path):
    """Sync all generated projection documents."""
    updated = [sync_global_md(path), sync_agents_md(path)]
    updated.extend(sync_agency_md(path))
    return updated


__all__ = ["sync_agency_md", "sync_agents_md", "sync_all", "sync_global_md"]
