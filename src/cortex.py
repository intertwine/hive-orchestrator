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
from datetime import datetime
from typing import List, Dict, Any, Optional
import frontmatter
import requests
from dotenv import load_dotenv

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
        """Read and parse GLOBAL.md file."""
        if not self.global_file.exists():
            print(f"❌ ERROR: GLOBAL.md not found at {self.global_file}")
            return None

        try:
            with open(self.global_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                return {
                    'metadata': post.metadata,
                    'content': post.content,
                    'path': str(self.global_file)
                }
        except Exception as e:
            print(f"❌ ERROR reading GLOBAL.md: {e}")
            return None

    def discover_projects(self) -> List[Dict[str, Any]]:
        """Discover all projects with AGENCY.md files."""
        projects = []

        if not self.projects_dir.exists():
            print(f"⚠️  WARNING: Projects directory not found at {self.projects_dir}")
            return projects

        agency_files = glob.glob(str(self.projects_dir / "*" / "AGENCY.md"))

        for agency_file in agency_files:
            try:
                with open(agency_file, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    projects.append({
                        'path': agency_file,
                        'project_id': post.metadata.get('project_id', 'unknown'),
                        'metadata': post.metadata,
                        'content': post.content
                    })
            except Exception as e:
                print(f"⚠️  WARNING: Could not parse {agency_file}: {e}")

        return projects

    def has_unresolved_blockers(self, project: Dict[str, Any],
                                 all_projects: List[Dict[str, Any]]) -> bool:
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
        metadata = project.get('metadata', {})
        dependencies = metadata.get('dependencies', {})
        blocked_by = dependencies.get('blocked_by', [])

        if not blocked_by:
            return False

        # Build a lookup of project statuses
        project_statuses = {
            p['project_id']: p['metadata'].get('status', 'unknown')
            for p in all_projects
        }

        # Check if any blocking project is not completed
        for blocker_id in blocked_by:
            blocker_status = project_statuses.get(blocker_id)
            if blocker_status is None:
                # Unknown blocker - treat as unresolved (conservative)
                return True
            if blocker_status != 'completed':
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
            metadata = project.get('metadata', {})

            # Check basic readiness criteria
            status = metadata.get('status', '')
            blocked = metadata.get('blocked', False)
            owner = metadata.get('owner')

            if status != 'active':
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
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'count': len(ready_projects),
            'projects': [
                {
                    'project_id': p['project_id'],
                    'path': p['path'],
                    'priority': p['metadata'].get('priority', 'medium'),
                    'tags': p['metadata'].get('tags', []),
                }
                for p in ready_projects
            ]
        }
        return json.dumps(output, indent=2)

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
            priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            sorted_projects = sorted(
                ready_projects,
                key=lambda p: priority_order.get(
                    p['metadata'].get('priority', 'medium'), 2
                )
            )

            for project in sorted_projects:
                meta = project['metadata']
                priority = meta.get('priority', 'medium')
                tags = ', '.join(meta.get('tags', []))
                priority_icon = {
                    'critical': '!!!',
                    'high': '!! ',
                    'medium': '!  ',
                    'low': '   '
                }.get(priority, '   ')

                lines.append(f"{priority_icon} {project['project_id']}")
                lines.append(f"    Priority: {priority}")
                if tags:
                    lines.append(f"    Tags: {tags}")
                lines.append(f"    Path: {project['path']}")
                lines.append("")

        lines.append("=" * 60)
        return '\n'.join(lines)

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

    def build_analysis_prompt(self, global_ctx: Dict, projects: List[Dict]) -> str:
        """Build the prompt for the LLM to analyze system state."""

        prompt = f"""You are the Cortex of Agent Hive, an orchestration operating system.

Your task is to analyze the current state of all projects and identify:
1. Blocked tasks that need attention
2. New project requests in GLOBAL.md
3. State updates needed in AGENCY.md files
4. Priority recommendations

# GLOBAL CONTEXT

## Metadata
{json.dumps(global_ctx['metadata'], indent=2)}

## Content
{global_ctx['content']}

# PROJECTS

"""

        for i, project in enumerate(projects, 1):
            prompt += f"""
## Project {i}: {project['project_id']}

### Metadata
{json.dumps(project['metadata'], indent=2)}

### Content
{project['content']}

---
"""

        prompt += """

# YOUR TASK

Analyze the above information and respond with a JSON object containing:

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

        return prompt

    def call_llm(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call the LLM via OpenRouter API."""

        if not self.api_key:
            print("❌ ERROR: Cannot call LLM without OPENROUTER_API_KEY")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agent-hive/orchestrator",
            "X-Title": "Agent Hive Cortex"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }

        try:
            print(f"🧠 Calling LLM ({self.model})...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            # Defensive checks for response structure
            choices = result.get('choices')
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                print("❌ ERROR: Unexpected API response structure "
                      f"(missing or empty 'choices'): {result}")
                return None

            message = choices[0].get('message') if isinstance(choices[0], dict) else None
            if not message or 'content' not in message:
                print("❌ ERROR: Unexpected API response structure "
                      f"(missing 'message' or 'content'): {result}")
                return None

            llm_response = message['content']

            # Try to parse as JSON
            # Remove markdown code blocks if present
            llm_response = llm_response.strip()
            if llm_response.startswith('```'):
                lines = llm_response.split('\n')
                llm_response = '\n'.join(lines[1:-1])

            return json.loads(llm_response)

        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR calling OpenRouter API: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ ERROR parsing LLM response as JSON: {e}")
            print(f"Response was: {llm_response[:200]}...")
            return None
        except Exception as e:
            print(f"❌ ERROR in LLM call: {e}")
            return None

    def apply_state_updates(self, updates: List[Dict[str, Any]]) -> bool:
        """Apply state updates to AGENCY.md files."""

        if not updates:
            print("✅ No state updates needed")
            return True

        print(f"\n📝 Applying {len(updates)} state update(s)...")

        for update in updates:
            try:
                file_path = Path(update['file'])
                if not file_path.is_absolute():
                    file_path = self.base_path / file_path

                # Resolve both paths to absolute, canonical form
                resolved_file_path = file_path.resolve()
                resolved_base_path = self.base_path.resolve()

                # Check that the file is within the base path (prevent path traversal)
                if not str(resolved_file_path).startswith(str(resolved_base_path)):
                    print(f"⚠️  WARNING: File path outside project directory: {resolved_file_path}")
                    continue

                if not resolved_file_path.exists():
                    print(f"⚠️  WARNING: File not found: {resolved_file_path}")
                    continue

                # Use the resolved path for all operations
                file_path = resolved_file_path

                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)

                # Update the frontmatter field
                field = update['field']
                value = update['value']
                post.metadata[field] = value

                # Also update last_updated
                post.metadata['last_updated'] = datetime.utcnow().isoformat() + 'Z'

                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(frontmatter.dumps(post))

                print(f"   ✓ Updated {file_path.name}: {field} = {value}")
                print(f"     Reason: {update.get('reason', 'N/A')}")

            except Exception as e:
                print(f"   ✗ ERROR updating {update['file']}: {e}")
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
            status = project['metadata'].get('status', 'unknown')
            blocked = project['metadata'].get('blocked', False)
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
        blocked = analysis.get('blocked_tasks', [])
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
        new_projects = analysis.get('new_projects', [])
        if new_projects:
            print(f"\n🆕 NEW PROJECT REQUESTS ({len(new_projects)}):")
            for proj in new_projects:
                print(f"\n  Name: {proj['name']}")
                print(f"  Description: {proj['description']}")
                print(f"  Priority: {proj['priority']}")

        # Apply state updates
        updates = analysis.get('state_updates', [])
        if updates:
            print(f"\n📝 STATE UPDATES ({len(updates)}):")
            success = self.apply_state_updates(updates)
            if not success:
                return False

        # Notes
        notes = analysis.get('notes', '')
        if notes:
            print(f"\n📌 NOTES:\n{notes}")

        # Update GLOBAL.md with last run time
        try:
            with open(self.global_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            post.metadata['last_cortex_run'] = datetime.utcnow().isoformat() + 'Z'
            with open(self.global_file, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            print("\n✅ Updated GLOBAL.md last_cortex_run timestamp")
        except Exception as e:
            print(f"\n⚠️  WARNING: Could not update GLOBAL.md timestamp: {e}")

        print("\n" + "=" * 60)
        print("✅ CORTEX RUN COMPLETED")
        print("=" * 60)

        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Agent Hive Cortex - The Orchestration Operating System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full LLM-based analysis (default)
  python -m src.cortex

  # Find ready work (fast, no LLM)
  python -m src.cortex --ready

  # Output as JSON for programmatic use
  python -m src.cortex --ready --json

  # Specify custom base path
  python -m src.cortex --path /path/to/hive
        """
    )

    parser.add_argument(
        '--ready', '-r',
        action='store_true',
        help='Find ready work (fast, no LLM required)'
    )

    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output in JSON format for programmatic consumption'
    )

    parser.add_argument(
        '--path', '-p',
        type=str,
        default=None,
        help='Base path for the hive (default: current directory)'
    )

    return parser.parse_args()


def main():
    """CLI entry point for Cortex."""
    args = parse_args()

    cortex = Cortex(base_path=args.path)

    if args.ready:
        # Fast path: no LLM required
        success = cortex.run_ready(output_json=args.json)
    else:
        # Full LLM-based analysis
        if args.json:
            print('{"error": "JSON output only supported with --ready flag"}',
                  file=sys.stderr)
            sys.exit(1)
        success = cortex.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
