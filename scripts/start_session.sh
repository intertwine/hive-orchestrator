#!/bin/bash
#
# Hive v2 Session Bootstrap Script
#
# Usage: ./scripts/start_session.sh <project-id-or-path>
# Example: ./scripts/start_session.sh demo
# Example: ./scripts/start_session.sh projects/demo
#
# This script generates a Hive v2 startup context package for AI agents
# to begin a focused work session on a specific project.
#

set -e

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No project id or path provided${NC}"
    echo "Usage: $0 <project-id-or-path>"
    echo "Example: $0 demo"
    echo "Example: $0 projects/demo"
    exit 1
fi

PROJECT_REF="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="${HIVE_BASE_PATH:-$REPO_ROOT}"

export PROJECT_REF
export WORKSPACE_ROOT

PROJECT_INFO=$(cd "$REPO_ROOT" && uv run python - <<'PY'
import os
from pathlib import Path

from src.hive.store.projects import discover_projects, get_project

root = Path(os.environ["WORKSPACE_ROOT"]).resolve()
project_ref = os.environ["PROJECT_REF"]

candidate = Path(project_ref)
candidate = candidate if candidate.is_absolute() else (root / candidate).resolve()

project = None
if candidate.exists():
    for discovered in discover_projects(root):
        agency_path = discovered.agency_path.resolve()
        if candidate == agency_path or candidate == agency_path.parent:
            project = discovered
            break

if project is None:
    project = get_project(root, project_ref)

print(f"{project.id}\t{project.agency_path.parent.resolve()}")
PY
)

if [ $? -ne 0 ] || [ -z "$PROJECT_INFO" ]; then
    echo -e "${RED}Error: Could not resolve project '$PROJECT_REF'${NC}"
    exit 1
fi

IFS=$'\t' read -r PROJECT_ID PROJECT_DIR <<< "$PROJECT_INFO"
AGENCY_FILE="$PROJECT_DIR/AGENCY.md"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         AGENT HIVE - HIVE V2 SESSION BOOTSTRAP        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Project:${NC} $PROJECT_ID"
echo -e "${GREEN}Path:${NC} $PROJECT_DIR"
echo -e "${GREEN}Workspace:${NC} $WORKSPACE_ROOT"
echo ""

# Generate session context file
SESSION_FILE="$PROJECT_DIR/SESSION_CONTEXT.md"

echo -e "${YELLOW}Generating session context...${NC}"

cd "$REPO_ROOT"
export AGENCY_FILE
export SESSION_FILE
export WORKSPACE_ROOT

uv run python - <<'PY'
import os
from pathlib import Path

from src.dashboard import generate_hive_context

agency_file = Path(os.environ["AGENCY_FILE"]).resolve()
session_file = Path(os.environ["SESSION_FILE"]).resolve()
workspace_root = Path(os.environ["WORKSPACE_ROOT"]).resolve()

context = generate_hive_context(str(agency_file), workspace_root, mode="startup", profile="light")
if not context:
    raise SystemExit("Failed to generate Hive v2 startup context")

session_file.write_text(context, encoding="utf-8")
PY

echo -e "${GREEN}✓ Session context generated: $SESSION_FILE${NC}"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo ""
echo "1. Open $SESSION_FILE"
echo "2. Copy the entire content"
echo "3. Paste it into your AI agent (Claude, Grok, Gemini, etc.)"
echo "4. Let the agent work against the canonical Hive v2 task context"
echo "5. Review the updated `.hive/tasks/` state and projections when done"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Happy Hive v2 session! 🚀${NC}"
