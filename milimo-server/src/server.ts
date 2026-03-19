// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * War Room Server
 *
 * Fastify server providing REST and WebSocket API for mobile app access.
 */

import Fastify from "fastify";
import cors from "@fastify/cors";
import websocket from "@fastify/websocket";
import jwt from "@fastify/jwt";
import rateLimit from "@fastify/rate-limit";

import { pendingRoutes } from "./routes/pending.js";
import { actionRoutes } from "./routes/actions.js";
import { statusRoutes } from "./routes/status.js";
import { authRoutes } from "./routes/auth.js";

const PORT = parseInt(process.env.PORT || "3000", 10);
const HOST = process.env.HOST || "0.0.0.0";
const JWT_SECRET = process.env.JWT_SECRET || "dev-secret-change-in-production";

const fastify = Fastify({
  logger: {
    level: process.env.LOG_LEVEL || "info",
    transport: {
      target: "pino-pretty",
      options: {
        colorize: true,
      },
    },
  },
  trustProxy: true,
});

// Register plugins
await fastify.register(cors, {
  origin: true,
  credentials: true,
});

await fastify.register(websocket, {
  options: {
    maxPayload: 1048576,
    clientTracking: true,
  },
});

await fastify.register(jwt, {
  secret: JWT_SECRET,
  sign: {
    expiresIn: "1h",
  },
});

await fastify.register(rateLimit, {
  max: 100,
  timeWindow: "1 minute",
  keyGenerator: (request) => {
    return request.ip;
  },
});

// Health check endpoint
fastify.get("/health", async () => {
  return { status: "ok", timestamp: new Date().toISOString() };
});

// Register routes
await fastify.register(authRoutes, { prefix: "/api/v1/auth" });
await fastify.register(pendingRoutes, { prefix: "/api/v1/pending" });
await fastify.register(actionRoutes, { prefix: "/api/v1/pending" });
await fastify.register(statusRoutes, { prefix: "/api/v1/status" });

// WebSocket endpoint for real-time updates
fastify.register(async function (fastify) {
  fastify.get("/ws", { websocket: true }, (connection, request) => {
    fastify.log.info("WebSocket client connected");

    connection.socket.on("message", (message) => {
      try {
        const data = JSON.parse(message.toString());

        if (data.type === "ping") {
          connection.socket.send(
            JSON.stringify({
              type: "pong",
              timestamp: new Date().toISOString(),
            })
          );
        } else if (data.type === "subscribe") {
          fastify.log.info({ channel: data.channel }, "Client subscribed");
          connection.socket.send(
            JSON.stringify({
              type: "subscribed",
              channel: data.channel,
            })
          );
        }
      } catch (error) {
        fastify.log.error({ error }, "WebSocket message parse error");
      }
    });

    connection.socket.on("close", () => {
      fastify.log.info("WebSocket client disconnected");
    });
  });
});

// Authentication middleware for protected routes
fastify.decorate("authenticate", async function (request, reply) {
  try {
    await request.jwtVerify();
  } catch (err) {
    reply.code(401).send({
      error: {
        code: "AUTHENTICATION_FAILED",
        message: "Invalid or expired token",
      },
    });
  }
});

// Start server
const start = async () => {
  try {
    await fastify.listen({ port: PORT, host: HOST });
    fastify.log.info(`War Room Server listening on http://${HOST}:${PORT}`);
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

// Handle shutdown gracefully
process.on("SIGTERM", async () => {
  fastify.log.info("Received SIGTERM, shutting down gracefully");
  await fastify.close();
  process.exit(0);
});

process.on("SIGINT", async () => {
  fastify.log.info("Received SIGINT, shutting down gracefully");
  await fastify.close();
  process.exit(0);
});

export { fastify, start };

// Start if run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  start();
}
