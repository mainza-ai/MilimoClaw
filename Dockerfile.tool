# Dockerfile for NemoClaw CLI tool
FROM docker:cli as docker-cli

FROM node:22-slim

# Copy modern Docker CLI
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    curl git ca-certificates openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw CLI
RUN npm install -g openclaw@2026.3.11

# Set up workdir
WORKDIR /app

# Copy source code (using .dockerignore to keep it slim)
COPY . .

# Install dependencies and link
RUN npm install --ignore-scripts && npm install -g . --ignore-scripts

# Create a non-root user for the tool (optional, but good practice)
# However, to talk to docker.sock, the user often needs to be in the docker group
# or we run as root inside the container. For simplicity, we'll run as root
# or assume the user will handle permissions.

ENTRYPOINT ["nemoclaw"]
CMD ["--help"]
