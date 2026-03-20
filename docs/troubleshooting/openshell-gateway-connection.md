# OpenShell Gateway Connection Troubleshooting

## Problem: MilimoClaw Container Cannot Connect to Gateway

### Symptoms
- `openclaw nemoclaw onboard` fails with "No active gateway"
- `openshell gateway info` shows "No gateway metadata found"
- TLS certificate errors when connecting to gateway
- "Connection refused" or "DNS error" when accessing gateway

---

## Solution Overview

The MilimoClaw container needs to connect to the OpenShell gateway running in `openshell-cluster-nemoclaw`. This requires:

1. **Network connectivity** - Container must be on the same Docker network as the gateway
2. **Gateway configuration** - OpenShell config files with correct metadata and TLS certs
3. **DNS resolution** - `/etc/hosts` entries for gateway DNS names
4. **Environment variables** - `HOME` and `OPENSHELL_GATEWAY` properly set

---

## Step-by-Step Fix

### 1. Connect Container to Gateway Network

```bash
# Check gateway container network
docker inspect openshell-cluster-nemoclaw | jq '.[0].NetworkSettings.Networks'

# Connect MilimoClaw to the gateway's network
docker network connect openshell-cluster-nemoclaw MilimoClaw

# Verify connection
docker inspect MilimoClaw | jq '.[0].NetworkSettings.Networks'
```

### 2. Get Gateway IP and Port

```bash
# Get gateway container IP
GATEWAY_IP=$(docker inspect openshell-cluster-nemoclaw | jq -r '.[0].NetworkSettings.Networks["openshell-cluster-nemoclaw"].IPAddress')

# Check gateway service port (look for NodePort)
docker exec openshell-cluster-nemoclaw kubectl get svc -n openshell

# Output example:
# NAME       TYPE      CLUSTER-IP      EXTERNAL-IP   PORT(S)
# openshell  NodePort  10.43.60.117    <none>        8080:30051/TCP
# 
# Use port 30051 (NodePort) for external access
```

### 3. Create OpenShell Configuration Directory

```bash
docker exec MilimoClaw mkdir -p /sandbox/.config/openshell/gateways/nemoclaw
```

### 4. Create Gateway Metadata File

```bash
# The gateway endpoint must use a DNS name that matches the TLS certificate
# Valid names: openshell, openshell.openshell.svc, openshell.openshell.svc.cluster.local, localhost, host.docker.internal

docker exec MilimoClaw bash -c 'cat > /sandbox/.config/openshell/gateways/nemoclaw/metadata.json << EOF
{
  "name": "nemoclaw",
  "gateway_endpoint": "https://openshell.openshell.svc.cluster.local:30051",
  "is_remote": false,
  "gateway_port": 30051
}
EOF'
```

### 5. Copy TLS Certificates from Host

```bash
# Copy the mTLS certificates from host to container
docker cp ~/.config/openshell/gateways/nemoclaw/mtls/ MilimoClaw:/sandbox/.config/openshell/gateways/nemoclaw/

# Fix permissions
docker exec -u root MilimoClaw chown -R sandbox:sandbox /sandbox/.config/openshell/
docker exec -u root MilimoClaw chmod -R 755 /sandbox/.config/openshell/gateways/nemoclaw/
```

### 6. Add DNS Resolution

```bash
# Add /etc/hosts entry for gateway DNS name
docker exec -u root MilimoClaw bash -c 'echo "172.18.0.2 openshell.openshell.svc.cluster.local openshell openshell.openshell.svc" >> /etc/hosts'

# Replace 172.18.0.2 with actual gateway IP from step 2
```

### 7. Set Active Gateway

```bash
docker exec MilimoClaw bash -c 'HOME=/sandbox && echo "nemoclaw" > ~/.config/openshell/active_gateway'
```

### 8. Verify Gateway Connection

```bash
# Test with curl first
docker exec MilimoClaw curl -sk https://openshell.openshell.svc.cluster.local:30051/

# Verify OpenShell can find the gateway
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openshell gateway info'
```

### 9. Run NemoClaw Onboarding

```bash
# Run onboarding with CLI options (non-interactive)
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openclaw nemoclaw onboard \
  --endpoint build \
  --api-key "nvapi-YOUR-API-KEY" \
  --model "nvidia/nemotron-3-super-120b-a12b"'
```

---

## Common Errors and Solutions

### Error: "No gateway metadata found"

**Cause**: OpenShell can't find the gateway config

