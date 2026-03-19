# MilimoClaw sandbox image — OpenShell + NemoClaw + MilimoClaw
# Based on official NemoClaw/OpenShell architecture

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/sandbox

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (required by openclaw@2026.3.11)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenShell CLI binary (from NVIDIA OpenShell releases)
RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
        x86_64|amd64) ASSET="openshell-x86_64-unknown-linux-musl.tar.gz" ;; \
        aarch64|arm64) ASSET="openshell-aarch64-unknown-linux-musl.tar.gz" ;; \
    esac && \
    tmpdir=$(mktemp -d) && \
    curl -fsSL "https://github.com/NVIDIA/OpenShell/releases/latest/download/$ASSET" -o "$tmpdir/$ASSET" && \
    tar xzf "$tmpdir/$ASSET" -C "$tmpdir" && \
    install -m 755 "$tmpdir/openshell" /usr/local/bin/openshell && \
    rm -rf "$tmpdir"

# Install OpenClaw CLI
RUN npm install -g openclaw@2026.3.11

# Install Python dependencies for orchestrator
RUN pip3 install pyyaml pytest

# Create sandbox user
RUN groupadd -r sandbox && useradd -r -g sandbox -d /sandbox -s /bin/bash sandbox \
    && mkdir -p /sandbox/.openclaw /sandbox/.milimo /sandbox/.nemoclaw \
    && chown -R sandbox:sandbox /sandbox

# Create plugin directories
RUN mkdir -p /opt/nemoclaw/dist \
    && mkdir -p /opt/milimo/dist \
    && mkdir -p /opt/milimo-blueprint \
    && mkdir -p /opt/nemoclaw-blueprint \
    && mkdir -p /opt/milimo/test

# Copy NemoClaw plugin and blueprint
COPY nemoclaw/dist/ /opt/nemoclaw/dist/
COPY nemoclaw/openclaw.plugin.json /opt/nemoclaw/
COPY nemoclaw/package.json /opt/nemoclaw/
COPY nemoclaw-blueprint/ /opt/nemoclaw-blueprint/

# Copy MilimoClaw plugin and blueprint
COPY milimo/dist/ /opt/milimo/dist/
COPY milimo/openclaw.plugin.json /opt/milimo/
COPY milimo/package.json /opt/milimo/
COPY milimo-blueprint/ /opt/milimo-blueprint/
COPY test/ /opt/milimo/test/

# Install runtime dependencies for both plugins
WORKDIR /opt/nemoclaw
RUN npm install --omit=dev

WORKDIR /opt/milimo
RUN npm install --omit=dev

# Set up blueprints for local resolution
RUN mkdir -p /sandbox/.milimo/blueprints/0.1.0 \
    && cp -r /opt/milimo-blueprint/* /sandbox/.milimo/blueprints/0.1.0/ \
    && mkdir -p /sandbox/.nemoclaw/blueprints/0.1.0 \
    && cp -r /opt/nemoclaw-blueprint/* /sandbox/.nemoclaw/blueprints/0.1.0/ \
    && chown -R sandbox:sandbox /sandbox/.milimo /sandbox/.nemoclaw

WORKDIR /sandbox
USER sandbox

# Pre-create OpenClaw directories
RUN mkdir -p /sandbox/.openclaw/agents/main/agent \
    && chmod 700 /sandbox/.openclaw

# Write openclaw.json for cloud inference mode (macOS Docker testing)
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

# Install NemoClaw and MilimoClaw plugins into OpenClaw
RUN openclaw doctor --fix > /dev/null 2>&1 || true \
    && openclaw plugins install /opt/nemoclaw > /dev/null 2>&1 || true \
    && openclaw plugins install /opt/milimo > /dev/null 2>&1 || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD openshell --version && openclaw --version || exit 1

ENTRYPOINT ["/bin/bash"]
CMD []
