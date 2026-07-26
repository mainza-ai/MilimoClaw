#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# ═══════════════════════════════════════════════════════════════════════
#  MilimoClaw Hermes Profile Install Script
# ═══════════════════════════════════════════════════════════════════════
# Installs and onboards the Milimo Hermes profile using NemoHermes.
#
# Usage:
#   ./install-hermes.sh [options]
#
# Options:
#   --name NAME           Sandbox name (default: milimo-hermes)
#   --profile PROFILE     Policy profile: restricted, balanced, open (default: restricted)
#   --model-router        Enable Model Router (requires qualifying Python 3.10-3.13)
#   --auth-mode MODE      Auth mode: api_key (default) or nous_oauth (managed tool gateways)
#   --nous-oauth          DEPRECATED: Use --auth-mode nous_oauth instead
#   --headless            Headless remote deployment (prompts for CHAT_UI_URL)
#   --slack-channels LIST Comma-separated Slack channels for alerts
#   --chat-ui-url URL     Remote dashboard URL for headless deployments
#   --non-interactive     Non-interactive mode (requires all env vars set)
#   --dry-run             Show commands without executing
#   --help                Show this help

set -euo pipefail

# Default values
SANDBOX_NAME="${SANDBOX_NAME:-milimo-hermes}"
POLICY_TIER="${POLICY_TIER:-restricted}"
ENABLE_MODEL_ROUTER="${ENABLE_MODEL_ROUTER:-false}"
AUTH_MODE="${AUTH_MODE:-api_key}"
HEADLESS="${HEADLESS:-false}"
SLACK_CHANNELS="${SLACK_CHANNELS:-}"
CHAT_UI_URL="${CHAT_UI_URL:-}"
NON_INTERACTIVE="${NON_INTERACTIVE:-false}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_SYNC_CHECK="${SKIP_SYNC_CHECK:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

show_help() {
  cat <<'EOF'
MilimoClaw Hermes Profile Install Script

USAGE:
    ./install-hermes.sh [OPTIONS]

OPTIONS:
    --name NAME              Sandbox name (default: milimo-hermes)
    --profile PROFILE        Policy profile: restricted, balanced, open (default: restricted)
    --model-router           Enable Model Router (requires qualifying Python 3.10-3.13)
    --auth-mode MODE         Auth mode: api_key (default) or nous_oauth (managed tool gateways)
    --nous-oauth             DEPRECATED: Use --auth-mode nous_oauth instead
    --headless               Headless remote deployment (prompts for CHAT_UI_URL)
    --slack-channels LIST    Comma-separated Slack channels for alerts
    --chat-ui-url URL        Remote dashboard URL for headless deployments
    --non-interactive        Non-interactive mode (requires all env vars set)
    --dry-run                Show commands without executing
    --skip-sync-check        Do not check root ↔ sandbox plugin/core sync before build
    --help                   Show this help

ENVIRONMENT VARIABLES (for non-interactive mode):
    NEMOCLAW_SANDBOX_NAME        Sandbox name
    NEMOCLAW_POLICY_TIER         Policy tier: restricted, balanced, open
    NEMOCLAW_MODEL_ROUTER        1 to enable Model Router
    NEMOCLAW_AUTH_MODE           Auth mode: api_key or nous_oauth
    NEMOCLAW_NOUS_OAUTH          1 to use Nous Portal OAuth (deprecated)
    NEMOCLAW_HEADLESS            1 for headless deployment
    SLACK_ALLOWED_CHANNELS       Comma-separated Slack channels
    CHAT_UI_URL                  Remote dashboard URL
    NVIDIA_API_KEY               NVIDIA API key (required)
    NEMOCLAW_ACCEPT_THIRD_PARTY 1 to accept third-party software
    NEMOCLAW_NON_INTERACTIVE     1 for non-interactive mode
    NEMOCLAW_MODEL_ROUTER_PYTHON Python path for Model Router
    MILIMO_SKIP_SYNC_CHECK       1 to skip the root ↔ sandbox plugin/core sync guard

EXAMPLES:
    # Interactive install with defaults
    ./install-hermes.sh

    # Headless CI install
    ./install-hermes.sh --non-interactive --headless --chat-ui-url https://my-host.example.com

    # With Model Router and Nous OAuth
    ./install-hermes.sh --model-router --auth-mode nous_oauth --slack-channels "#alerts,#general"

    # Custom sandbox name and policy
    ./install-hermes.sh --name my-milimo-hermes --profile balanced

EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --name)
        SANDBOX_NAME="$2"
        shift 2
        ;;
      --profile)
        POLICY_TIER="$2"
        shift 2
        ;;
      --model-router)
        ENABLE_MODEL_ROUTER=true
        shift
        ;;
      --auth-mode)
        AUTH_MODE="$2"
        if [[ "$AUTH_MODE" != "api_key" && "$AUTH_MODE" != "nous_oauth" ]]; then
          log_error "Invalid auth mode: $AUTH_MODE. Must be 'api_key' or 'nous_oauth'"
          exit 1
        fi
        shift 2
        ;;
      --nous-oauth)
        log_warn "--nous-oauth is deprecated. Use --auth-mode nous_oauth instead"
        AUTH_MODE="nous_oauth"
        shift
        ;;
      --headless)
        HEADLESS=true
        shift
        ;;
      --slack-channels)
        SLACK_CHANNELS="$2"
        shift 2
        ;;
      --chat-ui-url)
        CHAT_UI_URL="$2"
        shift 2
        ;;
      --non-interactive)
        NON_INTERACTIVE=true
        shift
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --skip-sync-check)
        SKIP_SYNC_CHECK=true
        shift
        ;;
      --help)
        show_help
        exit 0
        ;;
      *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
    esac
  done
}

