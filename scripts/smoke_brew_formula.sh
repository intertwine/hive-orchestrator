#!/bin/bash
#
# Smoke-test a generated Homebrew formula through style, audit, install, and test.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FORMULA_PATH="${1:-$REPO_ROOT/packaging/homebrew/agent-hive.rb}"
TAP_NAME="${HOMEBREW_TAP_NAME:-local/agent-hive-smoke}"
FORMULA_NAME="${HOMEBREW_FORMULA_NAME:-agent-hive}"
INSTALL_TARGET="$TAP_NAME/$FORMULA_NAME"

if ! command -v brew >/dev/null 2>&1; then
    echo "❌ Error: brew not found" >&2
    echo "Install Homebrew first: https://brew.sh" >&2
    exit 1
fi

if [ ! -f "$FORMULA_PATH" ]; then
    echo "❌ Error: formula not found at $FORMULA_PATH" >&2
    echo "Run 'make brew-formula' first." >&2
    exit 1
fi

export HOMEBREW_NO_AUTO_UPDATE="${HOMEBREW_NO_AUTO_UPDATE:-1}"
export HOMEBREW_NO_INSTALL_CLEANUP="${HOMEBREW_NO_INSTALL_CLEANUP:-1}"

cleanup() {
    brew uninstall --formula --force "$INSTALL_TARGET" >/dev/null 2>&1 || true
    brew untap "$TAP_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

brew untap "$TAP_NAME" >/dev/null 2>&1 || true
brew tap-new "$TAP_NAME" >/dev/null

TAP_REPO="$(brew --repo "$TAP_NAME")"
mkdir -p "$TAP_REPO/Formula"
cp "$FORMULA_PATH" "$TAP_REPO/Formula/$FORMULA_NAME.rb"

echo "🔎 Running Homebrew style checks..."
brew style "$INSTALL_TARGET"

echo "🔎 Running Homebrew audit..."
# Keep both flags on purpose: `--strict` catches formula quality regressions and
# `--online` validates remote resources the same way a real release install will.
brew audit --strict --online "$INSTALL_TARGET"

echo "🔎 Installing formula from temporary tap..."
brew install --formula "$INSTALL_TARGET"

echo "🔎 Running formula test..."
brew test "$INSTALL_TARGET"

echo "✅ Homebrew formula smoke checks passed for $INSTALL_TARGET"
