#!/usr/bin/env python3
"""
Agent Hive Cortex - The Orchestration Operating System

This module acts as the central nervous system for Agent Hive,
reading project state from AGENCY.md files and coordinating
AI agents across different vendors.
"""

import argparse
import os
import sys
import json
import glob
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.security import (
    safe_load_agency_md,
    safe_dump_agency_md,
    build_secure_llm_prompt,
    sanitize_untrusted_content,
    validate_path_within_base,
    MAX_RECURSION_DEPTH,
)
from src.tracing import (
    init_tracing,
    traced_llm_call,
    get_tracing_status,
    is_tracing_enabled,
)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""

    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


# Load environment variables
load_dotenv()


class CortexError(Exception):
    """Base exception for Cortex-related errors."""


class Cortex:
    """
    The Cortex orchestration engine.

    Responsibilities:
    - Read GLOBAL.md and all AGENCY.md files
    - Analyze project states and identify blocked tasks
    - Use LLM to generate state updates
    - Apply updates safely to markdown files
    """

    def __init__(self, base_path: str = None):
        """Initialize the Cortex with a base path."""
        self.base_path = Path(base_path or os.getcwd())
        self.global_file = self.base_path / "GLOBAL.md"
        self.projects_dir = self.base_path / "projects"

        # OpenRouter configuration
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5")

    def validate_environment(self) -> bool:
        """Validate that required environment variables are set."""
        if not self.api_key:
            print("❌ ERROR: OPENROUTER_API_KEY not set in environment")
            print("   Please set it in your .env file or environment variables")
            return False
        return True

    def read_global_context(self) -> Optional[Dict[str, Any]]:
        """Read and parse GLOBAL.md file using safe YAML loading."""
        if not self.global_file.exists():
            print(f"ERROR: GLOBAL.md not found at {self.global_file}")
            return None

        try:
            # Use safe loading to prevent YAML deserialization attacks
            parsed = safe_load_agency_md(self.global_file)
            return {
                "metadata": parsed.metadata,
                "content": parsed.content,
                "path": str(self.global_file),
            }
        except Exception as e:
            print(f"ERROR reading GLOBAL.md: {e}")
            return None

    def discover_projects(self) -> List[Dict[str, Any]]:
        """Discover all projects with AGENCY.md files using safe YAML loading."""
        projects = []

        if not self.projects_dir.exists():
            print(f"WARNING: Projects directory not found at {self.projects_dir}")
            return projects

        agency_files = glob.glob(
            str(self.projects_dir / "**" / "AGENCY.md"), recursive=True
        )

        for agency_file in agency_files:
            try:
                # Use safe loading to prevent YAML deserialization attacks
                parsed = safe_load_agency_md(Path(agency_file))
                projects.append(
                    {
                        "path": agency_file,
                        "project_id": parsed.metadata.get("project_id", "unknown"),
                        "metadata": parsed.metadata,
                        "content": parsed.content,
                    }
                )
            except Exception as e:
                print(f"WARNING: Could not parse {agency_file}: {e}")

        return projects

    def build_dependency_graph(self, projects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build a dependency graph from all projects.

        Returns a graph structure with:
        - nodes: dict mapping project_id -> project metadata
        - edges: dict mapping project_id -> list of project_ids it blocks
        - reverse_edges: dict mapping project_id -> list of project_ids blocking it

        Args:
            projects: List of discovered projects

        Returns:
            Dictionary containing the dependency graph structure
        """
        nodes = {}
        edges = {}  # project_id -> [projects it blocks]
        reverse_edges = {}  # project_id -> [projects that block it]

        # Build nodes
        for project in projects:
            project_id = project["project_id"]
            nodes[project_id] = {
                "status": project["metadata"].get("status", "unknown"),
                "priority": project["metadata"].get("priority", "medium"),
                "owner": project["metadata"].get("owner"),
                "blocked": project["metadata"].get("blocked", False),
                "path": project["path"],
                "dependencies": project["metadata"].get("dependencies", {}),
            }
            edges[project_id] = []
            reverse_edges[project_id] = []

        # Build edges from dependencies
        for project in projects:
            project_id = project["project_id"]
            deps = project["metadata"].get("dependencies", {})

            # blocked_by: these projects must complete before this one
            blocked_by = deps.get("blocked_by", [])
            for blocker_id in blocked_by:
                if blocker_id in nodes:
                    edges[blocker_id].append(project_id)
                    reverse_edges[project_id].append(blocker_id)

            # blocks: this project blocks these projects
            blocks = deps.get("blocks", [])
            for blocked_id in blocks:
                if blocked_id in nodes:
                    edges[project_id].append(blocked_id)
                    if project_id not in reverse_edges.get(blocked_id, []):
                        reverse_edges[blocked_id].append(project_id)

        return {"nodes": nodes, "edges": edges, "reverse_edges": reverse_edges}

    def detect_cycles(self, projects: List[Dict[str, Any]] = None) -> List[List[str]]:
        """
        Detect cycles in the dependency graph using DFS.

        A cycle means circular dependencies that can never be resolved.

        Args:
            projects: Optional list of projects. If None, discovers them.

        Returns:
            List of cycles, where each cycle is a list of project_ids
        """
        if projects is None:
            projects = self.discover_projects()

        graph = self.build_dependency_graph(projects)
        edges = graph["edges"]
        nodes = set(graph["nodes"].keys())

        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str, depth: int = 0) -> bool:
            """DFS to detect cycles, returns True if cycle found."""
            # Prevent DoS via deeply nested graphs
            if depth > MAX_RECURSION_DEPTH:
                print(f"WARNING: Max recursion depth exceeded at node {node}")
                return False

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, depth + 1):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle - extract it from path
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in nodes:
            if node not in visited:
                dfs(node, 0)

        return cycles

    def is_blocked(self, project_id: str, projects: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Check if a project is blocked and provide detailed blocking info.

        This performs full graph traversal to find all blocking reasons:
        - Direct blocking via `blocked` field
        - Blocked by uncompleted dependencies (transitive)
        - Part of a dependency cycle

        Args:
            project_id: The project to check
            projects: Optional list of projects. If None, discovers them.

        Returns:
            Dictionary with blocking status and details:
            {
                'is_blocked': bool,
                'reasons': [list of blocking reasons],
                'blocking_projects': [project_ids that block this],
                'in_cycle': bool,
                'cycle': [project_ids in cycle] if in_cycle
            }
        """
        if projects is None:
            projects = self.discover_projects()

        graph = self.build_dependency_graph(projects)
        result = {
            "is_blocked": False,
            "reasons": [],
            "blocking_projects": [],
            "in_cycle": False,
            "cycle": [],
        }

        # Check if project exists
        if project_id not in graph["nodes"]:
            result["is_blocked"] = True
            result["reasons"].append(f"Project '{project_id}' not found")
            return result

        node = graph["nodes"][project_id]

        # Check 1: Direct blocked flag
        if node.get("blocked", False):
            result["is_blocked"] = True
            result["reasons"].append("Explicitly marked as blocked")

        # Check 2: Uncompleted dependencies (transitive)
        visited = set()
        to_check = list(graph["reverse_edges"].get(project_id, []))

        while to_check:
            dep_id = to_check.pop(0)
            if dep_id in visited:
                continue
            visited.add(dep_id)

            if dep_id not in graph["nodes"]:
                result["is_blocked"] = True
                result["reasons"].append(f"Unknown dependency: {dep_id}")
                result["blocking_projects"].append(dep_id)
                continue

            dep_node = graph["nodes"][dep_id]
            if dep_node["status"] != "completed":
                result["is_blocked"] = True
                result["blocking_projects"].append(dep_id)
                # Also check transitive dependencies
                to_check.extend(graph["reverse_edges"].get(dep_id, []))

        if result["blocking_projects"]:
            result["reasons"].append(
                f"Blocked by uncompleted: {', '.join(result['blocking_projects'])}"
            )

        # Check 3: Cycle detection
        cycles = self.detect_cycles(projects)
        for cycle in cycles:
            if project_id in cycle:
                result["is_blocked"] = True
                result["in_cycle"] = True
                result["cycle"] = cycle
                result["reasons"].append(f"Part of dependency cycle: {' -> '.join(cycle)}")
                break

        return result

    def get_dependency_summary(self, projects: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a summary of the dependency graph for visualization.

        Args:
            projects: Optional list of projects. If None, discovers them.

        Returns:
            Dictionary with dependency summary suitable for visualization
        """
        if projects is None:
            projects = self.discover_projects()

        graph = self.build_dependency_graph(projects)
        cycles = self.detect_cycles(projects)

        summary = {
            "total_projects": len(graph["nodes"]),
            "projects": [],
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
        }

        for project_id, node in graph["nodes"].items():
            blocks = graph["edges"].get(project_id, [])
            blocked_by = graph["reverse_edges"].get(project_id, [])

            # Determine effective status
            blocking_info = self.is_blocked(project_id, projects)

            summary["projects"].append(
                {
                    "project_id": project_id,
                    "status": node["status"],
                    "priority": node["priority"],
                    "owner": node["owner"],
                    "blocked": node["blocked"],
                    "blocks": blocks,
                    "blocked_by": blocked_by,
                    "effectively_blocked": blocking_info["is_blocked"],
                    "blocking_reasons": blocking_info["reasons"],
                    "in_cycle": blocking_info["in_cycle"],
                }
            )

        return summary

    def has_unresolved_blockers(
        self, project: Dict[str, Any], all_projects: List[Dict[str, Any]]
    ) -> bool:
        """
        Check if a project has unresolved blocking dependencies.

        Examines the 'dependencies.blocked_by' field and checks if any
        of those projects are still incomplete (not status='completed').

        Args:
            project: The project to check
            all_projects: All discovered projects for dependency resolution

        Returns:
            True if there are unresolved blockers, False otherwise
        """
        metadata = project.get("metadata", {})
        dependencies = metadata.get("dependencies", {})
        blocked_by = dependencies.get("blocked_by", [])

        if not blocked_by:
            return False

        # Build a lookup of project statuses
        project_statuses = {
            p["project_id"]: p["metadata"].get("status", "unknown") for p in all_projects
        }

        # Check if any blocking project is not completed
        for blocker_id in blocked_by:
            blocker_status = project_statuses.get(blocker_id)
            if blocker_status is None:
                # Unknown blocker - treat as unresolved (conservative)
                return True
            if blocker_status != "completed":
                return True

        return False

    def ready_work(self, projects: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Find projects that are ready for work (no LLM required).

        A project is ready if:
        - status == 'active'
        - blocked == False
        - owner == None (unclaimed)
        - No unresolved blocking dependencies

        Args:
            projects: Optional list of projects. If None, discovers them.

        Returns:
            List of projects ready for an agent to claim
        """
        if projects is None:
            projects = self.discover_projects()

        ready = []
        for project in projects:
            metadata = project.get("metadata", {})

            # Check basic readiness criteria
            status = metadata.get("status", "")
            blocked = metadata.get("blocked", False)
            owner = metadata.get("owner")

            if status != "active":
                continue
            if blocked:
                continue
            if owner is not None:
                continue

            # Check dependency-based blocking
            if self.has_unresolved_blockers(project, projects):
                continue

            ready.append(project)

        return ready

    def format_ready_work_json(self, ready_projects: List[Dict[str, Any]]) -> str:
        """Format ready work as JSON for programmatic consumption."""
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "count": len(ready_projects),
            "projects": [
                {
                    "project_id": p["project_id"],
                    "path": p["path"],
                    "priority": p["metadata"].get("priority", "medium"),
                    "tags": p["metadata"].get("tags", []),
                }
                for p in ready_projects
            ],
        }
        return json.dumps(output, indent=2, cls=DateTimeEncoder)

    def format_ready_work_text(self, ready_projects: List[Dict[str, Any]]) -> str:
        """Format ready work as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("READY WORK")
        lines.append("=" * 60)
        lines.append(f"Timestamp: {datetime.utcnow().isoformat()}")
        lines.append(f"Found {len(ready_projects)} project(s) ready for work")
        lines.append("")

        if not ready_projects:
            lines.append("No projects ready. All are either:")
            lines.append("  - Not active (status != 'active')")
            lines.append("  - Blocked (blocked == true)")
            lines.append("  - Already claimed (owner != null)")
            lines.append("  - Waiting on dependencies")
        else:
            # Sort by priority
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_projects = sorted(
                ready_projects,
                key=lambda p: priority_order.get(p["metadata"].get("priority", "medium"), 2),
            )

            for project in sorted_projects:
                meta = project["metadata"]
                priority = meta.get("priority", "medium")
                tags = ", ".join(meta.get("tags", []))
                priority_icon = {
                    "critical": "!!!",
                    "high": "!! ",
                    "medium": "!  ",
                    "low": "   ",
                }.get(priority, "   ")

                lines.append(f"{priority_icon} {project['project_id']}")
                lines.append(f"    Priority: {priority}")
                if tags:
                    lines.append(f"    Tags: {tags}")
                lines.append(f"    Path: {project['path']}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def run_ready(self, output_json: bool = False) -> bool:
        """
        Run ready work detection (no LLM, fast).

        Args:
            output_json: If True, output JSON format; otherwise human-readable

        Returns:
            True on success
        """
        projects = self.discover_projects()
        ready_projects = self.ready_work(projects)

        if output_json:
            print(self.format_ready_work_json(ready_projects))
        else:
            print(self.format_ready_work_text(ready_projects))

        return True

    def format_deps_json(self, summary: Dict[str, Any]) -> str:
        """Format dependency summary as JSON."""
        output = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "total_projects": summary["total_projects"],
            "has_cycles": summary["has_cycles"],
            "cycles": summary["cycles"],
            "projects": summary["projects"],
        }
        return json.dumps(output, indent=2, cls=DateTimeEncoder)

    def format_deps_text(self, summary: Dict[str, Any]) -> str:
        """Format dependency summary as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("DEPENDENCY GRAPH")
        lines.append("=" * 60)
        lines.append(f"Timestamp: {datetime.utcnow().isoformat()}")
        lines.append(f"Total Projects: {summary['total_projects']}")
        lines.append("")

        # Cycle warning
        if summary["has_cycles"]:
            lines.append("!!! CYCLES DETECTED !!!")
            for cycle in summary["cycles"]:
                lines.append(f"    {' -> '.join(cycle)}")
            lines.append("")

        # Sort projects: blocked first, then by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_projects = sorted(
            summary["projects"],
            key=lambda p: (
                0 if p["effectively_blocked"] else 1,
                priority_order.get(p["priority"], 2),
            ),
        )

        # Group by status
        blocked_projects = [p for p in sorted_projects if p["effectively_blocked"]]
        ready_projects = [p for p in sorted_projects if not p["effectively_blocked"]]

        if blocked_projects:
            lines.append("BLOCKED PROJECTS:")
            lines.append("-" * 40)
            for proj in blocked_projects:
                status_icon = "!!!" if proj["in_cycle"] else "***"
                lines.append(f"{status_icon} {proj['project_id']}")
                lines.append(f"    Status: {proj['status']}")
                if proj["blocked_by"]:
                    lines.append(f"    Blocked by: {', '.join(proj['blocked_by'])}")
                if proj["blocking_reasons"]:
                    for reason in proj["blocking_reasons"]:
                        lines.append(f"    Reason: {reason}")
                lines.append("")

        if ready_projects:
            lines.append("UNBLOCKED PROJECTS:")
            lines.append("-" * 40)
            for proj in ready_projects:
                owner_str = f" (owner: {proj['owner']})" if proj["owner"] else ""
                lines.append(f"    {proj['project_id']} [{proj['status']}]{owner_str}")
                if proj["blocks"]:
                    lines.append(f"      Blocks: {', '.join(proj['blocks'])}")
            lines.append("")

        # Dependency visualization
        lines.append("DEPENDENCY TREE:")
        lines.append("-" * 40)

        # Find root projects (not blocked by anything)
        roots = [p for p in summary["projects"] if not p["blocked_by"]]
        visited = set()

        def print_tree(project_id: str, indent: int = 0):
            """Recursively print dependency tree."""
            if project_id in visited:
                lines.append("  " * indent + f"[{project_id}] (circular ref)")
                return
            visited.add(project_id)

            proj = next((p for p in summary["projects"] if p["project_id"] == project_id), None)
            if not proj:
                lines.append("  " * indent + f"[{project_id}] (unknown)")
                return

            status_char = {"completed": "+", "active": "*", "blocked": "!", "pending": "-"}.get(
                proj["status"], "?"
            )

            lines.append("  " * indent + f"[{status_char}] {project_id}")

            for blocked_id in proj["blocks"]:
                print_tree(blocked_id, indent + 1)

        for root in roots:
            print_tree(root["project_id"])

        lines.append("")
        lines.append("Legend: [+] completed  [*] active  [!] blocked  [-] pending")
        lines.append("=" * 60)

        return "\n".join(lines)

    def run_deps(self, output_json: bool = False) -> bool:
        """
        Display dependency graph (no LLM, fast).

        Args:
            output_json: If True, output JSON format; otherwise human-readable

        Returns:
            True on success
        """
        projects = self.discover_projects()
        summary = self.get_dependency_summary(projects)

        if output_json:
            print(self.format_deps_json(summary))
        else:
            print(self.format_deps_text(summary))

        return True

    def build_analysis_prompt(self, global_ctx: Dict, projects: List[Dict]) -> str:
        """
        Build the prompt for the LLM to analyze system state.

        Uses secure prompt construction to prevent injection attacks from
        user-editable AGENCY.md content.
        """
        # Combine all project content for sanitization
        combined_content_parts = []

        # Add global content (sanitized - GLOBAL.md is also user-editable)
        sanitized_global = sanitize_untrusted_content(global_ctx['content'])
        combined_content_parts.append(f"# GLOBAL CONTEXT\n{sanitized_global}")

        # Add each project content (sanitized)
        for i, project in enumerate(projects, 1):
            sanitized_content = sanitize_untrusted_content(project['content'])
            combined_content_parts.append(
                f"\n## Project {i}: {project['project_id']}\n{sanitized_content}"
            )

        combined_content = "\n---\n".join(combined_content_parts)

        # Build combined metadata
        combined_metadata = {
            "global": global_ctx['metadata'],
            "projects": [
                {
                    "project_id": p['project_id'],
                    "path": p['path'],
                    **p['metadata']
                }
                for p in projects
            ]
        }

        # Use secure prompt builder with additional task instructions
        additional_context = """
Your specific tasks are:
1. Identify blocked tasks that need attention
2. Detect new project requests in GLOBAL.md
3. Suggest state updates needed in AGENCY.md files
4. Provide priority recommendations

Respond with a JSON object containing:
{
  "summary": "Brief summary of system state",
  "blocked_tasks": [
    {
      "project_id": "project_id",
      "task": "description of blocked task",
      "reason": "why it's blocked",
      "recommendation": "suggested action"
    }
  ],
  "state_updates": [
    {
      "file": "path/to/AGENCY.md",
      "field": "frontmatter field to update",
      "value": "new value",
      "reason": "why this update is needed"
    }
  ],
  "new_projects": [
    {
      "name": "project name",
      "description": "what it should do",
      "priority": "high|medium|low"
    }
  ],
  "notes": "Any other observations or recommendations"
}

Return ONLY valid JSON, no markdown formatting or additional text.
"""

        return build_secure_llm_prompt(
            metadata=combined_metadata,
            content=combined_content,
            additional_context=additional_context
        )

    def call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call the LLM via OpenRouter API with optional Weave tracing.

        This method uses the tracing module to capture LLM call metrics
        including latency, token usage, and success/failure status.
        """

        if not self.api_key:
            print("❌ ERROR: Cannot call LLM without OPENROUTER_API_KEY")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agent-hive/orchestrator",
            "X-Title": "Agent Hive Cortex",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4000,
        }

        try:
            print(f"🧠 Calling LLM ({self.model})...")

            # Use traced LLM call for observability
            call_result = traced_llm_call(
                api_url=self.api_url,
                headers=headers,
                payload=payload,
                model=self.model,
                timeout=60,
            )

            metadata = call_result["metadata"]
            result = call_result["response"]

            # Log tracing metadata if available
            if metadata.latency_ms:
                print(f"   ⏱ Latency: {metadata.latency_ms:.0f}ms")
            if metadata.total_tokens:
                print(f"   📊 Tokens: {metadata.total_tokens}")

            # Check for errors in the traced call
            if not metadata.success:
                print(f"❌ ERROR calling OpenRouter API: {metadata.error}")
                return None

            if result is None:
                print("❌ ERROR: No response received from API")
                return None

            # Defensive checks for response structure
            choices = result.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                print(
                    "❌ ERROR: Unexpected API response structure "
                    f"(missing or empty 'choices'): {result}"
                )
                return None

            message = choices[0].get("message") if isinstance(choices[0], dict) else None
            if not message or "content" not in message:
                print(
                    "❌ ERROR: Unexpected API response structure "
                    f"(missing 'message' or 'content'): {result}"
                )
                return None

            llm_response = message["content"]

            # Try to parse as JSON
            # Remove markdown code blocks if present
            llm_response = llm_response.strip()
            if llm_response.startswith("```"):
                lines = llm_response.split("\n")
                llm_response = "\n".join(lines[1:-1])

            return json.loads(llm_response)

        except json.JSONDecodeError as e:
            print(f"❌ ERROR parsing LLM response as JSON: {e}")
            print(f"Response was: {llm_response[:200]}...")
            return None
        except Exception as e:
            print(f"❌ ERROR in LLM call: {e}")
            return None

    def apply_state_updates(self, updates: List[Dict[str, Any]]) -> bool:
        """Apply state updates to AGENCY.md files using safe YAML handling."""

        if not updates:
            print("No state updates needed")
            return True

        print(f"\nApplying {len(updates)} state update(s)...")

        for update in updates:
            try:
                file_path = Path(update["file"])
                if not file_path.is_absolute():
                    file_path = self.base_path / file_path

                # Validate path is within base directory (prevent path traversal)
                if not validate_path_within_base(file_path, self.base_path):
                    print(f"WARNING: File path outside project directory: {file_path}")
                    continue

                resolved_file_path = file_path.resolve()

                if not resolved_file_path.exists():
                    print(f"WARNING: File not found: {resolved_file_path}")
                    continue

                # Use the resolved path for all operations
                file_path = resolved_file_path

                # Read the file using safe loading
                parsed = safe_load_agency_md(file_path)

                # Update the frontmatter field
                field = update["field"]
                value = update["value"]
                parsed.metadata[field] = value

                # Also update last_updated
                parsed.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

                # Write back using safe dump
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(safe_dump_agency_md(parsed.metadata, parsed.content))

                print(f"   Updated {file_path.name}: {field} = {value}")
                print(f"     Reason: {update.get('reason', 'N/A')}")

            except Exception as e:
                print(f"   ERROR updating {update['file']}: {e}")
                return False

        return True

    def run(self) -> bool:
        """Main Cortex execution loop."""

        print("=" * 60)
        print("🧠 AGENT HIVE CORTEX")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Base Path: {self.base_path}")
        print()

        # Validate environment
        if not self.validate_environment():
            return False

        # Read global context
        print("📖 Reading GLOBAL.md...")
        global_ctx = self.read_global_context()
        if not global_ctx:
            return False
        print("   ✓ Loaded global context")

        # Discover projects
        print("\n🔍 Discovering projects...")
        projects = self.discover_projects()
        print(f"   ✓ Found {len(projects)} project(s)")
        for project in projects:
            status = project["metadata"].get("status", "unknown")
            blocked = project["metadata"].get("blocked", False)
            blocked_indicator = "🔒" if blocked else "✓"
            print(f"     {blocked_indicator} {project['project_id']} ({status})")

        # Build analysis prompt
        print("\n🔨 Building analysis prompt...")
        prompt = self.build_analysis_prompt(global_ctx, projects)
        print(f"   ✓ Prompt built ({len(prompt)} chars)")

        # Call LLM
        print("\n🌐 Analyzing system state...")
        analysis = self.call_llm(prompt)
        if not analysis:
            return False

        # Display results
        print("\n" + "=" * 60)
        print("📊 ANALYSIS RESULTS")
        print("=" * 60)
        print(f"\n{analysis.get('summary', 'No summary provided')}\n")

        # Blocked tasks
        blocked = analysis.get("blocked_tasks", [])
        if blocked:
            print(f"🔒 BLOCKED TASKS ({len(blocked)}):")
            for task in blocked:
                print(f"\n  Project: {task['project_id']}")
                print(f"  Task: {task['task']}")
                print(f"  Reason: {task['reason']}")
                print(f"  Recommendation: {task['recommendation']}")
        else:
            print("✅ No blocked tasks")

        # New projects
        new_projects = analysis.get("new_projects", [])
        if new_projects:
            print(f"\n🆕 NEW PROJECT REQUESTS ({len(new_projects)}):")
            for proj in new_projects:
                print(f"\n  Name: {proj['name']}")
                print(f"  Description: {proj['description']}")
                print(f"  Priority: {proj['priority']}")

        # Apply state updates
        updates = analysis.get("state_updates", [])
        if updates:
            print(f"\n📝 STATE UPDATES ({len(updates)}):")
            success = self.apply_state_updates(updates)
            if not success:
                return False

        # Notes
        notes = analysis.get("notes", "")
        if notes:
            print(f"\n📌 NOTES:\n{notes}")

        # Update GLOBAL.md with last run time (using safe loading)
        try:
            parsed = safe_load_agency_md(self.global_file)
            parsed.metadata["last_cortex_run"] = datetime.utcnow().isoformat() + "Z"
            with open(self.global_file, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, parsed.content))
            print("\nUpdated GLOBAL.md last_cortex_run timestamp")
        except Exception as e:
            print(f"\nWARNING: Could not update GLOBAL.md timestamp: {e}")

        print("\n" + "=" * 60)
        print("✅ CORTEX RUN COMPLETED")
        print("=" * 60)

        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Cortex - The Orchestration Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full LLM-based analysis (default)
  python -m src.cortex

  # Find ready work (fast, no LLM)
  python -m src.cortex --ready

  # Show dependency graph
  python -m src.cortex --deps

  # Output as JSON for programmatic use
  python -m src.cortex --ready --json
  python -m src.cortex --deps --json

  # Specify custom base path
  python -m src.cortex --path /path/to/hive
        """,
    )

    parser.add_argument(
        "--ready", "-r", action="store_true", help="Find ready work (fast, no LLM required)"
    )

    parser.add_argument(
        "--deps", "-d", action="store_true", help="Show dependency graph (fast, no LLM required)"
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in JSON format for programmatic consumption",
    )

    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default=None,
        help="Base path for the hive (default: current directory)",
    )

    return parser.parse_args()


def main():
    """CLI entry point for Cortex."""
    args = parse_args()

    # Initialize Weave tracing (optional - degrades gracefully if not configured)
    if is_tracing_enabled():
        init_tracing()
        tracing_status = get_tracing_status()
        if tracing_status["tracing_initialized"]:
            print(f"📈 Weave tracing active (project: {tracing_status['project']})")

    cortex = Cortex(base_path=args.path)

    if args.ready:
        # Fast path: no LLM required
        success = cortex.run_ready(output_json=args.json)
    elif args.deps:
        # Dependency graph: no LLM required
        success = cortex.run_deps(output_json=args.json)
    else:
        # Full LLM-based analysis
        if args.json:
            print('{"error": "JSON output only supported with --ready or --deps"}', file=sys.stderr)
            sys.exit(1)
        success = cortex.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