check_prerequisites() {
  log_info "Checking prerequisites..."

  # Source .env file from project root if it exists
  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")"
  local project_root
  project_root="$(dirname "$(dirname "$script_path")")"
  log_info "Project root: $project_root"
  if [[ -f "$project_root/.env" ]]; then
    log_info "Sourcing .env file from project root..."
    set -a
    source "$project_root/.env"
    set +a
    log_info "NVIDIA_API_KEY set: ${NVIDIA_API_KEY:+yes}"
  else
    log_warn ".env file not found at $project_root/.env"
  fi

  # Check for nemoclaw CLI
  if ! command -v nemoclaw &>/dev/null; then
    log_error "nemoclaw CLI not found. Install from https://github.com/NVIDIA/nemoclaw"
    exit 1
  fi

  # Check for nemohermes CLI (create function fallback if not installed)
  if ! command -v nemohermes &>/dev/null; then
    log_warn "nemohermes CLI not found. Creating fallback function..."
    nemohermes() { NEMOCLAW_AGENT=hermes nemoclaw "$@"; }
    export -f nemohermes
  fi

  # Check Docker
  if ! command -v docker &>/dev/null; then
    log_error "Docker not found. Please install Docker."
    exit 1
  fi

  # Check NVIDIA_API_KEY
  if [[ -z "${NVIDIA_API_KEY:-}" ]]; then
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
      log_error "NVIDIA_API_KEY environment variable required for non-interactive mode"
      exit 1
    else
      log_warn "NVIDIA_API_KEY not set. You will be prompted during onboarding."
    fi
  fi

  # Export for nemohermes onboard (expects NVIDIA_INFERENCE_API_KEY)
  export NVIDIA_INFERENCE_API_KEY="${NVIDIA_API_KEY}"

  # Check for qualifying Python if Model Router enabled
  if [[ "$ENABLE_MODEL_ROUTER" == "true" ]]; then
    check_model_router_python
  fi

  log_success "Prerequisites check passed"
}

check_model_router_python() {
  log_info "Checking for qualifying Python (3.10-3.13) for Model Router..."

  local python_path="${NEMOCLAW_MODEL_ROUTER_PYTHON:-}"

  if [[ -n "$python_path" ]]; then
    if [[ -x "$python_path" ]]; then
      local version
      version=$("$python_path" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      log_info "Using specified Python: $python_path (version $version)"
      return 0
    else
      log_error "Specified Python not executable: $python_path"
      exit 1
    fi
  fi

  # Probe for qualifying Python
  for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
      local version
      version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      local major_minor="${version%.*}"
      local major="${major_minor%%.*}"
      local minor="${major_minor#*.}"
      if [[ $major -eq 3 && $minor -ge 10 && $minor -le 13 ]]; then
        # Check required modules
        if "$cmd" -c "import ensurepip, pyexpat, ssl, venv" 2>/dev/null; then
          log_info "Found qualifying Python: $cmd (version $version)"
          export NEMOCLAW_MODEL_ROUTER_PYTHON
          NEMOCLAW_MODEL_ROUTER_PYTHON="$(command -v "$cmd")"
          return 0
        else
          log_warn "Python $cmd missing required modules (ensurepip, pyexpat, ssl, venv)"
        fi
      fi
    fi
  done

  log_error "No qualifying Python 3.10-3.13 found with required modules"
  log_error "Model Router requires: ensurepip, pyexpat, ssl, venv"
  log_error "Install a supported Python or set NEMOCLAW_MODEL_ROUTER_PYTHON"
  exit 1
}

detect_headless() {
  if [[ "$HEADLESS" == "true" ]]; then
    return 0
  fi

  # Auto-detect headless
  if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]] && ! [[ -t 0 ]]; then
    log_info "Headless environment detected"
    HEADLESS=true
  fi
}

