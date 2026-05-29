#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# scripts/pull_claw_files.sh - Pull files created by claws inside the sandbox container to the host Mac.

# Find the running claws container with the prefix openshell-my-assistant
CONTAINER_NAME=$(docker ps --filter "name=openshell-my-assistant" --format "{{.Names}}" | head -n 1)

if [ -z "$CONTAINER_NAME" ]; then
  echo "Error: No running container with prefix 'openshell-my-assistant' found."
  echo "Please start the claw services first using: npm run dev or scripts/milimo-start.sh"
  exit 1
fi

ROLE=$1
HOST_DEST="./claws_data"

if [ -z "$ROLE" ]; then
  echo "No specific claw role provided. Pulling files for all claws..."
  mkdir -p "$HOST_DEST"

  for r in content ops analytics finance build assistant; do
    echo " -> Extracting files from $r claw..."
    mkdir -p "$HOST_DEST/$r"
    # Pull standard claw workspace files, silencing standard errors for empty paths
    docker cp "$CONTAINER_NAME:/sandbox/.openclaw/milimo/claws/$r/." "$HOST_DEST/$r/" 2>/dev/null
  done
  echo "Success! All claw files have been synchronized successfully to: $HOST_DEST/"
else
  # Canonicalize role parameter
  ROLE_LOWER=$(echo "$ROLE" | tr '[:upper:]' '[:lower:]' | sed 's/-claw//g')

  # Validate role
  case "$ROLE_LOWER" in
    content | ops | analytics | finance | build | assistant)
      echo " -> Extracting files from $ROLE_LOWER claw..."
      mkdir -p "$HOST_DEST/$ROLE_LOWER"
      docker cp "$CONTAINER_NAME:/sandbox/.openclaw/milimo/claws/$ROLE_LOWER/." "$HOST_DEST/$ROLE_LOWER/" 2>/dev/null
      echo "Success! $ROLE_LOWER claw files synchronized to: $HOST_DEST/$ROLE_LOWER/"
      ;;
    *)
      echo "Error: Invalid claw role. Supported roles: content, ops, analytics, finance, build, assistant"
      exit 1
      ;;
  esac
fi
