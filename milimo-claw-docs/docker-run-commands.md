# NemoClaw Docker Setup & Management

This document contains the commands needed to build, run, and manage the `MilimoClaw` persistent Docker container.

## 1. Initial Setup / Rebuilding

If you need to rebuild the image and recreate the container from scratch:

```bash
# Build the Docker image
docker build -t nemoclaw-tool -f Dockerfile.tool .

# Remove any existing container
docker rm -f MilimoClaw

# Create and start the persistent background container
docker run -d --name MilimoClaw \
  --restart always \
  --entrypoint /bin/sh \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ~/.nemoclaw:/root/.nemoclaw \
  nemoclaw-tool -c "tail -f /dev/null"
```

## 2. Management Commands

To run `nemoclaw` commands inside the running container:
```bash
docker exec -it MilimoClaw node /app/bin/nemoclaw.js <command>
```

**Example:**
```bash
docker exec -it MilimoClaw node /app/bin/nemoclaw.js onboard
```

*(Optional)* You can add an alias to your shell profile (`~/.bashrc` or `~/.zshrc`) for convenience:
```bash
alias nemoclaw='docker exec -it MilimoClaw node /app/bin/nemoclaw.js'
```
## 3. Container Lifecycle

If you need to manually start, stop, or restart the background container:

Start container:
```bash
docker start MilimoClaw
```

Stop container:
```bash
docker stop MilimoClaw
```

Restart container:
```bash
docker restart MilimoClaw
```

## 4. Telegram Bridge

To run the Telegram Bridge integration so you can chat with your agent remotely, you need to set the `TELEGRAM_BOT_TOKEN` environment variable and start the auxiliary services. Make sure to also provide `NEMOCLAW_SANDBOX` and `SANDBOX_NAME` if your sandbox isn't named `nemoclaw`.

**Start the Telegram Bridge:**
```bash
docker exec -e TELEGRAM_BOT_TOKEN="<your-bot-token>" -e NEMOCLAW_SANDBOX="milimo" -e SANDBOX_NAME="milimo" MilimoClaw node /app/bin/nemoclaw.js start
```

**Check service status:**
```bash
docker exec -e NEMOCLAW_SANDBOX="milimo" MilimoClaw node /app/bin/nemoclaw.js status
```