prompt_chat_ui_url() {
  if [[ "$HEADLESS" == "true" && -z "$CHAT_UI_URL" ]]; then
    if [[ "$NON_INTERACTIVE" == "true" ]]; then
      log_error "CHAT_UI_URL required for headless non-interactive mode"
      exit 1
    fi

    echo ""
    log_info "Headless deployment detected. The Hermes dashboard runs on port 18790."
    log_info "To access it remotely, you need to set CHAT_UI_URL."
    echo ""
    echo "Options:"
    echo "  1. SSH port forwarding: ssh -L 18790:127.0.0.1:18790 user@host"
    echo "  2. Reverse proxy (nginx, traefik) with CHAT_UI_URL=https://your-domain.com"
    echo "  3. Tailscale/VPN with direct IP access"
    echo ""
    read -rp "Enter CHAT_UI_URL (or press Enter for SSH port forwarding): " CHAT_UI_URL

    if [[ -z "$CHAT_UI_URL" ]]; then
      log_info "Using SSH port forwarding. Run this after onboarding:"
      log_info "  ssh -L 18790:127.0.0.1:18790 $(whoami)@$(hostname -f)"
    fi
  fi
}

prompt_slack_channels() {
  if [[ -n "$SLACK_CHANNELS" ]]; then
    return 0
  fi

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    return 0
  fi

  echo ""
  log_info "Slack integration for War Room alerts (optional)."
  log_info "SLACK_ALLOWED_CHANNELS is baked into the sandbox image at build time."
  log_info "It cannot be changed without rebuilding the image."
  echo ""
  read -rp "Enter comma-separated Slack channels (e.g., #alerts,#general) or press Enter to skip: " SLACK_CHANNELS
}

prompt_auth_mode() {
  if [[ "$AUTH_MODE" == "nous_oauth" ]]; then
    return 0
  fi

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    return 0
  fi

  echo ""
  log_info "Authentication mode selection:"
  echo "  1) api_key       - Standard NVIDIA inference (default)"
  echo "  2) nous_oauth    - Nous Portal OAuth (enables managed tool gateways)"
  echo "                     Includes: web search, browser automation, image generation,"
  echo "                     audio processing, managed code execution"
  echo ""
  read -rp "Select auth mode [1/2] (default: 1): " choice
  echo
  case "$choice" in
    2)
      AUTH_MODE="nous_oauth"
      log_info "Nous OAuth mode selected - managed tool gateways enabled"
      ;;
    *)
      AUTH_MODE="api_key"
      log_info "API Key mode selected - standard NVIDIA inference"
      ;;
  esac
}

prompt_model_router() {
  if [[ "$ENABLE_MODEL_ROUTER" == "true" ]]; then
    return 0
  fi

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    return 0
  fi

  echo ""
  log_info "Model Router (cost-optimized inference routing):"
  echo "  - Uses PrefillRouter to select models based on cost/quality tolerance"
  echo "  - Finance/Ops approval: always highest accuracy (tolerance 0.0)"
  echo "  - Content generation: cost-optimized (tolerance 0.2-0.4)"
  echo "  - Requires qualifying Python 3.10-3.13 on host"
  echo ""
  read -rp "Enable Model Router? [y/N]: " -n 1
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    ENABLE_MODEL_ROUTER=true
    check_model_router_python
  fi
}

