# MilimoClaw sandbox image — OpenClaw + MilimoClaw plugin inside OpenShell
# Optimized for macOS Docker testing (cloud inference mode)

FROM node:22-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    curl git ca-certificates \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Create sandbox user (matches OpenShell convention)
RUN groupadd -r sandbox && useradd -r -g sandbox -d /sandbox -s /bin/bash sandbox \
    && mkdir -p /sandbox/.openclaw /sandbox/.milimo \
    && chown -R sandbox:sandbox /sandbox

# Install OpenClaw CLI
RUN npm install -g openclaw@2026.3.11

# Install Python dependencies for orchestrator
RUN pip3 install --break-system-packages pyyaml pytest

# Create necessary directories first
RUN mkdir -p /opt/milimo/dist \
    && mkdir -p /opt/milimo-blueprint \
    && mkdir -p /opt/milimo/test

# Copy our plugin and blueprint into the sandbox
COPY milimo/dist/ /opt/milimo/dist/
COPY milimo/openclaw.plugin.json /opt/milimo/
COPY milimo/package.json /opt/milimo/
COPY milimo-blueprint/ /opt/milimo-blueprint/
COPY test/ /opt/milimo/test/

# Install runtime dependencies only (no devDependencies, no build step)
WORKDIR /opt/milimo
RUN npm install --omit=dev

# Set up blueprint for local resolution
RUN mkdir -p /sandbox/.milimo/blueprints/0.1.0 \
    && cp -r /opt/milimo-blueprint/* /sandbox/.milimo/blueprints/0.1.0/ \
    && chown -R sandbox:sandbox /sandbox/.milimo

# Copy startup script
COPY scripts/milimo-start.sh /usr/local/bin/milimo-start
RUN chmod +x /usr/local/bin/milimo-start

WORKDIR /sandbox
USER sandbox

# Pre-create OpenClaw directories
RUN mkdir -p /sandbox/.openclaw/agents/main/agent \
    && chmod 700 /sandbox/.openclaw

# Write openclaw.json for cloud inference mode (macOS Docker testing)
# Uses NVIDIA Nemotron cloud API instead of local inference
# API key is injected at runtime via NVIDIA_API_KEY environment variable
RUN python3 -c "\
import json, os; \
config = { \
    'agents': {'defaults': {'model': {'primary': 'nvidia/nemotron-3-super-120b-a12b'}}}, \
    'models': {'mode': 'merge', 'providers': {'nvidia': { \
        'baseUrl': 'https://integrate.api.nvidia.com/v1', \
        'api': 'openai-completions', \
        'models': [{'id': 'nemotron-3-super-120b-a12b', 'name': 'NVIDIA Nemotron 3 Super 120B', 'reasoning': False, 'input': ['text'], 'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0}, 'contextWindow': 131072, 'maxTokens': 4096}] \
    }}, 'modelAlias': {'nvidia/nemotron-3-super-120b-a12b': 'nvidia/nemotron-3-super-120b-a12b'}}, \
    'providers': {'nvidia': {'apiKeyEnv': 'NVIDIA_API_KEY'}} \
}; \
path = os.path.expanduser('~/.openclaw/openclaw.json'); \
json.dump(config, open(path, 'w'), indent=2); \
os.chmod(path, 0o600)"

# Install MilimoClaw plugin into OpenClaw
RUN openclaw doctor --fix > /dev/null 2>&1 || true \
    && openclaw plugins install /opt/milimo > /dev/null 2>&1 || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD openclaw --version || exit 1

ENTRYPOINT ["/bin/bash"]
CMD []
