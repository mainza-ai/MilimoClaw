# MilimoClaw sandbox image — built on top of NVIDIA NemoClaw sandbox-base
#
# IMPORTANT: This Dockerfile is designed for nemoclaw onboard --from.
# NemoClaw provides the OpenShell security sandbox (Landlock, seccomp,
# netns, policy engine, gateway credential injection). Milimo adds
# multi-agent coordination, War Room, and blueprint economy on top.
#
# Do NOT run this image standalone (docker compose / docker run).
# The claws REQUIRE NemoClaw's orchestration — without the OpenShell
# gateway, inference routing, policy presets, and credential injection
# provided by nemoclaw onboard, the isolation model is incomplete.
#
# Supported deployment:
#   ./install.sh --solo --operator-name "name" --squad-name "squad"
# This generates a build context and runs nemoclaw onboard --from.
#
# Architecture:
#   Stage 1: Build Milimo TypeScript plugin
#   Stage 2: Layer Milimo plugin + blueprint on top of NemoClaw base

# ---------------------------------------------------------------------------
# Stage 1: Build Milimo TypeScript plugin
# ---------------------------------------------------------------------------
FROM node:22-slim AS milimo-builder
COPY milimo/package.json milimo/tsconfig.json /opt/milimo/
COPY milimo/src/ /opt/milimo/src/
WORKDIR /opt/milimo
RUN npm install && npm run build

