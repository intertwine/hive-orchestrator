#!/usr/bin/env python3
"""
Agent Hive Cross-Repository Multi-Agent Pipeline

Orchestrates multiple AI agents across different vendors to analyze,
strategize, and implement improvements to external GitHub repositories.

Architecture: "Relay Race" Pattern
- Each phase uses a different LLM model
- AGENCY.md serves as shared memory between phases
- Each agent reads previous phase output and writes to its section
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

from src.security import (
    safe_load_agency_md,
    safe_dump_agency_md,
)
from src.tracing import traced_llm_call, is_tracing_enabled, init_tracing

# Load environment variables
load_dotenv()


@dataclass
class PhaseConfig:
    """Configuration for a pipeline phase."""
    name: str
    model: str
    system_prompt: str
    output_section: str


@dataclass
class ExternalRepoInfo:
    """Information about an external repository."""
    url: str
    branch: str = "main"
    local_path: Optional[Path] = None
    file_tree: str = ""
    key_files: Dict[str, str] = field(default_factory=dict)


class CrossRepoPipeline:
    """
    Multi-agent pipeline for cross-repository improvements.

    The pipeline executes in three phases:
    1. ANALYST: Analyzes the external repository structure
    2. STRATEGIST: Identifies improvement opportunities
    3. IMPLEMENTER: Generates code changes and submits PR

    Each phase uses a different LLM model, demonstrating vendor-agnostic
    orchestration. Results are written to AGENCY.md as shared memory.
    """

    # Default models for each phase (can be overridden in AGENCY.md)
    DEFAULT_MODELS = {
        "analyst": "anthropic/claude-haiku-4.5",
        "strategist": "google/gemini-2.0-flash-001",
        "implementer": "openai/gpt-4o",
    }

    # Phase configurations with system prompts
    PHASES = {
        "analyze": PhaseConfig(
            name="analyze",
            model="analyst",
            system_prompt="""You are a code analyst examining a repository structure.
Your task is to provide a comprehensive analysis including:
1. Project architecture and technology stack
2. Key files and their purposes
3. Code organization patterns
4. Areas that could benefit from improvement
5. Technical debt or anti-patterns observed

Be thorough but concise. Focus on actionable insights.""",
            output_section="## Phase 1: Analysis",
        ),
        "strategize": PhaseConfig(
            name="strategize",
            model="strategist",
            system_prompt="""You are a technical strategist reviewing a codebase analysis.
Based on the analyst's findings, your task is to:
1. Identify the single most impactful improvement to make
2. Explain why this improvement matters
3. Outline the specific changes needed
4. Consider backward compatibility and risk
5. Estimate complexity (simple/medium/complex)

Choose an improvement that is:
- Meaningful and demonstrates value
- Achievable in a single PR
- Low risk and well-scoped

Be specific about file paths and changes needed.""",
            output_section="## Phase 2: Strategy",
        ),
        "implement": PhaseConfig(
            name="implement",
            model="implementer",
            system_prompt="""You are a senior developer implementing a planned improvement.
Based on the strategy provided, your task is to:
1. Generate the exact code changes needed
2. Provide complete file diffs (unified diff format)
3. Write a clear commit message
4. Create a PR title and description

Output format (use exactly this structure):
```
### Files to Modify

**File: path/to/file.ext**
```diff
--- a/path/to/file.ext
+++ b/path/to/file.ext
@@ -line,count +line,count @@
 context line
-removed line
+added line
 context line
```

### Commit Message
<commit message>

### PR Title
<pr title>

### PR Description
<pr description>
```