setup_link_cli_auth() {
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    log_info "Skipping interactive link-cli auth in non-interactive mode"
    log_info "Authenticate later with: nemohermes $SANDBOX_NAME exec --tty -- link-cli auth login"
    return 0
  fi

  log_info "Configuring Stripe Link CLI authentication..."

  local auth_log="/tmp/link-cli-auth-${SANDBOX_NAME}.log"
  local url_file="/tmp/link-cli-device-url.txt"

  if ! command -v nemohermes &>/dev/null; then
    log_warn "nemohermes CLI not found; skipping automated link-cli auth"
    log_info "Authenticate manually: link-cli auth login"
    return 0
  fi

  # Start auth login in background; it prints the device URL immediately,
  # then polls until approval or timeout. We capture the URL and detach.
  nohup nemohermes "$SANDBOX_NAME" exec -- link-cli auth login --timeout 300 \
    >"$auth_log" 2>&1 &
  local auth_pid=$!

  # Wait briefly for the device URL to appear in the log
  local device_url=""
  for _i in 1 2 3 4 5 6 7 8 9 10; do
    if [[ -s "$auth_log" ]]; then
      device_url=$(grep -oE 'https?://[^ ]+' "$auth_log" | head -1)
      [[ -n "$device_url" ]] && break
    fi
    sleep 1
  done

  if [[ -n "$device_url" ]]; then
    echo "$device_url" >"$url_file"
    log_success "Stripe Link device URL: $device_url"
    log_info "Complete authentication in your Stripe Link app."
    log_info "Background auth process continuing (PID: $auth_pid)."
    log_info "To check later: nemohermes $SANDBOX_NAME exec -- link-cli auth status"
  else
    log_warn "Could not capture device URL automatically."
    log_info "Authenticate manually after connecting:"
    log_info "  nemohermes $SANDBOX_NAME exec --tty -- link-cli auth login"
    kill "$auth_pid" 2>/dev/null || true
    wait "$auth_pid" 2>/dev/null || true
  fi
}

prepare_build_context() {
  log_info "Preparing build context..."

  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")"
  local project_root
  project_root="$(dirname "$(dirname "$script_path")")"
  sandbox_dir="$(dirname "$script_path")"

  log_info "Project root: $project_root"
  log_info "Sandbox dir: $sandbox_dir"

  # IMPORTANT: Dockerfile COPY paths are relative to milimo-hermes-sandbox/ (the build
  # context).  The sandbox-local copies under $sandbox_dir/ are the authoritative
  # build-time sources — they match the COPY paths in the Dockerfile.
  # $project_root/ copies are secondary mirrors kept in sync manually.
  for dir in milimo-core milimo-hermes-plugin milimo-blueprint; do
    if [[ -d "$sandbox_dir/$dir" ]]; then
      log_info "Removing existing $dir from build context..."
      rm -rf "${sandbox_dir:?}/${dir:?}"
    fi
    if [[ -d "$project_root/$dir" ]]; then
      log_info "Copying $dir into sandbox build context..."
      cp -r "$project_root/$dir" "$sandbox_dir/$dir"
    else
      log_error "Required directory not found: $project_root/$dir"
      exit 1
    fi
  done

  if [[ ! -f "$sandbox_dir/generate-config.ts" ]]; then
    log_error "Required file not found: $sandbox_dir/generate-config.ts"
    exit 1
  fi
  if [[ ! -d "$sandbox_dir/config" ]]; then
    log_error "Required directory not found: $sandbox_dir/config"
    exit 1
  fi

  log_success "Build context prepared successfully"
}

