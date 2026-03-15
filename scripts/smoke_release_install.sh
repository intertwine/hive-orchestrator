#!/bin/bash
#
# Smoke-test built release artifacts through the public CLI install paths.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="${1:-$REPO_ROOT/dist}"

WHEEL_PATH="$(find "$DIST_DIR" -maxdepth 1 -name 'agent_hive-*.whl' | sort -V | tail -n 1)"
if [ -z "$WHEEL_PATH" ]; then
    echo "❌ Error: no built wheel found in $DIST_DIR" >&2
    echo "Run 'make build' first." >&2
    exit 1
fi

TEMP_ROOT="$(mktemp -d)"
cleanup() {
    rm -rf "$TEMP_ROOT"
}
trap cleanup EXIT

run_uv_tool_smoke() {
    local uv_home="$TEMP_ROOT/uv-home"
    local uv_bin_dir="$uv_home/.local/bin"
    local workspace="$TEMP_ROOT/uv-workspace"
    local hive_bin

    mkdir -p "$uv_home" "$uv_bin_dir" "$workspace"
    HOME="$uv_home" UV_TOOL_BIN_DIR="$uv_bin_dir" uv tool install --force --from "$WHEEL_PATH" agent-hive >/dev/null

    hive_bin="$uv_bin_dir/hive"
    "$hive_bin" --version >/dev/null
    "$hive_bin" --path "$workspace" init --json >/dev/null
    "$hive_bin" --path "$workspace" doctor --json >/dev/null
}

run_pipx_smoke() {
    local pipx_home="$TEMP_ROOT/pipx-home"
    local pipx_bin="$TEMP_ROOT/pipx-bin"
    local pipx_man="$TEMP_ROOT/pipx-man"
    local workspace="$TEMP_ROOT/pipx-workspace"
    local python_bin

    mkdir -p "$pipx_home" "$pipx_bin" "$pipx_man" "$workspace"
    python_bin="$(command -v python3 || command -v python)"

    PIPX_HOME="$pipx_home" \
    PIPX_BIN_DIR="$pipx_bin" \
    PIPX_MAN_DIR="$pipx_man" \
    PIPX_DEFAULT_PYTHON="$python_bin" \
    uvx --from pipx pipx install --force "$WHEEL_PATH" >/dev/null

    "$pipx_bin/hive" --version >/dev/null
    "$pipx_bin/hive" --path "$workspace" init --json >/dev/null
    "$pipx_bin/hive" --path "$workspace" doctor --json >/dev/null
}

run_pip_smoke() {
    local venv_dir="$TEMP_ROOT/pip-venv"
    local workspace="$TEMP_ROOT/pip-workspace"

    mkdir -p "$workspace"
    python3 -m venv "$venv_dir"
    "$venv_dir/bin/pip" install "$WHEEL_PATH" >/dev/null

    "$venv_dir/bin/hive" --version >/dev/null
    "$venv_dir/bin/hive" --path "$workspace" init --json >/dev/null
    "$venv_dir/bin/hive" --path "$workspace" doctor --json >/dev/null
}

echo "🔎 Smoke-testing uv tool install..."
run_uv_tool_smoke

echo "🔎 Smoke-testing pip install..."
run_pip_smoke

echo "🔎 Smoke-testing pipx install..."
run_pipx_smoke

echo "✅ Release install smoke checks passed for $(basename "$WHEEL_PATH")"