**Solution**: 
1. Ensure `HOME=/sandbox` is set (OpenShell looks for `$HOME/.config/openshell/`)
2. Verify metadata.json exists at `/sandbox/.config/openshell/gateways/nemoclaw/metadata.json`
3. Check JSON is valid and properly formatted

### Error: "certificate not valid for name X"

**Cause**: Gateway endpoint uses IP address or wrong DNS name

**Solution**: Use DNS names that match the TLS certificate:
- `openshell.openshell.svc.cluster.local`
- `openshell.openshell.svc`
- `openshell`
- `localhost`
- `host.docker.internal`

### Error: "Connection refused"

**Cause**: Wrong port number

**Solution**: Use the NodePort (30051), not the internal port (8080):
```bash
# Check the NodePort
docker exec openshell-cluster-nemoclaw kubectl get svc -n openshell
# Look for: 8080:30051/TCP -> use 30051
```

### Error: "Name does not resolve"

**Cause**: DNS name not resolving inside container

**Solution**: Add `/etc/hosts` entry:
```bash
docker exec -u root MilimoClaw bash -c 'echo "GATEWAY_IP openshell.openshell.svc.cluster.local" >> /etc/hosts'
```

### Error: "Failed to create provider: transport error"

**Cause**: Combination of wrong endpoint, port, or missing TLS certs

**Solution**: Go through all steps above systematically

---

## Key Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| Gateway metadata | `/sandbox/.config/openshell/gateways/nemoclaw/metadata.json` | Gateway connection info |
| TLS certs | `/sandbox/.config/openshell/gateways/nemoclaw/mtls/` | Client authentication |
| Active gateway | `/sandbox/.config/openshell/active_gateway` | Which gateway to use |
| OpenClaw config | `/sandbox/.openclaw/openclaw.json` | Models, providers, agents |
| Agent models | `/sandbox/.openclaw/agents/main/agent/models.json` | Model configurations |

---

## Environment Variables Required

```bash
HOME=/sandbox                          # Required for OpenShell to find config
OPENSHELL_GATEWAY=nemoclaw            # Optional, overrides active gateway
NVIDIA_API_KEY=nvapi-xxx              # API key for inference
```

---

## Verification Checklist

- [ ] Container connected to gateway network (`docker network connect`)
- [ ] Gateway IP identified (`docker inspect`)
- [ ] NodePort identified (30051, not 8080)
- [ ] OpenShell config directory created
- [ ] metadata.json created with correct DNS name and port
- [ ] TLS certificates copied from host
- [ ] Permissions fixed (chown/chmod)
- [ ] /etc/hosts entry added
- [ ] active_gateway file created
- [ ] `openshell gateway info` shows gateway
- [ ] Onboarding completed successfully

---

## Quick Reference Commands

```bash
# Full setup in one script (run after container is connected to network)
docker exec MilimoClaw mkdir -p /sandbox/.config/openshell/gateways/nemoclaw

docker exec MilimoClaw bash -c 'cat > /sandbox/.config/openshell/gateways/nemoclaw/metadata.json << EOF
{"name":"nemoclaw","gateway_endpoint":"https://openshell.openshell.svc.cluster.local:30051","is_remote":false,"gateway_port":30051}
EOF'

docker cp ~/.config/openshell/gateways/nemoclaw/mtls/ MilimoClaw:/sandbox/.config/openshell/gateways/nemoclaw/
docker exec -u root MilimoClaw chown -R sandbox:sandbox /sandbox/.config/openshell/
docker exec -u root MilimoClaw chmod -R 755 /sandbox/.config/openshell/gateways/nemoclaw/

GATEWAY_IP=$(docker inspect openshell-cluster-nemoclaw | jq -r '.[0].NetworkSettings.Networks["openshell-cluster-nemoclaw"].IPAddress')
docker exec -u root MilimoClaw bash -c "echo '$GATEWAY_IP openshell.openshell.svc.cluster.local openshell' >> /etc/hosts"

docker exec MilimoClaw bash -c 'HOME=/sandbox && echo "nemoclaw" > ~/.config/openshell/active_gateway'

# Verify
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openshell gateway info'

# Onboard
docker exec MilimoClaw bash -c 'HOME=/sandbox && export HOME && openclaw nemoclaw onboard --endpoint build --api-key "$NVIDIA_API_KEY" --model "nvidia/nemotron-3-super-120b-a12b"'
```

---

## Related Documentation

- [NemoClaw Comparison Insights](../../nemoclaw-comparison-insights.md)
- [OpenShell Gateway Documentation](https://github.com/NVIDIA/OpenShell)
- [NemoClaw README](https://github.com/NVIDIA/NemoClaw)
