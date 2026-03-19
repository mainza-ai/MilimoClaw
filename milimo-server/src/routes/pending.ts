// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Pending Actions Routes
 */

import { FastifyInstance } from "fastify";
import { v4 as uuidv4 } from "crypto";

interface PendingAction {
  id: string;
  type: string;
  claw_role: string;
  action_type: string;
  description: string;
  payload: Record<string, unknown>;
  confidence: number;
  risk_level: string;
  created_at: string;
  expires_at: string;
}

// Mock data store (replace with actual War Room integration)
const pendingActions: Map<string, PendingAction> = new Map();

export async function pendingRoutes(fastify: FastifyInstance) {
  // List pending actions
  fastify.get("/", {
    onRequest: [fastify.authenticate],
    config: {
      rateLimit: {
        max: 100,
        timeWindow: "1 minute",
      },
    },
  }, async (request, reply) => {
    const user = request.user as { squad_id: string };
    const { limit = "20", offset = "0" } = request.query as { limit?: string; offset?: string };

    const limitNum = parseInt(limit, 10);
    const offsetNum = parseInt(offset, 10);

    const items = Array.from(pendingActions.values())
      .filter((action) => true) // Filter by squad_id in production
      .slice(offsetNum, offsetNum + limitNum);

    return {
      items,
      total: pendingActions.size,
      has_more: offsetNum + limitNum < pendingActions.size,
    };
  });

  // Get action details
  fastify.get<{ Params: { id: string } }>("/:id", {
    onRequest: [fastify.authenticate],
  }, async (request, reply) => {
    const { id } = request.params;
    const action = pendingActions.get(id);

    if (!action) {
      return reply.code(404).send({
        error: {
          code: "ACTION_NOT_FOUND",
          message: `Action ${id} not found`,
        },
      });
    }

    return action;
  });

  // Create pending action (internal use)
  fastify.post("/", async (request, reply) => {
    const body = request.body as Partial<PendingAction>;

    const id = uuidv4();
    const now = new Date();
    const expiresAt = new Date(now.getTime() + 60 * 60 * 1000); // 1 hour

    const action: PendingAction = {
      id,
      type: body.type || "auto_approval",
      claw_role: body.claw_role || "content",
      action_type: body.action_type || "unknown",
      description: body.description || "",
      payload: body.payload || {},
      confidence: body.confidence || 0.5,
      risk_level: body.risk_level || "medium",
      created_at: now.toISOString(),
      expires_at: expiresAt.toISOString(),
    };

    pendingActions.set(id, action);

    return reply.code(201).send(action);
  });
}