Be precise. Generate complete, working code.""",
            output_section="## Phase 3: Implementation",
        ),
    }

    def __init__(
        self,
        project_path: Path,
        base_path: Path = None,
        dry_run: bool = False,
    ):
        """
        Initialize the cross-repo pipeline.

        Args:
            project_path: Path to the project's AGENCY.md file
            base_path: Base path for the hive (defaults to cwd)
            dry_run: If True, don't make actual changes
        """
        self.project_path = Path(project_path)
        self.base_path = Path(base_path or os.getcwd())
        self.dry_run = dry_run

        # API configuration
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        # Will be populated from AGENCY.md
        self.project_data: Optional[Dict[str, Any]] = None
        self.external_repo: Optional[ExternalRepoInfo] = None
        self.models: Dict[str, str] = {}

    def validate_environment(self) -> bool:
        """Validate required environment and tools."""
        if not self.api_key:
            print("ERROR: OPENROUTER_API_KEY not set")
            return False

        # Check if git is available
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=10,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("ERROR: git not available")
            return False

        return True

    def load_project(self) -> bool:
        """Load project configuration from AGENCY.md."""
        try:
            parsed = safe_load_agency_md(self.project_path)
            self.project_data = {
                "metadata": parsed.metadata,
                "content": parsed.content,
            }

            # Extract target repo config
            target_repo = parsed.metadata.get("target_repo", {})
            if not target_repo.get("url"):
                print("ERROR: target_repo.url not specified in AGENCY.md")
                return False

            self.external_repo = ExternalRepoInfo(
                url=target_repo["url"],
                branch=target_repo.get("branch", "main"),
            )

            # Extract model configuration (with defaults)
            models_config = parsed.metadata.get("models", {})
            for phase, default_model in self.DEFAULT_MODELS.items():
                self.models[phase] = models_config.get(phase, default_model)

            return True

        except Exception as e:
            print(f"ERROR loading project: {e}")
            return False

    def clone_external_repo(self) -> bool:
        """Clone the external repository to a temporary directory."""
        if not self.external_repo:
            return False

        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="hive_cross_repo_")
            self.external_repo.local_path = Path(temp_dir)

            print(f"   Cloning {self.external_repo.url}...")
            result = subprocess.run(
                [
                    "git", "clone",
                    "--depth", "1",
                    "--branch", self.external_repo.branch,
                    self.external_repo.url,
                    temp_dir,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                print(f"   ERROR cloning repo: {result.stderr}")
                return False

            print(f"   Cloned to {temp_dir}")
            return True

        except subprocess.TimeoutExpired:
            print("   ERROR: Clone timed out")
            return False
        except Exception as e:
            print(f"   ERROR: {e}")
            return False

    def generate_file_tree(self, max_depth: int = 4) -> str:
        """Generate a text-based file tree of the external repo."""
        if not self.external_repo or not self.external_repo.local_path:
            return ""

        def _tree(directory: Path, prefix: str = "", depth: int = 0) -> str:
            if depth >= max_depth:
                return ""

            tree = ""
            try:
                items = sorted(
                    directory.iterdir(),
                    key=lambda x: (not x.is_dir(), x.name)
                )
                # Filter out common noise
                items = [
                    i for i in items
                    if not i.name.startswith(".")
                    and i.name not in {"node_modules", "__pycache__", "dist", "build", ".git"}
                ]

                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "L-- " if is_last else "|-- "
                    tree += f"{prefix}{current_prefix}{item.name}\n"

                    if item.is_dir() and depth < max_depth - 1:
                        extension = "    " if is_last else "|   "
                        tree += _tree(item, prefix + extension, depth + 1)

            except PermissionError:
                pass

            return tree

        repo_name = Path(self.external_repo.url).stem
        tree = f"{repo_name}/\n"
        tree += _tree(self.external_repo.local_path)
        return tree

    def read_key_files(self) -> Dict[str, str]:
        """Read key files from the external repo."""
        if not self.external_repo or not self.external_repo.local_path:
            return {}

        key_files = {}
        repo_path = self.external_repo.local_path

        # Common key files to read
        files_to_read = [
            "package.json",
            "pyproject.toml",
            "README.md",
            "src/index.ts",
            "src/main.ts",
            "src/index.js",
            "src/main.py",
            "tsconfig.json",
            ".github/workflows/*.yml",
        ]

        for pattern in files_to_read:
            if "*" in pattern:
                # Glob pattern
                for file_path in repo_path.glob(pattern):
                    if file_path.is_file():
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            relative_path = file_path.relative_to(repo_path)
                            if len(content) > 15000:
                                content = content[:15000] + "\n\n... (truncated)"
                            key_files[str(relative_path)] = content
                        except (UnicodeDecodeError, PermissionError):
                            pass
            else:
                file_path = repo_path / pattern
                if file_path.exists() and file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        if len(content) > 15000:
                            content = content[:15000] + "\n\n... (truncated)"
                        key_files[pattern] = content
                    except (UnicodeDecodeError, PermissionError):
                        pass

        return key_files

    def read_all_source_files(self) -> Dict[str, str]:
        """Read all source files for the implementer phase."""
        if not self.external_repo or not self.external_repo.local_path:
            return {}

        source_files = {}
        repo_path = self.external_repo.local_path

        # Source file extensions
        extensions = (".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java")

        for ext in extensions:
            for file_path in repo_path.rglob(f"*{ext}"):
                # Skip common noise directories
                if any(part in file_path.parts for part in
                       ("node_modules", "__pycache__", "dist", "build", ".git")):
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8")
                    relative_path = file_path.relative_to(repo_path)
                    # Limit file size
                    if len(content) > 20000:
                        content = content[:20000] + "\n\n... (truncated)"
                    source_files[str(relative_path)] = content
                except (UnicodeDecodeError, PermissionError):
                    pass

        return source_files

    def call_llm(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Optional[str]:
        """Call an LLM via OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agent-hive/orchestrator",
            "X-Title": "Agent Hive Cross-Repo Pipeline",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 8000,
        }

        try:
            result = traced_llm_call(
                api_url=self.api_url,
                headers=headers,
                payload=payload,
                model=model,
                timeout=120,
            )

            metadata = result["metadata"]
            response = result["response"]

            if metadata.latency_ms:
                print(f"      Latency: {metadata.latency_ms:.0f}ms")
            if metadata.total_tokens:
                print(f"      Tokens: {metadata.total_tokens}")

            if not metadata.success:
                print(f"      ERROR: {metadata.error}")
                return None

            if not response or "choices" not in response:
                print("      ERROR: Invalid response")
                return None

            return response["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"      ERROR calling LLM: {e}")
            return None

    def update_agency_md(self, section: str, content: str) -> bool:
        """Update a specific section in AGENCY.md."""
        if self.dry_run:
            print(f"   [DRY RUN] Would update section: {section}")
            return True

        try:
            parsed = safe_load_agency_md(self.project_path)

            # Find and update the section
            full_content = parsed.content
            section_header = section

            if section_header in full_content:
                # Find the next section header or end of content
                section_start = full_content.find(section_header)
                section_content_start = section_start + len(section_header)

                # Find next ## header
                next_section = full_content.find("\n## ", section_content_start)
                if next_section == -1:
                    # No next section, replace to end
                    new_content = (
                        full_content[:section_content_start] +
                        "\n\n" + content + "\n"
                    )
                else:
                    # Replace up to next section
                    new_content = (
                        full_content[:section_content_start] +
                        "\n\n" + content + "\n" +
                        full_content[next_section:]
                    )
            else:
                # Section doesn't exist, append it
                new_content = full_content + f"\n\n{section_header}\n\n{content}\n"

            # Update metadata
            parsed.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

            # Write back
            with open(self.project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, new_content))

            return True

        except Exception as e:
            print(f"   ERROR updating AGENCY.md: {e}")
            return False

    def add_agent_note(self, agent_name: str, note: str) -> bool:
        """Add a timestamped note to the Agent Notes section."""
        if self.dry_run:
            return True

        try:
            parsed = safe_load_agency_md(self.project_path)
            content = parsed.content

            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            note_entry = f"\n- **{timestamp} - {agent_name}**: {note}"

            if "## Agent Notes" in content:
                content = content.replace(
                    "## Agent Notes",
                    f"## Agent Notes{note_entry}",
                    1
                )
            else:
                content += f"\n\n## Agent Notes{note_entry}"

            with open(self.project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, content))

            return True

        except Exception as e:
            print(f"   ERROR adding agent note: {e}")
            return False

    def update_phase(self, new_phase: str) -> bool:
        """Update the current phase in AGENCY.md metadata."""
        if self.dry_run:
            return True

        try:
            parsed = safe_load_agency_md(self.project_path)
            parsed.metadata["phase"] = new_phase
            parsed.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

            with open(self.project_path, "w", encoding="utf-8") as f:
                f.write(safe_dump_agency_md(parsed.metadata, parsed.content))

            return True

        except Exception as e:
            print(f"   ERROR updating phase: {e}")
            return False

    def run_analyst_phase(self) -> bool:
        """Run the analyst phase."""
        phase_config = self.PHASES["analyze"]
        model = self.models["analyst"]

        print("\n   Phase 1: ANALYSIS")
        print(f"   Model: {model}")
        print("   " + "-" * 40)

        # Generate file tree
        print("   Generating file tree...")
        file_tree = self.generate_file_tree()
        self.external_repo.file_tree = file_tree

        # Read key files
        print("   Reading key files...")
        key_files = self.read_key_files()
        self.external_repo.key_files = key_files

        # Build context for analyst
        files_content = "\n\n".join([
            f"### {path}\n```\n{content}\n```"
            for path, content in key_files.items()
        ])

        user_prompt = f"""Analyze this repository:

## Repository URL
{self.external_repo.url}

## File Structure
```
{file_tree}
```

## Key Files
{files_content}

Provide a comprehensive analysis of this codebase."""

        # Call analyst LLM
        print("   Calling analyst LLM...")
        analysis = self.call_llm(model, phase_config.system_prompt, user_prompt)

        if not analysis:
            print("   ERROR: Analyst phase failed")
            return False

        # Update AGENCY.md
        print("   Updating AGENCY.md...")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        output = f"*Generated by {model} at {timestamp}*\n\n{analysis}"

        if not self.update_agency_md(phase_config.output_section, output):
            return False

        self.add_agent_note("Analyst", f"Completed analysis using {model}")
        self.update_phase("strategize")

        print("   Analysis complete!")
        return True

    def run_strategist_phase(self) -> bool:
        """Run the strategist phase."""
        phase_config = self.PHASES["strategize"]
        model = self.models["strategist"]

        print("\n   Phase 2: STRATEGY")
        print(f"   Model: {model}")
        print("   " + "-" * 40)

        # Load current AGENCY.md to get analyst output
        parsed = safe_load_agency_md(self.project_path)
        content = parsed.content

        # Extract Phase 1 analysis
        analysis_start = content.find("## Phase 1: Analysis")
        analysis_end = content.find("## Phase 2:")
        if analysis_end == -1:
            analysis_end = content.find("## Phase 3:")
        if analysis_end == -1:
            analysis_end = content.find("## Agent Notes")
        if analysis_end == -1:
            analysis_end = len(content)

        analyst_output = content[analysis_start:analysis_end].strip()

        user_prompt = f"""Based on this codebase analysis, identify the most impactful improvement:

{analyst_output}

## Repository URL
{self.external_repo.url}

Remember: Choose a single, well-scoped improvement that can be implemented in one PR.
Be specific about the exact changes needed."""

        # Call strategist LLM
        print("   Calling strategist LLM...")
        strategy = self.call_llm(model, phase_config.system_prompt, user_prompt)

        if not strategy:
            print("   ERROR: Strategist phase failed")
            return False

        # Update AGENCY.md
        print("   Updating AGENCY.md...")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        output = f"*Generated by {model} at {timestamp}*\n\n{strategy}"

        if not self.update_agency_md(phase_config.output_section, output):
            return False

        self.add_agent_note("Strategist", f"Identified improvement using {model}")
        self.update_phase("implement")

        print("   Strategy complete!")
        return True

    def run_implementer_phase(self) -> bool:
        """Run the implementer phase."""
        phase_config = self.PHASES["implement"]
        model = self.models["implementer"]

        print("\n   Phase 3: IMPLEMENTATION")
        print(f"   Model: {model}")
        print("   " + "-" * 40)

        # Load current AGENCY.md to get strategy
        parsed = safe_load_agency_md(self.project_path)
        content = parsed.content

        # Extract Phase 2 strategy
        strategy_start = content.find("## Phase 2: Strategy")
        strategy_end = content.find("## Phase 3:")
        if strategy_end == -1:
            strategy_end = content.find("## Agent Notes")
        if strategy_end == -1:
            strategy_end = len(content)

        strategist_output = content[strategy_start:strategy_end].strip()

        # Also get all source files for context
        print("   Reading all source files...")
        source_files = self.read_all_source_files()

        files_content = "\n\n".join([
            f"### {path}\n```\n{content}\n```"
            for path, content in list(source_files.items())[:20]  # Limit to 20 files
        ])

        user_prompt = f"""Implement this improvement:

{strategist_output}

## Current Source Files
{files_content}

Generate complete, working code changes in unified diff format.
Include commit message, PR title, and PR description."""

        # Call implementer LLM
        print("   Calling implementer LLM...")
        implementation = self.call_llm(model, phase_config.system_prompt, user_prompt)

        if not implementation:
            print("   ERROR: Implementer phase failed")
            return False

        # Update AGENCY.md
        print("   Updating AGENCY.md...")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        output = f"*Generated by {model} at {timestamp}*\n\n{implementation}"

        if not self.update_agency_md(phase_config.output_section, output):
            return False

        self.add_agent_note("Implementer", f"Generated implementation using {model}")
        self.update_phase("review")

        print("   Implementation complete!")
        return True

    def cleanup(self):
        """Clean up temporary files."""
        if self.external_repo and self.external_repo.local_path:
            try:
                shutil.rmtree(self.external_repo.local_path)
                print("\n   Cleaned up temp directory")
            except Exception:
                pass

    def run(self, phases: List[str] = None) -> bool:
        """
        Run the cross-repo pipeline.

        Args:
            phases: List of phases to run (default: all phases)

        Returns:
            True on success
        """
        print("=" * 60)
        print(" AGENT HIVE CROSS-REPO PIPELINE")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Project: {self.project_path}")
        print(f"Dry Run: {self.dry_run}")
        print()

        # Validate environment
        print(" Validating environment...")
        if not self.validate_environment():
            return False
        print("   OK")

        # Load project
        print("\n Loading project configuration...")
        if not self.load_project():
            return False
        print(f"   Target: {self.external_repo.url}")
        print(f"   Branch: {self.external_repo.branch}")
        print("   Models:")
        for phase, model in self.models.items():
            print(f"     - {phase}: {model}")

        # Clone external repo
        print("\n Cloning external repository...")
        if not self.clone_external_repo():
            return False

        # Determine which phases to run
        if phases is None:
            current_phase = self.project_data["metadata"].get("phase", "analyze")
            all_phases = ["analyze", "strategize", "implement"]
            start_idx = all_phases.index(current_phase) if current_phase in all_phases else 0
            phases = all_phases[start_idx:]

        # Run phases
        try:
            print("\n Running pipeline phases...")

            if "analyze" in phases:
                if not self.run_analyst_phase():
                    return False

            if "strategize" in phases:
                if not self.run_strategist_phase():
                    return False

            if "implement" in phases:
                if not self.run_implementer_phase():
                    return False

        finally:
            self.cleanup()

        print("\n" + "=" * 60)
        print(" PIPELINE COMPLETE")
        print("=" * 60)
        print(f"\nResults written to: {self.project_path}")
        print("\nNext steps:")
        print("  1. Review the generated implementation in AGENCY.md")
        print("  2. Fork the target repository")
        print("  3. Apply the diffs manually or use the PR submitter")
        print("  4. Submit a PR to the target repository")

        return True


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Hive Cross-Repository Multi-Agent Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline on a project
  python -m src.cross_repo_pipeline projects/external/my-project/AGENCY.md

  # Run only specific phases
  python -m src.cross_repo_pipeline projects/external/my-project/AGENCY.md --phases analyze

  # Dry run (no changes)
  python -m src.cross_repo_pipeline projects/external/my-project/AGENCY.md --dry-run
        """,
    )

    parser.add_argument(
        "project",
        type=str,
        help="Path to the project's AGENCY.md file",
    )

    parser.add_argument(
        "--phases",
        "-p",
        type=str,
        nargs="+",
        choices=["analyze", "strategize", "implement"],
        help="Specific phases to run (default: all remaining phases)",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Preview without making changes",
    )

    parser.add_argument(
        "--base-path",
        "-b",
        type=str,
        default=None,
        help="Base path for the hive (default: current directory)",
    )

    return parser.parse_args()


def main():
    """CLI entry point."""
    args = parse_args()

    # Initialize tracing if enabled
    if is_tracing_enabled():
        init_tracing()

    pipeline = CrossRepoPipeline(
        project_path=Path(args.project),
        base_path=Path(args.base_path) if args.base_path else None,
        dry_run=args.dry_run,
    )

    success = pipeline.run(phases=args.phases)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
