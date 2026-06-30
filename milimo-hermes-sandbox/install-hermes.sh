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

  # Check for nemohermes alias
  if ! command -v nemohermes &>/dev/null; then
    log_warn "nemohermes alias not found. Creating alias..."
    alias nemohermes="NEMOCLAW_AGENT=hermes nemoclaw"
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

prepare_build_context() {
  log_info "Preparing build context..."

  local script_path
  script_path="$(realpath "${BASH_SOURCE[0]}")"
  local project_root
  project_root="$(dirname "$(dirname "$script_path")")"
  local sandbox_dir
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
    cmd+=" --fresh"
    export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
    export NEMOCLAW_NON_INTERACTIVE=1
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
  export NEMOCLAW_PROVIDER_KEY="${NEMOCLAW_PROVIDER_KEY:-inference}"
  export NEMOCLAW_INFERENCE_BASE_URL="${NEMOCLAW_INFERENCE_BASE_URL:-https://inference.local/v1}"
  export CHAT_UI_URL="${CHAT_UI_URL:-http://127.0.0.1:8642}"
  export NEMOCLAW_MESSAGING_CHANNELS_B64="${NEMOCLAW_MESSAGING_CHANNELS_B64:-W10=}"
  export NEMOCLAW_MESSAGING_ALLOWED_IDS_B64="${NEMOCLAW_MESSAGING_ALLOWED_IDS_B64:-e30=}"
  export NEMOCLAW_DISCORD_GUILDS_B64="${NEMOCLAW_DISCORD_GUILDS_B64:-e30=}"
  export NEMOCLAW_TELEGRAM_CONFIG_B64="${NEMOCLAW_TELEGRAM_CONFIG_B64:-e30=}"
  export NEMOCLAW_WECHAT_CONFIG_B64="${NEMOCLAW_WECHAT_CONFIG_B64:-e30=}"
  export NEMOCLAW_SLACK_CONFIG_B64="${NEMOCLAW_SLACK_CONFIG_B64:-e30=}"
  export NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER="${NEMOCLAW_HERMES_TOOL_GATEWAY_BROKER:-0}"
  export NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64="${NEMOCLAW_HERMES_TOOL_GATEWAY_PRESETS_B64:-W10=}"
  export NEMOCLAW_BUILD_ID="${NEMOCLAW_BUILD_ID:-default}"
  export NEMOCLAW_DARWIN_VM_COMPAT="${NEMOCLAW_DARWIN_VM_COMPAT:-0}"

  if [[ -n "$SLACK_CHANNELS" ]]; then
    # Convert comma-separated to JSON array, then base64
    local slack_json
    slack_json=$(echo "$SLACK_CHANNELS" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$"; ""))')
    local slack_b64
    slack_b64=$(echo -n "$slack_json" | base64 -w0)
    export NEMOCLAW_SLACK_CONFIG_B64="$slack_b64"
  fi

  prepare_build_context
  build_docker_image

  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "[DRY RUN] Would execute onboarding:"
    log_info "  $onboard_cmd"
    log_info "  Build arg env vars set: NEMOCLAW_MODEL, CHAT_UI_URL, NEMOCLAW_SLACK_CONFIG_B64, etc."
    return 0
  fi

  # Run onboarding
  log_info "Starting Hermes onboarding..."
  log_info "Command: $onboard_cmd"
  echo ""

  if eval "$onboard_cmd"; then
    log_success "Hermes onboarding completed!"
    echo ""
    log_info "Next steps:"
    log_info "  1. Connect: nemohermes $SANDBOX_NAME connect"
    log_info "  2. Access dashboard: http://127.0.0.1:18790/"
    log_info "  3. Change model: nemohermes inference set --model <model> --provider <provider> --sandbox $SANDBOX_NAME"
    log_info "  4. OpenAI-compatible API: http://127.0.0.1:8642/v1"

    if [[ -n "$CHAT_UI_URL" ]]; then
      log_info "  4. Remote dashboard: $CHAT_UI_URL"
    fi

    if [[ "$HEADLESS" == "true" && -z "$CHAT_UI_URL" ]]; then
      log_info "  4. SSH tunnel: ssh -L 18790:127.0.0.1:18790 $(whoami)@$(hostname -f)"
    fi
  else
    log_error "Onboarding failed"
    exit 1
  fi
}

main "$@"
