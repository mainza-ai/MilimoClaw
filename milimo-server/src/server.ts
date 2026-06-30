// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * War Room Server
 *
 * Fastify server providing REST and WebSocket API for mobile app access.
 */

import Fastify, { FastifyRequest, FastifyReply } from "fastify";
import cors from "@fastify/cors";
import websocket from "@fastify/websocket";
import jwt from "@fastify/jwt";
import rateLimit from "@fastify/rate-limit";

// Augment FastifyInstance with runtime authenticate decorator
declare module "fastify" {
  interface FastifyInstance {
    authenticate: (request: FastifyRequest, reply: FastifyReply) => Promise<void>;
  }
}

import { pendingRoutes } from "./routes/pending.js";
import { actionRoutes } from "./routes/actions.js";
import { statusRoutes } from "./routes/status.js";
import { authRoutes } from "./routes/auth.js";
import { createWebhookRoute } from "./payments/webhooks.js";
import { TenantManager } from "./tenants/manager.js";
import { TenantLimitsEnforcer } from "./tenants/limits.js";

const PORT = parseInt(process.env.PORT || "3000", 10);
const HOST = process.env.HOST || "0.0.0.0";
const JWT_SECRET = process.env.JWT_SECRET;

if (!JWT_SECRET) {
  throw new Error(
    "JWT_SECRET environment variable is required. Generate one with: openssl rand -hex 32"
  );
}

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
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS?.split(",") || [];

await fastify.register(cors, {
  origin: ALLOWED_ORIGINS.length > 0 ? ALLOWED_ORIGINS : false,
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

// Register Stripe webhook routes (must be before authenticate decorator)
createWebhookRoute(fastify);

// Shared instances for cross-module use
const tenantManager = new TenantManager();
const tenantLimitsEnforcer = new TenantLimitsEnforcer();

// Tenant resolution middleware — scopes requests to tenants
fastify.addHook("onRequest", async (request, reply) => {
  // Skip middleware for public endpoints
  const publicPaths = ["/health", "/webhooks/stripe", "/webhooks/stripe/v2", "/api/v1/auth/token"];
  if (publicPaths.some((p) => request.url.startsWith(p))) {
    return;
  }

  // Extract tenant from JWT or header
  const user = request.user as { tenant_id?: string } | undefined;
  if (user?.tenant_id) {
    const tenant = await tenantManager.getTenant(user.tenant_id);
    if (!tenant) {
      return reply.code(403).send({
        error: { code: "TENANT_NOT_FOUND", message: "Tenant not found" },
      });
    }
    // Check limits
    const alerts = tenantLimitsEnforcer.checkAlerts(tenant);
    if (alerts.some((a) => a.severity === "critical")) {
      return reply.code(429).send({
        error: { code: "TENANT_LIMIT_EXCEEDED", message: "Tenant resource limits exceeded", alerts },
      });
    }
    (request as any).tenant = tenant;
  }
});

// WebSocket endpoint for real-time updates (requires JWT authentication)
fastify.register(async function (fastify) {
  fastify.get("/ws", { websocket: true }, (socket, request) => {
    // Authenticate WebSocket connection via query parameter
    const query = request.query as { token?: string };
    const token = query.token;
    if (!token) {
      fastify.log.warn("WebSocket connection rejected: no token provided");
      socket.close(4001, "Authentication required");
      return;
    }

    try {
      const decoded = fastify.jwt.verify(token);
      fastify.log.info({ user: decoded }, "WebSocket client authenticated");
    } catch (err) {
      fastify.log.warn("WebSocket connection rejected: invalid token");
      socket.close(4001, "Invalid token");
      return;
    }

    fastify.log.info("WebSocket client connected");

    socket.on("message", (message: Buffer) => {
      try {
        const data = JSON.parse(message.toString());

        if (data.type === "ping") {
          socket.send(
            JSON.stringify({
              type: "pong",
              timestamp: new Date().toISOString(),
            })
          );
        } else if (data.type === "subscribe") {
          fastify.log.info({ channel: data.channel }, "Client subscribed");
          socket.send(
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

    socket.on("close", () => {
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
