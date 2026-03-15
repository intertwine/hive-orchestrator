#!/usr/bin/env python3
"""
Hive Dashboard - Streamlit UI

Provides human oversight and control over the Hive 2.0 workspace.

Security Note: This dashboard uses safe YAML loading to prevent deserialization
attacks from malicious AGENCY.md content.
"""

import os
import glob
from pathlib import Path
from datetime import datetime
import streamlit as st
from src.hive.context_bundle import build_context_bundle, generate_file_tree as render_file_tree
from src.hive.projections.agency_md import sync_agency_md
from src.hive.projections.agents_md import sync_agents_md
from src.hive.projections.global_md import sync_global_md
from src.hive.scheduler.query import dependency_summary, ready_tasks
from src.hive.store.cache import rebuild_cache
from src.security import safe_load_agency_md, safe_dump_agency_md


def load_project(project_path: str):
    """Load and parse an AGENCY.md file using safe YAML loading."""
    try:
        # Use safe loading to prevent YAML deserialization attacks
        parsed = safe_load_agency_md(Path(project_path))
        return {
            "path": project_path,
            "metadata": parsed.metadata,
            "content": parsed.content,
            "raw": safe_dump_agency_md(parsed.metadata, parsed.content),
        }
    except Exception as e:
        st.error(f"Error loading project: {e}")
        return None


def discover_projects(base_path: Path):
    """Find all AGENCY.md files in the projects directory."""
    projects_dir = base_path / "projects"
    if not projects_dir.exists():
        return []

    agency_files = glob.glob(str(projects_dir / "**" / "AGENCY.md"), recursive=True)
    projects = []

    for agency_file in agency_files:
        project_data = load_project(agency_file)
        if project_data:
            projects.append(project_data)

    return sorted(projects, key=lambda x: x["metadata"].get("project_id", ""))


def generate_file_tree(
    directory: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
):
    """Generate a text-based file tree."""
    return render_file_tree(directory, prefix, max_depth, current_depth)


def generate_deep_work_context(project_path: str, base_path: Path):
    """Generate a v2 startup context package for focused work sessions."""
    return generate_hive_context(project_path, base_path, mode="startup", profile="light")


def list_project_ready_tasks(base_path: Path, project_id: str, limit: int = 10):
    """Return canonical ready tasks for a single project."""
    return ready_tasks(base_path, project_id=project_id, limit=limit)


def sync_hive_views(base_path: Path):
    """Refresh generated projections and the derived cache."""
    sync_global_md(base_path)
    sync_agency_md(base_path)
    sync_agents_md(base_path)
    rebuild_cache(base_path)


def generate_hive_context(
    project_path: str,
    base_path: Path,
    *,
    mode: str = "startup",
    profile: str = "light",
):
    """Generate a formatted Hive v2 startup or handoff context."""

    project_data = load_project(project_path)
    if not project_data:
        return None

    project_id = project_data["metadata"].get("project_id", "unknown")

    try:
        bundle = build_context_bundle(
            base_path,
            project_ref=project_id,
            mode=mode,
            profile=profile,
        )
    except FileNotFoundError as exc:
        st.error(f"Project is not available in Hive v2 context: {exc}")
        return None

    return str(bundle["rendered"])