build_docker_image() {
  log_info "Building Milimo Hermes sandbox image..."

  local sandbox_dir
  sandbox_dir="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"

  local docker_args=()
  docker_args+=(-f "$sandbox_dir/Dockerfile")
  docker_args+=(-t milimo-hermes-sandbox:latest)
  docker_args+=(--build-arg "NEMOCLAW_MODEL=${NEMOCLAW_MODEL}")
  docker_args+=(--build-arg "NEMOCLAW_INFERENCE_PROVIDER_ID=${NEMOCLAW_INFERENCE_PROVIDER_ID:-custom}")
  docker_args+=(--build-arg "NEMOCLAW_PROVIDER_KEY=${NEMOCLAW_PROVIDER_KEY}")
  docker_args+=(--build-arg "NEMOCLAW_INFERENCE_BASE_URL=${NEMOCLAW_INFERENCE_BASE_URL}")
  docker_args+=(--build-arg "CHAT_UI_URL=${CHAT_UI_URL}")
  docker_args+=(--build-arg "NEMOCLAW_MESSAGING_CHANNELS_B64=${NEMOCLAW_MESSAGING_CHANNELS_B64}")
  docker_args+=(--build-arg "NEMOCLAW_MESSAGING_ALLOWED_IDS_B64=${NEMOCLAW_MESSAGING_ALLOWED_IDS_B64}")
  docker_args+=(--build-arg "NEMOCLAW_DISCORD_GUILDS_B64=${NEMOCLAW_DISCORD_GUILDS_B64}")
  docker_args+=(--build-arg "NEMOCLAW_TELEGRAM_CONFIG_B64=${NEMOCLAW_TELEGRAM_CONFIG_B64}")
  docker_args+=(--build-arg "NEMOCLAW_WECHAT_CONFIG_B64=${NEMOCLAW_WECHAT_CONFIG_B64}")
  docker_args+=(--build-arg "NEMOCLAW_SLACK_CONFIG_B64=${NEMOCLAW_SLACK_CONFIG_B64}")
  docker_args+=(--build-arg "NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER=${NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER}")
  docker_args+=(--build-arg "NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64=${NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64}")
  docker_args+=(--build-arg "NEMOCLAW_BUILD_ID=${NEMOCLAW_BUILD_ID}")
  docker_args+=(--build-arg "NEMOCLAW_DARWIN_VM_COMPAT=${NEMOCLAW_DARWIN_VM_COMPAT}")
  docker_args+=(--build-arg "NEMOCLAW_MESSAGING_PLAN_B64=${NEMOCLAW_MESSAGING_PLAN_B64}")
  docker_args+=(--build-arg "MILIMO_SPEND_TEST_MODE=${MILIMO_SPEND_TEST_MODE:-true}")
  docker_args+=(--build-arg "MILIMO_DAILY_SPEND_CAP_CENTS=${MILIMO_DAILY_SPEND_CAP_CENTS:-10000}")
  docker_args+=(--build-arg "MILIMO_OPERATOR=${MILIMO_OPERATOR:-}")

  if [[ -n "$SLACK_CHANNELS" ]]; then
    local slack_json
    slack_json=$(echo "$SLACK_CHANNELS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')
    local slack_b64
    slack_b64=$(echo -n "$slack_json" | base64 -w0)
    docker_args+=(--build-arg "NEMOCLAW_SLACK_CONFIG_B64=$slack_b64")
  fi

  run_command "docker build ${docker_args[*]} \"$sandbox_dir\""

  log_success "Sandbox image built successfully"
}

run_command() {
  local cmd="$1"
  log_info "Running: $cmd"
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "[DRY RUN] Would execute: $cmd"
    return 0
  fi
  eval "$cmd"
}

build_onboard_command() {
  local cmd="nemohermes onboard"
  cmd+=" --name $SANDBOX_NAME"
  cmd+=" --from ./milimo-hermes-sandbox/Dockerfile"

  if [[ "$ENABLE_MODEL_ROUTER" == "true" ]]; then
    cmd+=" --model-router"
    if [[ -n "${NEMOCLAW_MODEL_ROUTER_PYTHON:-}" ]]; then
      cmd+=" --model-router-python ${NEMOCLAW_MODEL_ROUTER_PYTHON}"
    fi
  fi

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    cmd+=" --non-interactive --yes"
    cmd+=" --yes-i-accept-third-party-software"
    cmd+=" --recreate-sandbox"
    export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
    export NEMOCLAW_NON_INTERACTIVE=1
    export NEMOCLAW_RECREATE_SANDBOX=1
    export NEMOCLAW_POLICY_TIER="${NEMOCLAW_POLICY_TIER:-$POLICY_TIER}"
    export NEMOCLAW_POLICY_MODE="${NEMOCLAW_POLICY_MODE:-suggested}"
  fi

  printf '%s\n' "$cmd"
}

main() {
  echo "════════════════════════════════════════════════════════════════════"
  echo "  MilimoClaw Hermes Profile Installer"
  echo "════════════════════════════════════════════════════════════════════"
  echo ""

  parse_args "$@"

  # Load env vars for non-interactive mode
  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    SANDBOX_NAME="${NEMOCLAW_SANDBOX_NAME:-$SANDBOX_NAME}"
    POLICY_TIER="${NEMOCLAW_POLICY_TIER:-$POLICY_TIER}"
    ENABLE_MODEL_ROUTER="${NEMOCLAW_MODEL_ROUTER:-false}"
    AUTH_MODE="${NEMOCLAW_AUTH_MODE:-api_key}"
    # Handle deprecated NEMOCLAW_NOUS_OAUTH
    if [[ "${NEMOCLAW_NOUS_OAUTH:-}" == "1" || "${NEMOCLAW_NOUS_OAUTH:-}" == "true" ]]; then
      AUTH_MODE="nous_oauth"
    fi
    HEADLESS="${NEMOCLAW_HEADLESS:-false}"
    SLACK_CHANNELS="${SLACK_ALLOWED_CHANNELS:-$SLACK_CHANNELS}"
    CHAT_UI_URL="${CHAT_UI_URL:-$CHAT_UI_URL}"
  fi

  check_prerequisites
  detect_headless
  prompt_chat_ui_url
  prompt_slack_channels
  prompt_auth_mode
  prompt_model_router

  log_info "Configuration:"
  log_info "  Sandbox name: $SANDBOX_NAME"
  log_info "  Policy tier: $POLICY_TIER"
  log_info "  Model Router: $ENABLE_MODEL_ROUTER"
  log_info "  Auth mode: $AUTH_MODE"
  log_info "  Headless: $HEADLESS"
  log_info "  Slack channels: ${SLACK_CHANNELS:-none}"
  log_info "  CHAT_UI_URL: ${CHAT_UI_URL:-none}"
  echo ""

  # Prepare onboarding command - uses nemohermes onboard with our custom Dockerfile
  # Note: nemohermes onboard only supports flags shown in `nemohermes onboard --help`
  # Build args are passed explicitly to `docker build --build-arg`
  # Auth/nous_oauth is handled by the onboarding wizard; do not pass --auth here
  local onboard_cmd
  onboard_cmd=$(build_onboard_command)

  # Set build arg environment variables (Docker will use these for ARGs in Dockerfile)
  export NEMOCLAW_MODEL="${NEMOCLAW_MODEL:-stepfun-ai/step-3.7-flash}"
  export NEMOCLAW_INFERENCE_PROVIDER_ID="${NEMOCLAW_INFERENCE_PROVIDER_ID:-custom}"
  export NEMOCLAW_PROVIDER_KEY="${NEMOCLAW_PROVIDER_KEY:-inference}"
  export NEMOCLAW_INFERENCE_BASE_URL="${NEMOCLAW_INFERENCE_BASE_URL:-https://inference.local/v1}"
  export NVIDIA_INFERENCE_API_KEY="${NVIDIA_API_KEY:-}"
  export CHAT_UI_URL="${CHAT_UI_URL:-http://127.0.0.1:8642}"
  export NEMOCLAW_MESSAGING_CHANNELS_B64="${NEMOCLAW_MESSAGING_CHANNELS_B64:-W10=}"
  export NEMOCLAW_MESSAGING_ALLOWED_IDS_B64="${NEMOCLAW_MESSAGING_ALLOWED_IDS_B64:-e30=}"
  export NEMOCLAW_DISCORD_GUILDS_B64="${NEMOCLAW_DISCORD_GUILDS_B64:-e30=}"
  export NEMOCLAW_TELEGRAM_CONFIG_B64="${NEMOCLAW_TELEGRAM_CONFIG_B64:-e30=}"
  export NEMOCLAW_WECHAT_CONFIG_B64="${NEMOCLAW_WECHAT_CONFIG_B64:-e30=}"
  export NEMOCLAW_SLACK_CONFIG_B64="${NEMOCLAW_SLACK_CONFIG_B64:-e30=}"
  export NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64="${NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64:-W10=}"
  export NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER="${NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER:-0}"
  export NEMOCLAW_BUILD_ID="${NEMOCLAW_BUILD_ID:-default}"
  export NEMOCLAW_DARWIN_VM_COMPAT="${NEMOCLAW_DARWIN_VM_COMPAT:-0}"
  export NEMOCLAW_MESSAGING_PLAN_B64="${NEMOCLAW_MESSAGING_PLAN_B64:-}"
  export MILIMO_SPEND_TEST_MODE="${MILIMO_SPEND_TEST_MODE:-true}"
  export MILIMO_DAILY_SPEND_CAP_CENTS="${MILIMO_DAILY_SPEND_CAP_CENTS:-10000}"
  export MILIMO_OPERATOR="${MILIMO_OPERATOR:-}"

  if [[ -n "$SLACK_CHANNELS" ]]; then
    # Convert comma-separated to JSON array, then base64
    local slack_json
    slack_json=$(echo "$SLACK_CHANNELS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')
    local slack_b64
    slack_b64=$(echo -n "$slack_json" | base64 -w0)
    export NEMOCLAW_SLACK_CONFIG_B64="$slack_b64"
  fi

  local project_root
  project_root="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")"

  if [[ "${MILIMO_SKIP_SYNC_CHECK:-${SKIP_SYNC_CHECK:-false}}" != "true" ]]; then
    log_info "Checking root ↔ sandbox plugin/core sync..."
    local sync_script="$project_root/scripts/check-plugin-sync.sh"
    if [[ -x "$sync_script" ]]; then
      if ! "$sync_script"; then
        if [[ "$NON_INTERACTIVE" == "true" ]]; then
          log_error "Plugin sync check failed in non-interactive mode — aborting."
          exit 1
        fi
        log_warn "Proceeding anyway (interactive mode — run 'make sync' or --skip-sync-check to silence)."
      fi
    fi
  else
    log_info "Skipping root ↔ sandbox plugin/core sync check (MILIMO_SKIP_SYNC_CHECK=true)"
  fi

  prepare_build_context
  build_docker_image

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "[DRY RUN] Would execute onboarding:"
    log_info "  $onboard_cmd"
    log_info "  Build arg env vars set: NEMOCLAW_MODEL, CHAT_UI_URL, NEMOCLAW_SLACK_CONFIG_B64, etc."
    return 0
  fi

  # ── Pre-flight: clean stale state + verify gateway ──────────────────
  # Stale --fresh resumable state from a previously killed onboard can
  # interfere with the next attempt.  Clear it unconditionally.
  rm -rf /tmp/.nemoclaw-onboarding-* 2>/dev/null || true

  # Verify the OpenShell gateway is responsive.  If not, recovery will
  # add ~2 minutes to the onboard; better to fail fast here.
  if ! timeout 10 curl -s --max-time 5 "http://127.0.0.1:8080/health" >/dev/null 2>&1; then
    log_warn "OpenShell gateway health check failed — will attempt recovery during onboard."
  fi

  # ── Preemptive sandbox cleanup ──────────────────────────────────────
  # nemohermes onboard --recreate-sandbox can hang indefinitely at
  # [6/8] Creating sandbox if the graceful teardown of the existing
  # sandbox stalls.  We handle this in three layers:
  #
  #   Layer 1 — nemohermes destroy (with timeout)
  #   Layer 2 — docker rm -f any leftover openshell container
  #   Layer 3 — wait until the sandbox status returns not-found
  #
  # Each layer has its own timeout so a single stuck call cannot block
  # the install script.
  log_info "Cleaning up any existing sandbox '$SANDBOX_NAME' before rebuild..."

  # Layer 1: nemohermes destroy (handles gateway state cleanup)
  if timeout 30 nemohermes "$SANDBOX_NAME" status --json 2>/dev/null | grep -q '"found":true'; then
    log_info "  Existing sandbox found — destroying via nemohermes..."
    NEMOCLAW_RECREATE_WITHOUT_BACKUP=1 timeout 60 \
      nemohermes "$SANDBOX_NAME" destroy --yes 2>/dev/null || true
  else
    log_info "  No existing sandbox found via nemohermes status."
  fi

  # Layer 2: Docker-level cleanup (handles stray containers)
  local _old_container
  _old_container="$(docker ps -a --filter name=openshell-"$SANDBOX_NAME" --format '{{.ID}}' 2>/dev/null | head -1)"
  if [[ -n "$_old_container" ]]; then
    log_info "  Removing stale Docker container $_old_container..."
    docker rm -f "$_old_container" 2>/dev/null || true
  fi

  # Layer 3: Verify sandbox is actually gone
  local _cleanup_attempts=0
  while timeout 10 nemohermes "$SANDBOX_NAME" status --json 2>/dev/null | grep -q '"found":true'; do
    _cleanup_attempts=$((_cleanup_attempts + 1))
    if [ "$_cleanup_attempts" -ge 6 ]; then
      log_warn "  Could not fully clean sandbox state after 6 attempts — proceeding anyway."
      break
    fi
    log_info "  Waiting for sandbox cleanup (attempt $_cleanup_attempts)..."
    sleep 5
  done
  log_success "Sandbox cleanup complete."

  # ── Run onboarding with retry ────────────────────────────────────────
  # Timeout for onboarding command (15 min). nemohermes onboard can hang
  # indefinitely at [6/8] Creating sandbox if the destroy step stalls.
  local _onboard_timeout="900"
  local _onboard_retries=0
  local _onboard_max_retries=1
  local _onboard_ok=false

  while [ "$_onboard_retries" -le "$_onboard_max_retries" ]; do
    if [ "$_onboard_retries" -gt 0 ]; then
      log_info "Retrying onboarding (attempt $((_onboard_retries + 1))/${_onboard_max_retries})..."
      # After a failed --recreate-sandbox, the sandbox may already be
      # destroyed.  Retry without --recreate-sandbox since there's nothing
      # to recreate.
      onboard_cmd="${onboard_cmd/--recreate-sandbox/}"
    fi

    log_info "Starting Hermes onboarding (timeout: ${_onboard_timeout}s, attempt $((_onboard_retries + 1)))..."
    log_info "Command: $onboard_cmd"
    echo ""

    if timeout "$_onboard_timeout" bash -c "$onboard_cmd"; then
      _onboard_ok=true
      break
    fi

    log_warn "Onboarding attempt $((_onboard_retries + 1)) failed or timed out."
    _onboard_retries=$((_onboard_retries + 1))
  done

  if ! "$_onboard_ok"; then
    log_error "Onboarding failed after $_onboard_max_retries retries."
    log_error "Try destroying manually first: nemohermes $SANDBOX_NAME destroy --yes"
    exit 1
  fi

  log_success "Hermes onboarding completed!"
  echo ""

  # Apply network policy presets from the blueprint's presets/ directory.
  local preset_dir="$sandbox_dir/milimo-blueprint/policies/presets"
  if [[ -d "$preset_dir" ]]; then
    log_info "Applying network policy presets from $preset_dir..."
    local preset_failed=0
    for preset_file in "$preset_dir"/*.yaml; do
      [[ -f "$preset_file" ]] || continue
      local preset_name
      preset_name=$(basename "$preset_file" .yaml)
      log_info "Applying preset: $preset_name"
      if ! nemohermes "$SANDBOX_NAME" policy-add --from-file "$preset_file" --yes 2>&1; then
        log_warn "Preset $preset_name did not apply (collision or invalid). Check 'nemohermes $SANDBOX_NAME policy-list'."
        preset_failed=1
      fi
    done
    if [[ "$preset_failed" -eq 0 ]]; then
      log_success "All network policy presets applied!"
    else
      log_warn "Some presets may not have applied. Check 'nemohermes $SANDBOX_NAME policy-list'."
    fi
  fi

  setup_link_cli_auth

  # ── Post-onboarding: reliable port forwarding ─────────────────────────
  # The dashboard socat inside the sandbox lands on 18790 (not 18789) when
  # --tui mode is active.  SSH-based forward to 18789 connects to nothing.
  # We forward 18790 (dashboard socat) and 9090 (war room server) using
  # openshell forward start --background, which creates an SSH tunnel via
  # the OpenShell gateway proxy.  Each forward has a 15s timeout so a
  # single stuck tunnel cannot block the install script.
  log_info "Setting up port forwarding..."

  # Stop stale forwards from previous sandbox instances
  for _port in 18789 18790 9090; do
    timeout 5 openshell forward stop "$_port" "$SANDBOX_NAME" 2>/dev/null || true
  done
  sleep 1

  # Dashboard: SSH tunnel to socat on 18790 (forwards to dashboard on 19119)
  if timeout 15 openshell forward start --background 18790 "$SANDBOX_NAME" >/dev/null 2>&1; then
    log_success "  Dashboard: http://127.0.0.1:18790/"
  else
    log_warn "  Dashboard forward failed — run: openshell forward start --background 18790 $SANDBOX_NAME"
  fi

  # War Room: SSH tunnel to war room server on 9090
  if timeout 15 openshell forward start --background 9090 "$SANDBOX_NAME" >/dev/null 2>&1; then
    log_success "  War Room: http://127.0.0.1:9090/warroom.html"
  else
    log_warn "  War Room forward failed — run: openshell forward start --background 9090 $SANDBOX_NAME"
  fi

  log_info "Port forwarding setup complete."

  log_info "Next steps:"
  log_info "  1. Connect: nemohermes $SANDBOX_NAME connect"
  log_info "  2. Access dashboard: http://127.0.0.1:18789/"
  log_info "  3. Change model: nemohermes inference set --model <model> --provider <provider> --sandbox $SANDBOX_NAME"
  log_info "  4. OpenAI-compatible API: http://127.0.0.1:8642/v1"

  if [[ -n "$CHAT_UI_URL" ]]; then
    log_info "  5. Remote dashboard: $CHAT_UI_URL"
  fi

  if [[ "$HEADLESS" == "true" && -z "$CHAT_UI_URL" ]]; then
    log_info "  5. SSH tunnel: ssh -L 18790:127.0.0.1:18790 $(whoami)@$(hostname -f)"
  fi

  log_info "  6. Nous Portal login (interactive): nemohermes $SANDBOX_NAME exec --tty -- hermes setup --portal"
}

main "$@"
