#!/bin/bash
#
# Smoke-test built release artifacts through the public CLI install paths.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="${1:-$REPO_ROOT/dist}"
RELEASE_PYTHON_VERSION="${RELEASE_PYTHON_VERSION:-3.11}"
DIST_PACKAGE_NAME="${DIST_PACKAGE_NAME:-mellona-hive}"
WHEEL_GLOB="${DIST_PACKAGE_NAME//-/_}-*.whl"

WHEEL_PATH="$(find "$DIST_DIR" -maxdepth 1 -name "$WHEEL_GLOB" | sort -V | tail -n 1)"
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

resolve_release_python_bin() {
    local python_bin

    python_bin="$(uv python find --no-project "$RELEASE_PYTHON_VERSION" 2>/dev/null || true)"
    if [ -n "$python_bin" ]; then
        echo "$python_bin"
        return
    fi

    uv python install "$RELEASE_PYTHON_VERSION" >/dev/null
    python_bin="$(uv python find --no-project "$RELEASE_PYTHON_VERSION" 2>/dev/null || true)"
    if [ -n "$python_bin" ]; then
        echo "$python_bin"
        return
    fi

    echo "❌ Error: could not resolve Python $RELEASE_PYTHON_VERSION for release smoke checks." >&2
    exit 1
}

assert_search_payload() {
    local python_bin="$1"
    local json_path="$2"
    local expected_kind="$3"
    local expected_path_fragment="$4"

    "$python_bin" - "$json_path" "$expected_kind" "$expected_path_fragment" <<'PY'
import json
import sys
from pathlib import Path

json_path, expected_kind, expected_path_fragment = sys.argv[1:4]
payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
results = payload.get("results") if isinstance(payload, dict) else payload
if not isinstance(results, list) or not results:
    raise SystemExit(f"Search payload {json_path} did not include any results.")

matches = [
    item
    for item in results
    if item.get("kind") == expected_kind
    and expected_path_fragment in str(item.get("path", ""))
]
if not matches:
    raise SystemExit(
        f"Expected a {expected_kind} result containing {expected_path_fragment!r} in {json_path}."
    )
if not all(str(item.get("explanation", "")).strip() for item in matches):
    raise SystemExit(f"Matched results in {json_path} were missing explanations.")
PY
}

run_installed_search_smoke() {
    local hive_bin="$1"
    local workspace="$2"
    local python_bin
    local api_json="$TEMP_ROOT/installed-api-search.json"
    local v24_json="$TEMP_ROOT/installed-v24-search.json"
    local examples_json="$TEMP_ROOT/installed-examples-search.json"

    python_bin="$(resolve_release_python_bin)"

    "$hive_bin" --path "$workspace" search "runtime contract" --scope api --limit 5 --json >"$api_json"
    "$hive_bin" --path "$workspace" search "DelegateGatewayAdapter" --scope api --limit 5 --json >"$v24_json"
    "$hive_bin" --path "$workspace" search "sandbox doctor" --scope examples --limit 5 --json >"$examples_json"

    assert_search_payload \
        "$python_bin" \
        "$api_json" \
        "api" \
        "package:docs/hive-v2.3-rfc/HIVE_V2_3_RUNTIME_AND_SANDBOX_SPEC.md"
    assert_search_payload \
        "$python_bin" \
        "$v24_json" \
        "api" \
        "package:docs/hive-v2.4-rfc/HIVE_V2_4_ADAPTER_MODEL_AND_LINK_SPEC.md"
    assert_search_payload \
        "$python_bin" \
        "$examples_json" \
        "example" \
        "package:docs/recipes/sandbox-doctor.md"
}

run_uv_tool_smoke() {
    local uv_home="$TEMP_ROOT/uv-home"
    local uv_bin_dir="$uv_home/.local/bin"
    local workspace="$TEMP_ROOT/uv-workspace"
    local hive_bin

    mkdir -p "$uv_home" "$uv_bin_dir" "$workspace"
    HOME="$uv_home" UV_TOOL_BIN_DIR="$uv_bin_dir" uv tool install --force --from "$WHEEL_PATH" "$DIST_PACKAGE_NAME" >/dev/null

    hive_bin="$uv_bin_dir/hive"
    "$hive_bin" --version >/dev/null
    "$hive_bin" --path "$workspace" init --json >/dev/null
    "$hive_bin" --path "$workspace" doctor --json >/dev/null
    "$hive_bin" --path "$workspace" sandbox doctor --json >/dev/null
    run_installed_search_smoke "$hive_bin" "$workspace"
}

run_pipx_smoke() {
    local pipx_home="$TEMP_ROOT/pipx-home"
    local pipx_bin="$TEMP_ROOT/pipx-bin"
    local pipx_man="$TEMP_ROOT/pipx-man"
    local workspace="$TEMP_ROOT/pipx-workspace"
    local python_bin

    mkdir -p "$pipx_home" "$pipx_bin" "$pipx_man" "$workspace"
    python_bin="$(resolve_release_python_bin)"

    PIPX_HOME="$pipx_home" \
    PIPX_BIN_DIR="$pipx_bin" \
    PIPX_MAN_DIR="$pipx_man" \
    PIPX_DEFAULT_PYTHON="$python_bin" \
    uvx --from pipx pipx install --force "$WHEEL_PATH" >/dev/null

    "$pipx_bin/hive" --version >/dev/null
    "$pipx_bin/hive" --path "$workspace" init --json >/dev/null
    "$pipx_bin/hive" --path "$workspace" doctor --json >/dev/null
    "$pipx_bin/hive" --path "$workspace" sandbox doctor --json >/dev/null
}

run_pip_smoke() {
    local venv_dir="$TEMP_ROOT/pip-venv"
    local workspace="$TEMP_ROOT/pip-workspace"
    local python_bin

    mkdir -p "$workspace"
    python_bin="$(resolve_release_python_bin)"
    "$python_bin" -m venv "$venv_dir"
    "$venv_dir/bin/pip" install "$WHEEL_PATH" >/dev/null

    "$venv_dir/bin/hive" --version >/dev/null
    "$venv_dir/bin/hive" --path "$workspace" init --json >/dev/null
    "$venv_dir/bin/hive" --path "$workspace" doctor --json >/dev/null
    "$venv_dir/bin/hive" --path "$workspace" sandbox doctor --json >/dev/null
    "$venv_dir/bin/python" -m hive --version >/dev/null
    "$venv_dir/bin/python" -m hive --path "$workspace" doctor --json >/dev/null
    "$venv_dir/bin/python" -m hive --path "$workspace" sandbox doctor --json >/dev/null
}

echo "🔎 Smoke-testing uv tool install..."
run_uv_tool_smoke

echo "🔎 Smoke-testing pip install..."
run_pip_smoke

echo "🔎 Smoke-testing pipx install..."
run_pipx_smoke

echo "✅ Release install smoke checks passed for $(basename "$WHEEL_PATH")"