def main():
    """Main dashboard application."""

    st.set_page_config(page_title="Hive Dashboard", page_icon="🧠", layout="wide")

    # Determine base path
    base_path = Path(os.getenv("HIVE_BASE_PATH", os.getcwd()))
    workspace_dependencies = dependency_summary(base_path)
    dependency_map = {
        entry["project_id"]: entry for entry in workspace_dependencies.get("projects", [])
    }
    workspace_ready_tasks = ready_tasks(base_path)

    st.title("🧠 Hive Dashboard")
    st.caption("CLI-first orchestration for agent workspaces")

    # Sidebar: Project list and actions
    with st.sidebar:
        st.header("🗂️ Projects")

        projects = discover_projects(base_path)

        if projects:
            project_options = {
                (
                    f"{p['metadata'].get('project_id', 'unknown')} "
                    f"({p['metadata'].get('status', 'unknown')})"
                ): p["path"]
                for p in projects
            }
            selected_project_key = st.selectbox(
                "Select a project", options=list(project_options.keys())
            )
            selected_project_path = project_options[selected_project_key]
        else:
            st.warning(
                "No projects found yet. Run `hive quickstart demo --title \"Demo project\"` "
                "from this workspace, then refresh."
            )
            selected_project_path = None

        st.divider()

        st.header("⚙️ Actions")

        if st.button("🔄 Sync Hive Views", type="primary", use_container_width=True):
            with st.spinner("Refreshing projections and cache..."):
                sync_hive_views(base_path)
                st.success("Hive projections and cache refreshed!")
                st.rerun()

        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

        st.divider()

        st.header("📊 System Status")

        # Load GLOBAL.md using safe loading
        global_file = base_path / "GLOBAL.md"
        if global_file.exists():
            try:
                global_parsed = safe_load_agency_md(global_file)
                last_run = global_parsed.metadata.get("last_sync", "Never")
                if last_run and last_run != "Never":
                    try:
                        last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        last_run = last_run.strftime("%Y-%m-%d %H:%M UTC")
                    except ValueError:
                        # If the date string is malformed, keep the original value
                        pass
                st.metric("Last Sync", last_run)
                st.metric("Total Projects", len(projects))
            except Exception as e:
                st.error(f"Error loading GLOBAL.md: {e}")

        st.divider()

        # Dependency Overview
        st.header("🔗 Dependencies")
        if workspace_dependencies["has_cycles"]:
            st.error(f"⚠️ {len(workspace_dependencies['cycles'])} cycle(s) detected!")

        blocked_count = sum(
            1 for project in workspace_dependencies["projects"] if project["effectively_blocked"]
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Blocked", blocked_count)
        with col2:
            st.metric("Ready Tasks", len(workspace_ready_tasks))

    # Main area: Project details
    if selected_project_path:
        project_data = load_project(selected_project_path)

        if project_data:
            metadata = project_data["metadata"]

            # Project header
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.header(f"📁 {metadata.get('project_id', 'Unknown')}")
            with col2:
                status = metadata.get("status", "unknown")
                status_color = {
                    "active": "🟢",
                    "pending": "🟡",
                    "blocked": "🔴",
                    "completed": "✅",
                }.get(status, "⚪")
                st.metric("Status", f"{status_color} {status}")
            with col3:
                priority = metadata.get("priority", "medium")
                st.metric("Priority", priority.upper())

            # Metadata display
            with st.expander("📋 Metadata", expanded=False):
                st.json(metadata)

            # Dependencies section
            deps = metadata.get("dependencies", {})
            if deps:
                with st.expander("🔗 Dependencies", expanded=False):
                    col1, col2 = st.columns(2)

                    with col1:
                        blocked_by = deps.get("blocked_by", [])
                        if blocked_by:
                            st.markdown("**Blocked By:**")
                            for dep in blocked_by:
                                st.markdown(f"- `{dep}`")
                        else:
                            st.markdown("**Blocked By:** None")

                        parent = deps.get("parent")
                        if parent:
                            st.markdown(f"**Parent:** `{parent}`")

                    with col2:
                        blocks = deps.get("blocks", [])
                        if blocks:
                            st.markdown("**Blocks:**")
                            for dep in blocks:
                                st.markdown(f"- `{dep}`")
                        else:
                            st.markdown("**Blocks:** None")

                        related = deps.get("related", [])
                        if related:
                            st.markdown("**Related:**")
                            for dep in related:
                                st.markdown(f"- `{dep}`")

                    blocking_info = dependency_map.get(metadata.get("project_id", "unknown"))
                    if blocking_info and blocking_info["effectively_blocked"]:
                        st.warning("⚠️ This project is effectively blocked")
                        for reason in blocking_info["blocking_reasons"]:
                            st.markdown(f"- {reason}")

            # Main content
            st.divider()
            st.markdown(project_data["content"])

            st.divider()

            st.subheader("✅ Canonical Ready Tasks")
            project_ready_tasks = list_project_ready_tasks(
                base_path, metadata.get("project_id", "unknown"), limit=10
            )
            if project_ready_tasks:
                st.dataframe(
                    [
                        {
                            "Task": task["title"],
                            "Task ID": task["id"],
                            "Priority": task["priority"],
                            "Status": task["status"],
                        }
                        for task in project_ready_tasks
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            elif (base_path / ".hive" / "tasks").exists():
                st.caption("No canonical ready tasks for this project right now.")
            else:
                st.info(
                    "No canonical task substrate found yet. Run `hive quickstart demo --title "
                    "\"Demo project\"` for a full first project, or `hive init` if you want an "
                    "empty workspace."
                )

            st.divider()

            # Context assembly section
            st.subheader("🚀 Hive v2 Context")
            st.write(
                "Generate startup or handoff context from the canonical Hive v2 context pipeline."
            )

            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                profile = st.selectbox(
                    "Context profile",
                    options=["light", "default", "deep"],
                    index=0,
                )
            with col2:
                mode = st.selectbox("Mode", options=["startup", "handoff"], index=0)

            with col3:
                if st.button("Generate Context", type="primary", use_container_width=True):
                    context = generate_hive_context(
                        selected_project_path,
                        base_path,
                        mode=mode,
                        profile=profile,
                    )
                    if context:
                        st.session_state["deep_work_context"] = context

            if "deep_work_context" in st.session_state:
                st.text_area(
                    "Hive v2 Context (copy and paste this to your AI agent)",
                    value=st.session_state["deep_work_context"],
                    height=400,
                    key="context_output",
                )

                st.info(
                    "💡 Copy the above context or regenerate it locally with "
                    f"`hive context {mode} --project {metadata.get('project_id', 'unknown')}`."
                )

    else:
        st.info("👈 Select a project from the sidebar to view details")
        st.markdown(
            """
### First-run path

If this workspace is still empty, the fastest path is:

```bash
hive quickstart demo --title "Demo project"
hive task ready
hive context startup --project demo
```

Use the dashboard after that when you want a visual view of projects, ready tasks, and context.
"""
        )

        st.divider()

        st.subheader("🎯 Getting Started")
        st.markdown(
            """
        **Hive 2.0** keeps machine state in `.hive/` and human context in Markdown.

        ### Quick Start

        1. **Bootstrap the workspace**
           ```bash
           hive quickstart demo --title "Demo project"
           ```

        2. **Inspect ready work**
           ```bash
           hive task ready
           ```

        3. **Generate startup context**
           ```bash
           hive context startup --project demo
           ```

        4. **Use the dashboard when you want a visual view**
           - Select a project from the sidebar
           - Generate a `startup` or `handoff` context
           - Copy the context and paste it to your AI agent

        ### Architecture

        - **.hive/tasks/**: Canonical machine-readable task substrate
        - **AGENCY.md / GLOBAL.md / AGENTS.md**: Human-readable projections
        - **PROGRAM.md**: Project workflow and evaluator policy
        - **Dashboard**: This UI for human oversight and context assembly

        ### Learn More

        Check the README.md for full documentation.
        """
        )


if __name__ == "__main__":
    main()
