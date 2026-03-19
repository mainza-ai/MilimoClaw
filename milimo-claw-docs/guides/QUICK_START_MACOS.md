# Milimo Claw — Quick Start Guide (macOS Docker)

> Get Milimo Claw running on macOS using Docker with cloud inference.

---

## Overview

This guide gets you running Milimo Claw on macOS using Docker. Since local GPU inference (MLX/NIM) isn't available from Docker containers on macOS, we use cloud inference with NVIDIA Nemotron.

**Time required:** ~10 minutes

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **macOS** | macOS 12+ (Monterey or later) |
| **Docker Desktop** | Latest version, running |
| **Node.js** | v20.0.0 or later |
| **Git** | Latest version |
| **NVIDIA API Key** | Free tier available at [NVIDIA Build](https://build.nvidia.com/) |

---

## Step 1: Get NVIDIA API Key

1. Go to [https://build.nvidia.com/](https://build.nvidia.com/)
2. Sign in or create an account
3. Navigate to **API Keys** section
4. Generate a new API key
5. Copy the key for later use

> **Note:** Free tier includes generous monthly token limits for testing.

---

## Step 2: Clone & Install

```bash
# Clone the repository
git clone https://github.com/mainza-ai/MilimoClaw.git
cd MilimoClaw

# Install dependencies
npm install

# Build the plugin
npm run build -w milimo
```

---

## Step 3: Build the Docker Image

```bash
# Build the Milimo Claw Docker image
docker build -t milimo-claw:latest .

# Verify the build
docker images | grep milimo-claw
```

---

## Step 4: Configure Environment

Set your NVIDIA API key as an environment variable:

```bash
# Set NVIDIA API key (replace with your actual key)
export NVIDIA_API_KEY=nvapi-xxxx-your-key-here

# Verify it's set
echo $NVIDIA_API_KEY
```

Create a `.env` file in the project root for additional configuration:

```bash
# Create .env file
cat > .env << 'EOF'
# Milimo Claw Configuration
MILIMO_ENV=development
MILIMO_LOG_LEVEL=debug

# Solo Founder Mode (Docker Testing)
MILIMO_SOLO_MODE=true
MILIMO_DOCKER_TESTING=true
EOF
```

---

## Step 5: Run Milimo Claw

### Basic Run

```bash
# Run with NVIDIA API key (must be set in environment)
docker run -d --name MilimoClaw \
  --entrypoint "/bin/sh" \
  -e NVIDIA_API_KEY=$NVIDIA_API_KEY \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.nemoclaw:/root/.nemoclaw \
  milimo-claw:latest -c "sleep infinity"

# Inside the container, verify installation
openclaw --version
openclaw milimo --help
```

### Run with Full Configuration

```bash
# Run with all mounts and environment
docker run -d --name MilimoClaw \
  --entrypoint "/bin/sh" \
  -e NVIDIA_API_KEY=$NVIDIA_API_KEY \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.nemoclaw:/root/.nemoclaw \
  -v $(pwd)/milimo-blueprint:/opt/milimo-blueprint:ro \
  milimo-claw:latest -c "sleep infinity"
```

### Verify Container is Running

```bash
# Check container status
docker ps | grep MilimoClaw

# Check container logs
docker logs MilimoClaw --tail 20

# Enter the container
docker exec -it MilimoClaw bash

# Inside the container, verify installation
openclaw --version
openclaw plugins list
```

---

## Step 6: Onboard MilimoClaw

Inside the Docker container:

```bash
# Run the onboarding wizard
openclaw milimo onboard

# Or non-interactive setup
openclaw milimo onboard --squad solo --role content --template solo-founder --solo

# Verify onboarding
openclaw milimo squad onboard-status

# Launch the War Room
openclaw milimo warroom
```

**Onboarding wizard steps:**

1. **NemoClaw Check** — Verifies inference is configured
2. **Template Selection** — Choose `solo-founder` for single operator
3. **Solo/Mesh Mode** — Confirm solo mode
4. **Squad Name** — Enter a unique squad name
5. **Role Assignment** — Select your primary claw role
6. **Operator Name** — Enter your name
7. **War Room Mode** — Choose `full`, `minimal`, or `disabled`
8. **Confirmation** — Review and apply

---

## Step 7: Verify Installation

```bash
# Check onboarding status
openclaw milimo squad onboard-status

# Check squad status
openclaw milimo squad status

# Verify solo founder template loaded
cat ~/.milimo/config.json
```

---

## Common Commands

### Outside Docker

```bash
# Run tests
npm test

# Run Python tests
cd milimo-blueprint && python3 -m pytest tests/test_solo_*.py -v

# Build Docker image
docker build -t milimo-claw:latest .

# Run container
docker run -it --rm -e NVIDIA_API_KEY=$NVIDIA_API_KEY milimo-claw:latest
```

### Inside Docker Container

```bash
# Check onboarding status
openclaw milimo squad onboard-status

# Check squad status
openclaw milimo squad status

# View War Room
openclaw milimo warroom

# Activate deep work mode
openclaw milimo squad finals-mode --resume-date 2026-04-01

# View logs
cat ~/.milimo/logs/warroom.log

# Re-run onboarding (will prompt to reconfigure)
openclaw milimo onboard
```

---

## Troubleshooting

### Docker Issues

**Problem:** Docker build fails

```bash
# Ensure Docker Desktop is running
docker info

# Prune and rebuild
docker system prune -af
docker build --no-cache -t milimo-claw:latest .
```

**Problem:** Container exits immediately

```bash
# Run with interactive mode
docker run -it --rm milimo-claw:latest /bin/bash
```

### API Key Issues

**Problem:** NVIDIA API key not working

```bash
# Verify key is set
echo $NVIDIA_API_KEY

# Test API directly
curl -H "Authorization: Bearer $NVIDIA_API_KEY" \
  https://integrate.api.nvidia.com/v1/models
```

### Inference Issues

**Problem:** No response from model

- Verify API key is valid and has credits
- Check network connectivity
- Review logs: `cat ~/.milimo/logs/*.log`

---

## Configuration Files

| File | Purpose |
|------|---------|
| `solo-founder.yaml` | Solo founder template (cloud mode) |
| `.env` | Environment variables |
| `~/.milimo/logs/` | Log files directory |

---

## Architecture (macOS Docker Mode)

```
┌─────────────────────────────────────────────────────────────┐
│                     macOS Host                               │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Docker Container                        │ │
│  │                                                          │ │
│  │   ┌─────────────────┐     ┌──────────────────────┐     │ │
│  │   │   Milimo Claw   │────▶│  NVIDIA Nemotron API │     │ │
│  │   │   (5 Claws)     │     │  (Cloud Inference)   │     │ │
│  │   └─────────────────┘     └──────────────────────┘     │ │
│  │           │                                            │ │
│  │           ▼                                            │ │
│  │   ┌─────────────────┐                                  │ │
│  │   │    War Room     │                                  │ │
│  │   │  (Single View)  │                                  │ │
│  │   └─────────────────┘                                  │ │
│  │                                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. **Read the Solo Founder Template** - `milimo-blueprint/templates/solo-founder.yaml`
2. **Explore the War Room** - `openclaw milimo warroom`
3. **Review Documentation** - `milimo-claw-docs/reference/SOLO_FOUNDER_TEMPLATE.md`
4. **Run Tests** - Verify everything works

---

## References

- [Solo Founder Template](../reference/SOLO_FOUNDER_TEMPLATE.md)
- [Solo Founder Status](../reports/SOLO_FOUNDER_STATUS.md)
- [Docker Commands](./docker-run-commands.md)
- [Contributing Guide](./CONTRIBUTING.md)
