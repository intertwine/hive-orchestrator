"""Regression checks for launch-facing v2 wording."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_agent_harness_docs_use_manager_loop_by_default():
    """High-traffic harness docs should teach the manager loop first."""
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    assert "hive console home --json" in agents
    assert "hive next --json" in agents
    assert "hive work <task-id> --owner <your-name> --json" in agents
    assert "hive finish <run-id> --json" in agents
    assert "Checkout-only helpers in this repo are for maintainers." in agents
    assert "hive console home --json" in claude
    assert "hive next --json" in claude
    assert "hive work <task-id> --owner <your-name> --json" in claude
    assert "hive finish <run-id> --json" in claude
    assert "Repo checkout helpers are for maintainers" in claude


def test_historical_project_docs_frame_v2_as_the_current_model():
    """Narrative project docs should not present Cortex-era architecture as current guidance."""
    beads = (REPO_ROOT / "projects" / "beads-adoption" / "AGENCY.md").read_text(encoding="utf-8")
    hive_mcp = (REPO_ROOT / "projects" / "hive-mcp" / "AGENCY.md").read_text(encoding="utf-8")
    coordination = (
        REPO_ROOT / "projects" / "agent-coordination" / "AGENCY.md"
    ).read_text(encoding="utf-8")

    assert "Historical note" in beads
    assert "live product model is the `.hive/` substrate" in beads
    assert "current thin v2 adapter" in hive_mcp
    assert "Current integrations should treat `.hive/` as canonical" in hive_mcp
    assert "Historical note" in coordination
    assert "task claims on canonical `.hive/tasks/*.md`" in coordination


def test_public_prompt_packs_describe_v2_not_cortex():
    """Launch-facing prompt packs should match the current product story."""
    getting_started = (
        REPO_ROOT / "articles" / "prompts" / "06-getting-started.md"
    ).read_text(encoding="utf-8")
    long_horizon = (
        REPO_ROOT / "articles" / "prompts" / "01-solving-the-long-horizon-agent-problem.md"
    ).read_text(encoding="utf-8")
    coordination = (
        REPO_ROOT / "articles" / "prompts" / "03-multi-agent-coordination-without-chaos.md"
    ).read_text(encoding="utf-8")
    skills = (
        REPO_ROOT / "articles" / "prompts" / "05-skills-and-protocols.md"
    ).read_text(encoding="utf-8")

    assert "OpenRouter API" not in getting_started
    assert "run Cortex" not in getting_started
    assert "task cards, run artifacts, and memory notes" in long_horizon
    assert "canonical claims for the default flow" in coordination
    assert "OWNER:" not in coordination
    assert "HIVE TASK FLOW" in skills
    assert "claim_project" not in skills


def test_generated_article_manifests_match_the_v2_story():
    """Generated image manifests should not drift back to the Cortex-era narrative."""
    coordination_manifest = (
        REPO_ROOT
        / "articles"
        / "images"
        / "multi-agent-coordination-without-chaos"
        / "manifest.json"
    ).read_text(encoding="utf-8")
    getting_started_manifest = (
        REPO_ROOT / "articles" / "images" / "getting-started" / "manifest.json"
    ).read_text(encoding="utf-8")
    skills_manifest = (
        REPO_ROOT / "articles" / "images" / "skills-and-protocols" / "manifest.json"
    ).read_text(encoding="utf-8")
    weave_manifest = (
        REPO_ROOT / "articles" / "images" / "weave-tracing" / "manifest.json"
    ).read_text(encoding="utf-8")

    assert "canonical claims for the default flow" in coordination_manifest
    assert "Cortex Orchestration" not in coordination_manifest
    assert "OWNER:" not in coordination_manifest
    assert "OpenRouter API" not in getting_started_manifest
    assert "run Cortex" not in getting_started_manifest
    assert "claim_project" not in skills_manifest
    assert "generic model-provider API" in weave_manifest
    assert "Cortex, Dashboard, Dispatcher" not in weave_manifest
