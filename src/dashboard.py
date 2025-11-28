#!/usr/bin/env python3
"""
Agent Hive Dashboard - Streamlit UI

Provides human oversight and control over the Agent Hive orchestration system.
"""

import os
import glob
from pathlib import Path
from datetime import datetime
import streamlit as st
import frontmatter
from cortex import Cortex


def load_project(project_path: str):
    """Load and parse an AGENCY.md file."""
    try:
        with open(project_path, "r", encoding="utf-8") as f:
            post = frontmatter.load(f)
            return {
                "path": project_path,
                "metadata": post.metadata,
                "content": post.content,
                "raw": frontmatter.dumps(post),
            }
    except Exception as e:
        st.error(f"Error loading project: {e}")
        return None


def discover_projects(base_path: Path):
    """Find all AGENCY.md files in the projects directory."""
    projects_dir = base_path / "projects"
    if not projects_dir.exists():
        return []

    agency_files = glob.glob(str(projects_dir / "*" / "AGENCY.md"))
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
    if current_depth >= max_depth:
        return ""

    tree = ""
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        items = [i for i in items if not i.name.startswith(".") and i.name != "__pycache__"]

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            tree += f"{prefix}{current_prefix}{item.name}\n"

            if item.is_dir() and current_depth < max_depth - 1:
                extension = "    " if is_last else "│   "
                tree += generate_file_tree(item, prefix + extension, max_depth, current_depth + 1)

    except PermissionError:
        # Ignore directories/files that cannot be accessed due to permissions
        pass

    return tree


def generate_deep_work_context(project_path: str, base_path: Path):
    """Generate a comprehensive context package for Deep Work sessions."""

    project_data = load_project(project_path)
    if not project_data:
        return None

    project_dir = Path(project_path).parent
    project_id = project_data["metadata"].get("project_id", "unknown")

    # Build the context
    context = f"""# DEEP WORK SESSION CONTEXT
# Project: {project_id}
# Generated: {datetime.utcnow().isoformat()}

---

## YOUR ROLE

You are an AI agent entering a Deep Work session for the Agent Hive project: **{project_id}**.

Your responsibilities:
1. Read and understand the AGENCY.md file below
2. Work on the assigned tasks
3. Update the AGENCY.md frontmatter to reflect your progress
4. Add notes about your work in the "Agent Notes" section
5. Mark yourself as the owner while working (set `owner` field to your model name)
6. Set `blocked: true` if you need human intervention or another agent

---

## AGENCY.md CONTENT

{project_data['raw']}

---

## PROJECT FILE STRUCTURE

{generate_file_tree(project_dir)}

---

## AVAILABLE COMMANDS

- Update AGENCY.md frontmatter fields (status, blocked, priority, etc.)
- Create new files in the project directory
- Read existing files
- Add timestamped notes to the "Agent Notes" section

---

## HANDOFF PROTOCOL

Before ending your session:
1. Update all completed tasks (mark with [x])
2. Update `last_updated` timestamp in frontmatter
3. Add a note describing what you accomplished
4. Set `owner: null` if you're done, or keep it set if you'll continue later
5. Set `blocked: true` with `blocking_reason` if you need help

---

## BOOTSTRAP COMPLETE

You may now begin working on the project. Start by analyzing the current state and identifying the highest priority task you can complete.
"""

    return context


