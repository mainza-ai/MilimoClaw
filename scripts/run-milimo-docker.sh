#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

# MilimoClaw Docker Run Script for macOS
# Usage: ./scripts/run-milimo-docker.sh
# Reads configuration from .env file in project root

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== MilimoClaw Docker Runner ===${NC}"

# Load .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

if [ -f "$ENV_FILE" ]; then
  echo -e "${GREEN}Loading environment from .env file...${NC}"
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
else
  echo -e "${YELLOW}No .env file found at $ENV_FILE${NC}"
  echo "Copy .env.example to .env and fill in your values:"
  echo "  cp .env.example .env"
fi

# Check if NVIDIA_API_KEY is set
if [ -z "$NVIDIA_API_KEY" ] || [[ "$NVIDIA_API_KEY" == nvapi-your-key-here ]] || [[ "$NVIDIA_API_KEY" == nvapi-*here ]]; then
  echo -e "${YELLOW}Warning: NVIDIA_API_KEY not configured.${NC}"
  echo ""
  echo "Get your API key from: https://build.nvidia.com/"
  echo ""
  read -p "Enter your NVIDIA API key: " NVIDIA_API_KEY
  if [ -z "$NVIDIA_API_KEY" ]; then
    echo -e "${RED}Error: NVIDIA_API_KEY is required${NC}"
    exit 1
  fi
fi

# Stop and remove existing container if running
if docker ps -a --format '{{.Names}}' | grep -q "^MilimoClaw$"; then
  echo -e "${YELLOW}Stopping existing MilimoClaw container...${NC}"
  docker stop MilimoClaw 2>/dev/null || true
  docker rm MilimoClaw 2>/dev/null || true
fi

# Run the container
echo -e "${GREEN}Starting MilimoClaw container...${NC}"
docker run -d --name MilimoClaw \
  --entrypoint "/bin/sh" \
  -e NVIDIA_API_KEY="$NVIDIA_API_KEY" \
  -e BUILD_CLAW_NVIDIA_API_KEY="$BUILD_CLAW_NVIDIA_API_KEY" \
  -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.nemoclaw:/root/.nemoclaw \
  milimo-claw:latest -c "sleep infinity"

# Wait for container to be healthy
echo -e "${YELLOW}Waiting for container to start...${NC}"
sleep 5

# Check if container is running
if docker ps --format '{{.Names}}' | grep -q "^MilimoClaw$"; then
  echo -e "${GREEN}✓ Container started successfully!${NC}"
  echo ""
  echo "Container status:"
  docker ps --filter name=MilimoClaw --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
  echo ""
  echo -e "${GREEN}Quick commands:${NC}"
  echo "  Enter container:    docker exec -it MilimoClaw bash"
  echo "  Check logs:         docker logs MilimoClaw --tail 50"
  echo "  Stop container:     docker stop MilimoClaw"
  echo ""
  echo -e "${GREEN}Inside the container:${NC}"
  echo "  openclaw --version"
  echo "  openclaw plugins list"
  echo "  cd /sandbox/.milimo/blueprints/0.1.0"
  echo "  python3 -c \"from orchestrator.solo_init import load_solo_founder_template; print('OK')\""
else
  echo -e "${RED}✗ Container failed to start${NC}"
  docker logs MilimoClaw --tail 30
  exit 1
fi
