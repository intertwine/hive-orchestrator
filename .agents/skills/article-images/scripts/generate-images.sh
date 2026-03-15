#!/usr/bin/env bash
#
# Generate article images from prompt markdown files.
# Supports multiple image generation providers: OpenAI (DALL-E) and Google Gemini.
# Automatically falls back to alternate provider when rate limits are hit.
#
# Usage:
#   ./generate-images.sh                                    # Generate with default provider (gemini)
#   ./generate-images.sh --provider openai                  # Use OpenAI DALL-E
#   ./generate-images.sh --provider gemini                  # Use Google Gemini
#   ./generate-images.sh --glob "articles/prompts/01-*.md"  # Specific file
#   ./generate-images.sh --dry-run                          # Preview only
#   ./generate-images.sh --force                            # Regenerate all
#   ./generate-images.sh --count 3                          # 3 variants per prompt
#   ./generate-images.sh --no-fallback                      # Disable automatic provider fallback

set -uo pipefail

# Find repo root (where .env lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Navigate up from .claude/skills/article-images to repo root (3 levels)
REPO_ROOT="$(cd "$SKILL_DIR/../../.." && pwd)"

# Load .env if it exists
if [[ -f "$REPO_ROOT/.env" ]]; then
    # Export variables from .env (skip comments and empty lines)
    while IFS='=' read -r key value; do
        # Skip empty lines and comments
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Trim whitespace from key
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        # Export the variable
        export "$key=$value"
    done < "$REPO_ROOT/.env"
fi

# Parse arguments
PROMPTS_GLOB="${PROMPTS_GLOB:-articles/prompts/*.md}"
DRY_RUN="${DRY_RUN:-false}"
FORCE="${FORCE:-false}"
IMAGES_PER_PROMPT="${IMAGES_PER_PROMPT:-1}"
PROVIDER="${PROVIDER:-gemini}"
ENABLE_FALLBACK=true
PARALLEL="${PARALLEL:-1}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        --glob)
            PROMPTS_GLOB="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --count)
            IMAGES_PER_PROMPT="$2"
            shift 2
            ;;
        --no-fallback)
            ENABLE_FALLBACK=false
            shift
            ;;
        --parallel)
            PARALLEL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --provider NAME   Image provider: 'gemini' (default) or 'openai'"
            echo "  --glob PATTERN    Glob pattern for prompt files (default: articles/prompts/*.md)"
            echo "  --dry-run         Preview without generating images"
            echo "  --force           Regenerate even if manifest exists"
            echo "  --count N         Number of image variants per prompt (default: 1)"
            echo "  --parallel N      Number of images to generate in parallel (default: 1)"
            echo "  --no-fallback     Disable automatic fallback to alternate provider on rate limit"
            echo "  --help            Show this help message"
            echo ""
            echo "Providers:"
            echo "  gemini   - Google Gemini (requires GOOGLE_CLOUD_PROJECT)"
            echo "  openai   - OpenAI gpt-image-1.5 (requires OPENAI_API_KEY)"
            echo ""
            echo "Auto-fallback:"
            echo "  When rate limits (429) are hit, automatically retries with the alternate"
            echo "  provider if credentials are available. Use --no-fallback to disable."
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Check which providers have credentials available
has_gemini_creds() {
    [[ -n "${GOOGLE_CLOUD_PROJECT:-}" ]]
}

has_openai_creds() {
    [[ -n "${OPENAI_API_KEY:-}" ]]
}

# Get the fallback provider
get_fallback_provider() {
    local current="$1"
    if [[ "$current" == "gemini" ]] && has_openai_creds; then
        echo "openai"
    elif [[ "$current" == "openai" ]] && has_gemini_creds; then
        echo "gemini"
    else
        echo ""
    fi
}