def main():
    """Main dashboard application."""

    st.set_page_config(page_title="Agent Hive Dashboard", page_icon="🧠", layout="wide")

    # Determine base path
    base_path = Path(os.getenv("HIVE_BASE_PATH", os.getcwd()))

    st.title("🧠 Agent Hive Dashboard")
    st.caption("Vendor-Agnostic Agent Orchestration OS")

    # Sidebar: Project list and actions
    with st.sidebar:
        st.header("🗂️ Projects")

        projects = discover_projects(base_path)

        if projects:
            project_options = {
                f"{p['metadata'].get('project_id', 'unknown')} ({p['metadata'].get('status', 'unknown')})": p[
                    "path"
                ]
                for p in projects
            }
            selected_project_key = st.selectbox(
                "Select a project", options=list(project_options.keys())
            )
            selected_project_path = project_options[selected_project_key]
        else:
            st.warning("No projects found in `projects/` directory")
            selected_project_path = None

        st.divider()

        st.header("⚙️ Actions")

        if st.button("🧠 Run Cortex", type="primary", use_container_width=True):
            with st.spinner("Running Cortex..."):
                cortex = Cortex(str(base_path))
                success = cortex.run()
                if success:
                    st.success("Cortex run completed!")
                    st.rerun()
                else:
                    st.error("Cortex run failed. Check console for details.")

        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

        st.divider()

        st.header("📊 System Status")

        # Load GLOBAL.md
        global_file = base_path / "GLOBAL.md"
        if global_file.exists():
            with open(global_file, "r", encoding="utf-8") as f:
                global_post = frontmatter.load(f)
                last_run = global_post.metadata.get("last_cortex_run", "Never")
                if last_run and last_run != "Never":
                    try:
                        last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        last_run = last_run.strftime("%Y-%m-%d %H:%M UTC")
                    except ValueError:
                        # If the date string is malformed, keep the original value
                        pass
                st.metric("Last Cortex Run", last_run)
                st.metric("Total Projects", len(projects))

        st.divider()

        # Dependency Overview
        st.header("🔗 Dependencies")
        sidebar_cortex = Cortex(str(base_path))
        dep_summary = sidebar_cortex.get_dependency_summary()

        if dep_summary["has_cycles"]:
            st.error(f"⚠️ {len(dep_summary['cycles'])} cycle(s) detected!")

        blocked_count = sum(1 for p in dep_summary["projects"] if p["effectively_blocked"])
        ready_count = sum(
            1
            for p in dep_summary["projects"]
            if not p["effectively_blocked"] and p["status"] == "active"
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Blocked", blocked_count)
        with col2:
            st.metric("Ready", ready_count)

    # Create cortex instance for dependency analysis
    cortex = Cortex(str(base_path))

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

                    # Check blocking status
                    blocking_info = cortex.is_blocked(metadata.get("project_id", "unknown"))
                    if blocking_info["is_blocked"]:
                        st.warning("⚠️ This project is effectively blocked")
                        for reason in blocking_info["reasons"]:
                            st.markdown(f"- {reason}")

            # Main content
            st.divider()
            st.markdown(project_data["content"])

            st.divider()

            # Deep Work section
            st.subheader("🚀 Deep Work Session")
            st.write(
                "Generate a comprehensive context package for an AI agent to work on this project."
            )

            col1, col2 = st.columns([3, 1])

            with col2:
                if st.button("Generate Context", type="primary", use_container_width=True):
                    context = generate_deep_work_context(selected_project_path, base_path)
                    if context:
                        st.session_state["deep_work_context"] = context

            if "deep_work_context" in st.session_state:
                st.text_area(
                    "Deep Work Context (copy and paste this to your AI agent)",
                    value=st.session_state["deep_work_context"],
                    height=400,
                    key="context_output",
                )

                st.info(
                    "💡 Copy the above context and paste it into your AI agent (Claude, Grok, Gemini, etc.) to start a Deep Work session."
                )

    else:
        st.info("👈 Select a project from the sidebar to view details")

        st.divider()

        st.subheader("🎯 Getting Started")
        st.markdown(
            """
        **Agent Hive** is a vendor-agnostic orchestration OS for autonomous AI agents.

        ### Quick Start

        1. **Set up your environment**
           ```bash
           uv sync
           export OPENROUTER_API_KEY="your-key-here"
           ```

        2. **Run the Cortex** (orchestration engine)
           ```bash
           uv run python src/cortex.py
           ```

        3. **Create a new project**
           - Create a folder in `projects/your-project-name/`
           - Add an `AGENCY.md` file using the same format as `projects/demo/AGENCY.md`

        4. **Launch Deep Work sessions**
           - Select a project from the sidebar
           - Click "Generate Context"
           - Copy the context and paste it to your AI agent

        ### Architecture

        - **AGENCY.md**: Shared memory for each project (human + machine readable)
        - **GLOBAL.md**: System-wide context and state
        - **Cortex**: Autonomous orchestration engine (runs every 4 hours via GitHub Actions)
        - **Dashboard**: This UI for human oversight

        ### Learn More

        Check the README.md for full documentation.
        """
        )


if __name__ == "__main__":
    main()
