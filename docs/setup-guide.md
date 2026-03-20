# MilimoClaw Setup Guide

## Quick Start

### Prerequisites

- Docker Desktop or Colima running
- OpenShell CLI installed on host (`~/.local/bin/openshell`)
- NVIDIA API key from [build.nvidia.com](https://build.nvidia.com)
- Gateway running (`openshell-cluster-nemoclaw` container)

### 1. Start the Gateway

```bash
# On host machine
export PATH="$HOME/.local/bin:$PATH"
export NVIDIA_API_KEY="nvapi-your-key-here"

openshell gateway start --name nemoclaw --recreate
```

### 2. Build Plugins

```bash
cd /path/to/MilimoClaw

# Build nemoclaw
cd nemoclaw && npm run build && cd ..

# Build milimo  
cd milimo && npm run build && cd ..
```

### 3. Run MilimoClaw Container

```bash
# Use the provided script
./scripts/run-milimo-docker.sh

# Or manually:
docker run -d --name MilimoClaw \
  --entrypoint "/bin/sh" \
  -e NVIDIA_API_KEY="nvapi-your-key-here" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.nemoclaw:/root/.nemoclaw \
  milimo-claw:latest \
  -c "sleep infinity"
```

### 4. Connect Container to Gateway Network

```bash
docker network connect openshell-cluster-nemoclaw MilimoClaw
```

### 5. Configure Gateway Connection

```bash
# Get gateway IP
GATEWAY_IP=$(docker inspect openshell-cluster-nemoclaw | jq -r '.[0].NetworkSettings.Networks["openshell-cluster-nemoclaw"].IPAddress')

# Create config directory
docker exec MilimoClaw mkdir -p /sandbox/.config/openshell/gateways/nemoclaw

# Create metadata (use NodePort 30051, not 8080)
docker exec MilimoClaw bash -c 'cat > /sandbox/.config/openshell/gateways/nemoclaw/metadata.json << EOF
{"name":"nemoclaw","gateway_endpoint":"https://openshell.openshell.svc.cluster.local:30051","is_remote":false,"gateway_port":30051}
EOF'

# Copy TLS certificates
docker cp ~/.config/openshell/gateways/nemoclaw/mtls/ MilimoClaw:/sandbox/.config/openshell/gateways/nemoclaw/

# Fix permissions
docker exec -u root MilimoClaw chown -R sandbox:sandbox /sandbox/.config/openshell/
docker exec -u root MilimoClaw chmod -R 755 /sandbox/.config/openshell/gateways/nemoclaw/

# Add DNS resolution
docker exec -u root MilimoClaw bash -c "echo '$GATEWAY_IP openshell.openshell.svc.cluster.local openshell' >> /etc/hosts"

# Set active gateway
docker exec MilimoClaw bash -c 'HOME=/sandbox && echo "nemoclaw" > ~/.config/openshell/active_gateway'
```

### 6. Verify Gateway Connection

```bash
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openshell gateway info'
# Should show:
# Gateway: nemoclaw
# Gateway endpoint: https://openshell.openshell.svc.cluster.local:30051
```

### 7. Run NemoClaw Onboarding

```bash
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openclaw nemoclaw onboard \
  --endpoint build \
  --api-key "$NVIDIA_API_KEY" \
  --model "nvidia/nemotron-3-super-120b-a12b"'
```

### 8. Run MilimoClaw Onboarding

```bash
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openclaw milimo onboard'
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HOST MACHINE                                 │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  openshell-cluster-nemoclaw (Gateway Container)              │    │
│  │  - k3s Kubernetes                                            │    │
│  │  - openshell-0 pod (gateway service)                         │    │
│  │  - NodePort 30051 → 8080                                     │    │
│  │  - IP: 172.18.0.2                                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              │ Docker Network: openshell-cluster-nemoclaw
│                              │                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  MilimoClaw Container                                        │    │
│  │  - OpenClaw + NemoClaw + MilimoClaw plugins                 │    │
│  │  - OpenShell CLI (for gateway connection)                   │    │
│  │  - IP: 172.18.0.3                                           │    │
│  │  - Connects to gateway at: openshell.openshell.svc:30051   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Ports

| Port | Service | Notes |
|------|---------|-------|
| 30051 | Gateway NodePort | External access to gateway |
| 8080 | Gateway Internal | Only accessible inside k3s cluster |
| 18789 | OpenClaw Gateway | Local WebSocket gateway |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `/sandbox/.config/openshell/gateways/nemoclaw/metadata.json` | Gateway connection config |
| `/sandbox/.config/openshell/gateways/nemoclaw/mtls/` | TLS certificates |
| `/sandbox/.openclaw/openclaw.json` | OpenClaw main config |
| `/sandbox/.openclaw/agents/main/agent/models.json` | Model configurations |

---

## Troubleshooting

See [Gateway Connection Troubleshooting](./troubleshooting/openshell-gateway-connection.md)

---

## Notes

- Always use NodePort (30051) for connections from outside k3s
- Gateway DNS name must match TLS certificate (use `openshell.openshell.svc.cluster.local`)
- Environment variable `HOME=/sandbox` is required for OpenShell to find config
- The MilimoClaw container itself acts as the "sandbox" - no separate sandbox pod needed