# ---------------------------------------------------------------------------
# Stage 2: Runtime — NemoClaw sandbox base + Milimo
# ---------------------------------------------------------------------------
ARG SANDBOX_BASE=ghcr.io/nvidia/nemoclaw/sandbox-base:latest
FROM ${SANDBOX_BASE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV HOME=/sandbox

# Install additional Python dependencies for Milimo orchestrator
# hadolint ignore=DL3013,DL3042,DL3059
RUN pip3 install --no-cache-dir --break-system-packages pyyaml pytest requests httpx stripe

# Install GitHub CLI (gh) — required by the OpenClaw GitHub skill
# hadolint ignore=DL3008
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# Copy built Milimo plugin and blueprint
COPY --from=milimo-builder /opt/milimo/dist/ /opt/milimo/dist/
COPY milimo/openclaw.plugin.json /opt/milimo/
COPY milimo/package.json /opt/milimo/
COPY milimo-blueprint/ /opt/milimo-blueprint/
COPY test/ /opt/milimo/test/

# Install runtime dependencies for Milimo plugin
WORKDIR /opt/milimo
RUN npm install --omit=dev

# Create Milimo claw data directories under unified .openclaw layout
RUN BASE="/sandbox/.openclaw/milimo/claws" \
    && mkdir -p "$BASE/ops/clients/active" "$BASE/ops/clients/archived" \
    && mkdir -p "$BASE/ops/projects/active" "$BASE/ops/projects/completed" \
    && mkdir -p "$BASE/ops/calendar" "$BASE/ops/queue/hold" "$BASE/ops/queue/review" "$BASE/ops/queue/auto" \
    && mkdir -p "$BASE/ops/memory" "$BASE/ops/context" "$BASE/ops/logs" "$BASE/ops/tools" \
    && mkdir -p "$BASE/content/drafts/pending" "$BASE/content/drafts/approved" "$BASE/content/drafts/rejected" \
    && mkdir -p "$BASE/content/calendar" "$BASE/content/queue/hold" "$BASE/content/queue/review" "$BASE/content/queue/auto" \
    && mkdir -p "$BASE/content/memory" "$BASE/content/context" "$BASE/content/logs" "$BASE/content/tools" \
    && mkdir -p "$BASE/analytics/reports/daily" "$BASE/analytics/reports/weekly" "$BASE/analytics/reports/monthly" \
    && mkdir -p "$BASE/analytics/metrics" "$BASE/analytics/queue/hold" "$BASE/analytics/queue/review" "$BASE/analytics/queue/auto" \
    && mkdir -p "$BASE/analytics/memory" "$BASE/analytics/context" "$BASE/analytics/logs" "$BASE/analytics/tools" \
    && mkdir -p "$BASE/finance/invoices/draft" "$BASE/finance/invoices/sent" "$BASE/finance/invoices/paid" "$BASE/finance/invoices/overdue" \
    && mkdir -p "$BASE/finance/expenses" "$BASE/finance/revenue" \
    && mkdir -p "$BASE/finance/queue/hold" "$BASE/finance/queue/review" "$BASE/finance/queue/auto" \
    && mkdir -p "$BASE/finance/memory" "$BASE/finance/context" "$BASE/finance/logs" "$BASE/finance/tools" \
    && mkdir -p "$BASE/build/prs/open" "$BASE/build/prs/merged" "$BASE/build/prs/closed" \
    && mkdir -p "$BASE/build/deployments/staging" "$BASE/build/deployments/production" \
    && mkdir -p "$BASE/build/tasks" "$BASE/build/docs" "$BASE/build/context" "$BASE/build/data" \
    && mkdir -p "$BASE/build/queue/hold" "$BASE/build/queue/review" "$BASE/build/queue/auto" \
    && mkdir -p "$BASE/build/memory" "$BASE/build/logs" "$BASE/build/tools" \
    && mkdir -p "$BASE/assistant/context" "$BASE/assistant/memory" "$BASE/assistant/logs" "$BASE/assistant/tools" \
    && mkdir -p "$BASE/assistant/queue/hold" "$BASE/assistant/queue/review" "$BASE/assistant/queue/auto" \
    && mkdir -p /sandbox/.openclaw/milimo/mesh/heartbeats \
    && mkdir -p /sandbox/.openclaw/milimo/mesh/inboxes \
    && mkdir -p /sandbox/.openclaw/milimo/mesh/alerts \
    && mkdir -p /sandbox/.openclaw/milimo/blueprints \
    && ln -sfn /sandbox/.openclaw/milimo/milimo-blueprint /sandbox/.openclaw/milimo/blueprints/0.1.0 \
    && rm -rf /sandbox/.milimo 2>/dev/null || true \
    && ln -sfn /sandbox/.openclaw/milimo /sandbox/.milimo \
    && chown -R sandbox:sandbox /sandbox/.openclaw/milimo /sandbox/.milimo 2>/dev/null || true

# Build args — injected by nemoclaw onboard, fall back to env vars
# NEMOCLAW_MODEL is set by the user during nemoclaw onboard (model selection step).
# The fallback value mirrors NemoClaw's own default — override at build time via
# nemoclaw onboard or --build-arg.
ARG NEMOCLAW_MODEL=nvidia/nemotron-3-super-120b-a12b
ARG CHAT_UI_URL=http://127.0.0.1:18789
ARG MILIMO_BUILD_ID=default

ENV MILIMO_MODEL=${NEMOCLAW_MODEL} \
    CHAT_UI_URL=${CHAT_UI_URL}

COPY scripts/milimo-start.sh /usr/local/bin/milimo-start
RUN chmod +x /usr/local/bin/milimo-start

WORKDIR /sandbox
USER sandbox

# Generate openclaw.json with inference + gateway config.
# Model and provider are injected via NEMOCLAW_MODEL (build arg from onboard).
RUN python3 <<'PYEOF'
import json, os, secrets
from urllib.parse import urlparse
model = os.environ['MILIMO_MODEL']
chat_ui_url = os.environ.get('CHAT_UI_URL', 'http://127.0.0.1:18789')
parsed = urlparse(chat_ui_url)
chat_origin = f'{parsed.scheme}://{parsed.netloc}' if parsed.scheme and parsed.netloc else 'http://127.0.0.1:18789'
origins = ['http://127.0.0.1:18789']
origins = list(dict.fromkeys(origins + [chat_origin]))
config = {
    'agents': {
        'defaults': {
            'model': {'primary': f'inference/{model}'},
            'contextPruning': {
                'mode': 'cache-ttl',
                'ttl': '4h',
                'minPrunableToolChars': 4096,
                'softTrim': {
                    'maxChars': 8192,
                    'headChars': 4096,
                    'tailChars': 4096
                }
            },
            'compaction': {
                'mode': 'safeguard',
                'reserveTokens': 8192,
                'keepRecentTokens': 16384,
                'recentTurnsPreserve': 4,
                'truncateAfterCompaction': True,
                'notifyUser': True,
                'memoryFlush': {
                    'enabled': True,
                    'softThresholdTokens': 4096
                }
            }
        }
    },
    'models': {'mode': 'merge', 'providers': {
        'nvidia': {
            'baseUrl': 'https://inference.local/v1',
            'apiKey': 'openshell-managed',
            'api': 'openai-completions',
            'models': [{'id': model.split('/')[-1], 'name': model, 'reasoning': False, 'input': ['text'], 'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0}, 'contextWindow': 65536, 'maxTokens': 4096}]
        },
        'inference': {
            'baseUrl': 'https://inference.local/v1',
            'apiKey': 'unused',
            'api': 'openai-completions',
            'models': [{'id': model, 'name': model, 'reasoning': False, 'input': ['text'], 'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0}, 'contextWindow': 65536, 'maxTokens': 4096}]
        }
    }},
    'channels': {'defaults': {'configWrites': False}},
    'gateway': {
        'mode': 'local',
        'controlUi': {
            'allowInsecureAuth': True,
            'dangerouslyDisableDeviceAuth': True,
            'allowedOrigins': origins,
        },
        'trustedProxies': ['127.0.0.1', '::1'],
        'auth': {'token': secrets.token_hex(32)}
    }
}
path = os.path.expanduser('~/.openclaw/openclaw.json')
json.dump(config, open(path, 'w'), indent=2)
os.chmod(path, 0o600)
PYEOF

# Install Milimo plugin into OpenClaw + GitHub skill.
# Follows NemoClaw's own plugin install pattern (openclaw plugins install).
RUN openclaw doctor --fix > /dev/null 2>&1 || true \
    && openclaw plugins install /opt/milimo > /dev/null 2>&1 || true \
    && openclaw skills install github > /dev/null 2>&1 || true

# Health check — verifies sandbox runtime AND Milimo Claw heartbeat
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
CMD openshell --version && openclaw --version && \
python3 -c 'import os,time,sys,glob;hb=os.path.expanduser("~/.openclaw/milimo/mesh/heartbeats");fs=glob.glob(os.path.join(hb,"*.json"));sys.exit(0 if fs and time.time()-os.path.getmtime(max(fs,key=os.path.getmtime))<90 else 1)' 2>/dev/null || exit 1

# Lock openclaw.json via DAC (as root)
USER root
RUN chown root:root /sandbox/.openclaw \
    && find /sandbox/.openclaw -mindepth 1 -maxdepth 1 -exec chown -h root:root {} + \
    && chmod 1777 /sandbox/.openclaw \
    && chmod 444 /sandbox/.openclaw/openclaw.json
USER sandbox

WORKDIR /opt/nemoclaw
ENTRYPOINT []
CMD []
