#!/bin/bash
#
# Hive v2 Session Bootstrap Script
#
# Usage: ./scripts/start_session.sh <project_path>
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
    echo -e "${RED}Error: No project path provided${NC}"
    echo "Usage: $0 <project_path>"
    echo "Example: $0 projects/demo"
    exit 1
fi

PROJECT_PATH="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKSPACE_ROOT="${HIVE_BASE_PATH:-$REPO_ROOT}"

if [[ "$PROJECT_PATH" = /* ]]; then
    PROJECT_DIR="$PROJECT_PATH"
else
    PROJECT_DIR="$WORKSPACE_ROOT/$PROJECT_PATH"
fi

AGENCY_FILE="$PROJECT_DIR/AGENCY.md"

# Validate project path
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}Error: Project directory does not exist: $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$AGENCY_FILE" ]; then
    echo -e "${RED}Error: AGENCY.md not found in $PROJECT_DIR${NC}"
    exit 1
fi

# Get project ID from AGENCY.md
PROJECT_ID=$(grep "project_id:" "$AGENCY_FILE" | head -1 | sed 's/project_id: *//' | tr -d '\r')

# Validate that PROJECT_ID was found
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: 'project_id:' field not found in $AGENCY_FILE${NC}"
    exit 1
fi

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
