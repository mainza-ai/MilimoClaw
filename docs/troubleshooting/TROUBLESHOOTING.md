# Troubleshooting Guide

## Quick Diagnostics

```bash
# Check sandbox status
nemoclaw my-assistant status

# Check gateway
openshell gateway info

# Check Docker container
docker ps | grep nemoclaw

# Check port forward
lsof -i :18789
```

---

## Common Issues

### Issue: "No gateway metadata found"

**Cause**: Gateway not configured or onboarding not run.

**Solution**:
```bash
# Run native onboarding on HOST
nemoclaw onboard
```

---

### Issue: "Connection refused" to gateway

**Cause**: Gateway container not running.

**Solution**:
```bash
# Check gateway status
openshell gateway info

# Start gateway if needed
openshell gateway start --name nemoclaw --recreate
```

---

### Issue: Dashboard shows "Disconnected from gateway"

**Cause**: Browser cannot provide mTLS client certificate.

**Solution**: Use TUI instead of web dashboard:
```bash
openshell sandbox connect my-assistant
openclaw tui
```

---

### Issue: Sandbox stuck in "Pending" phase

**Cause**: Gateway not ready or network issues.

**Solution**:
```bash
# Check gateway is running
docker ps | grep openshell-cluster

# Check k3s pods
docker exec openshell-cluster-nemoclaw kubectl get pods -n openshell

# Restart gateway
openshell gateway destroy
nemoclaw onboard
```

---

### Issue: Inference timeout / no response

**Cause**: Model provider not configured or API key invalid.

**Solution**:
```bash
# Check inference config
openshell inference get

# Verify API key
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://integrate.api.nvidia.com/v1/models

# Reconfigure inference (inside sandbox)
openclaw nemoclaw onboard --endpoint build \
  --api-key "$NVIDIA_API_KEY" \
  --model "nvidia/nemotron-3-super-120b-a12b"
```

---

### Issue: "Network namespace creation failed"

**Cause**: macOS cannot pass kernel capabilities to containers.

**Solution**: This is a macOS limitation. Use cloud inference or deploy on native Linux.

Workaround for development:
```bash
# Use MilimoClaw container directly (reduced security)
# See docs/setup-guide.md for alternative setup
```

---

### Issue: Plugin not found

**Cause**: MilimoClaw plugin not installed in sandbox.

**Solution**:
```bash
# Check existing plugins
openclaw plugins list

# Install plugin
openclaw plugins install /tmp/milimo
```

---

### Issue: Port forward not working

**Cause**: Port conflict or forward not started.

**Solution**:
```bash
# Stop existing forward
openshell forward stop 18789

# Start forward
openshell forward start --background 18789 my-assistant

# Verify
lsof -i :18789
```

---

## Diagnostic Commands

### Check Full Stack

```bash
# Gateway
openshell gateway info
docker ps | grep nemoclaw

# Sandbox
nemoclaw list
nemoclaw my-assistant status

# Inference
openshell inference get

# Port forward
openshell forward list

# k3s (inside gateway container)
docker exec openshell-cluster-nemoclaw kubectl get pods -n openshell
docker exec openshell-cluster-nemoclaw kubectl get svc -n openshell
```

### Check Logs

```bash
# Gateway logs
docker logs openshell-cluster-nemoclaw --tail 50

# Sandbox logs (inside sandbox)
cat ~/.openclaw/logs/*.log
```

---

## Architecture Reference

```
HOST (macOS)
├── openshell-cluster-nemoclaw (Docker)
│   └── k3s
│       ├── openshell-0 (gateway pod)
│       └── my-assistant (sandbox pod)
│
└── Port forward: 127.0.0.1:18789 → my-assistant
```

---

## Related Documentation

- [Native vs Plugin Onboarding](./NATIVE_VS_PLUGIN_ONBOARDING.md)
- [Quick Start Guide](../QUICK_START.md)
- [Setup Guide](../setup-guide.md)
