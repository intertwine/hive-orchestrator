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

if ! PROJECT_JSON=$(cd "$REPO_ROOT" && uv run hive --path "$WORKSPACE_ROOT" --json project show "$PROJECT_REF" 2>/dev/null); then
    echo -e "${RED}Error: Could not resolve project '$PROJECT_REF'${NC}"
    exit 1
fi

if [ -z "$PROJECT_JSON" ]; then
    echo -e "${RED}Error: Could not resolve project '$PROJECT_REF'${NC}"
    exit 1
fi

PROJECT_INFO="$(PROJECT_JSON="$PROJECT_JSON" uv run python - <<'PY'
import json
import os

payload = json.loads(os.environ["PROJECT_JSON"])
project = payload["project"]
print(f"{project['id']}\t{project['path']}")
PY
)"
IFS=$'\t' read -r PROJECT_ID AGENCY_FILE <<< "$PROJECT_INFO"
PROJECT_DIR="$(dirname "$AGENCY_FILE")"

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
if ! uv run hive --path "$WORKSPACE_ROOT" context startup --project "$PROJECT_REF" --output "$SESSION_FILE" >/dev/null; then
    echo -e "${RED}Error: Could not generate startup context for '$PROJECT_REF'${NC}"
    exit 1
fi

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
