#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# OpenShell CLI Helper for Intel Mac
# 
# Since OpenShell CLI doesn't support macOS x86_64, this script runs
# the Linux OpenShell CLI in a Docker container that connects to the
# existing openshell-cluster-nemoclaw gateway.
#
# Usage:
#   ./scripts/openshell-cli-helper.sh [openshell commands...]
#   ./scripts/openshell-cli-helper.sh gateway info
#   ./scripts/openshell-cli-helper.sh provider create --name nvidia-nim --type openai ...

set -euo pipefail

IMAGE_NAME="openshell-cli-helper:latest"
CONTAINER_NAME="openshell-cli-helper"

build_if_needed() {
    if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
        echo "Building OpenShell CLI helper image..."
        docker build -t "$IMAGE_NAME" - << 'DOCKERFILE'
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl ca-certificates && rm -rf /var/lib/apt/lists/*
RUN ARCH=$(uname -m) && \
    case "$ARCH" in \
        x86_64|amd64) ASSET="openshell-x86_64-unknown-linux-musl.tar.gz" ;; \
        aarch64|arm64) ASSET="openshell-aarch64-unknown-linux-musl.tar.gz" ;; \
    esac && \
    curl -fsSL "https://github.com/NVIDIA/OpenShell/releases/download/v0.0.11/$ASSET" -o /tmp/openshell.tar.gz && \
    tar xzf /tmp/openshell.tar.gz -C /tmp && \
    mv /tmp/openshell /usr/local/bin/openshell && \
    chmod +x /usr/local/bin/openshell && \
    rm /tmp/openshell.tar.gz
ENTRYPOINT ["openshell"]
DOCKERFILE
    fi
}

# Build image if needed
build_if_needed

# Check if openshell-cluster container is running
if ! docker ps --format '{{.Names}}' | grep -q "^openshell-cluster-nemoclaw$"; then
    echo "Error: openshell-cluster-nemoclaw container not running"
    echo "Start it first or check if it exists"
    exit 1
fi

# Get the gateway endpoint from the cluster container
GATEWAY_IP=$(docker inspect openshell-cluster-nemoclaw --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
GATEWAY_PORT="30051"
GATEWAY_ENDPOINT="https://${GATEWAY_IP}:${GATEWAY_PORT}"

# Run openshell command connecting to the existing gateway
# We need to share the cluster's network to access the gateway
docker run --rm \
    --name "$CONTAINER_NAME" \
    --network container:openshell-cluster-nemoclaw \
    -e OPENSHELL_GATEWAY_ENDPOINT="${GATEWAY_ENDPOINT}" \
    -e OPENSHELL_NO_VERIFY_TLS=true \
    "$IMAGE_NAME" \
    "$@"