# Setup provider-specific configuration
setup_provider() {
    local provider="$1"

    case "$provider" in
        gemini)
            if ! has_gemini_creds; then
                echo "Error: GOOGLE_CLOUD_PROJECT not set. Add it to .env or export it." >&2
                return 1
            fi
            SCRIPT_NAME="generate-images-gemini.mjs"
            ;;
        openai)
            if ! has_openai_creds; then
                echo "Error: OPENAI_API_KEY not set. Add it to .env or export it." >&2
                return 1
            fi
            SCRIPT_NAME="generate-images-from-prompts.mjs"
            # Set gpt-image-1.5 compatible sizes if not already set
            export MODEL="${MODEL:-gpt-image-1.5}"
            export SIZE_16_9="${SIZE_16_9:-1536x1024}"
            export SIZE_4_3="${SIZE_4_3:-1536x1024}"
            export SIZE_3_2="${SIZE_3_2:-1536x1024}"
            ;;
        *)
            echo "Error: Unknown provider '$provider'. Use 'gemini' or 'openai'." >&2
            return 1
            ;;
    esac
    return 0
}

# Run the image generation script and capture output
run_generation() {
    local provider="$1"
    local output
    local exit_code

    setup_provider "$provider" || return 1

    echo "Generating images..."
    echo "  Provider: $provider"
    echo "  Prompts: $PROMPTS_GLOB"
    echo "  Dry run: $DRY_RUN"
    echo "  Force: $FORCE"
    echo "  Variants per prompt: $IMAGES_PER_PROMPT"
    echo "  Parallel: $PARALLEL"
    echo ""

    # Run and capture both output and exit code
    # Use a temp file to capture output while still showing it in real-time
    local temp_output
    temp_output=$(mktemp)

    set +e
    node "$SCRIPT_DIR/$SCRIPT_NAME" 2>&1 | tee "$temp_output"
    exit_code=${PIPESTATUS[0]}
    set -e

    output=$(cat "$temp_output")
    rm -f "$temp_output"

    # Check if we hit a rate limit (429)
    if [[ $exit_code -ne 0 ]] && echo "$output" | grep -q "429\|RESOURCE_EXHAUSTED\|rate.limit\|Too Many Requests"; then
        echo ""
        echo "⚠️  Rate limit hit with $provider provider."
        return 2  # Special exit code for rate limit
    fi

    return $exit_code
}

# Export environment variables for the Node script
export PROMPTS_GLOB
export DRY_RUN
export FORCE
export IMAGES_PER_PROMPT
export PARALLEL

# Run from repo root so paths resolve correctly
cd "$REPO_ROOT"

# Validate the requested provider has credentials
if ! setup_provider "$PROVIDER"; then
    exit 1
fi

# Run generation with primary provider
run_generation "$PROVIDER"
primary_exit=$?

# If rate limited and fallback is enabled, try alternate provider
if [[ $primary_exit -eq 2 ]] && [[ "$ENABLE_FALLBACK" == "true" ]]; then
    FALLBACK=$(get_fallback_provider "$PROVIDER")

    if [[ -n "$FALLBACK" ]]; then
        echo ""
        echo "🔄 Automatically switching to $FALLBACK provider..."
        echo "   (The manifest tracks progress, so only missing images will be generated)"
        echo ""

        run_generation "$FALLBACK"
        fallback_exit=$?

        if [[ $fallback_exit -eq 0 ]]; then
            echo ""
            echo "✅ Completed with fallback provider ($FALLBACK)"
            exit 0
        elif [[ $fallback_exit -eq 2 ]]; then
            echo ""
            echo "❌ Both providers hit rate limits. Please try again later."
            exit 1
        else
            exit $fallback_exit
        fi
    else
        echo ""
        echo "ℹ️  No fallback provider available (missing credentials for alternate provider)."
        echo "   To enable fallback, set both GOOGLE_CLOUD_PROJECT and OPENAI_API_KEY in .env"
        exit 1
    fi
elif [[ $primary_exit -ne 0 ]]; then
    exit $primary_exit
fi
