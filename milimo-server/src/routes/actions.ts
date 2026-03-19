// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Action Routes (Approve/Veto)
 */

import { FastifyInstance } from "fastify";
import { v4 as uuidv4 } from "crypto";

interface ApproveRequest {
  Params: { id: string };
  Body: {
    biometric_verified?: boolean;
    notes?: string;
  };
}

interface VetoRequest {
  Params: { id: string };
  Body: {
    reason: string;
    biometric_verified?: boolean;
  };
}

// In-memory store for decisions (replace with actual War Room integration)
const decisions = new Map<string, {
  action_id: string;
  status: "approved" | "vetoed";
  resolved_at: string;
  resolved_by: string;
  notes?: string;
  reason?: string;
}>();

export async function actionRoutes(fastify: FastifyInstance) {
  // Approve action
  fastify.post<ApproveRequest>("/:id/approve", {
    onRequest: [fastify.authenticate],
    config: {
      rateLimit: {
        max: 20,
        timeWindow: "1 minute",
      },
    },
  }, async (request, reply) => {
    const { id } = request.params;
    const { biometric_verified, notes } = request.body;
    const user = request.user as { device_id: string; squad_id: string };

    // Check if action exists
    // In production, check against pendingActions from pending.ts

    // Check if already resolved
    if (decisions.has(id)) {
      return reply.code(409).send({
        error: {
          code: "ACTION_RESOLVED",
          message: "Action has already been approved or vetoed",
          details: decisions.get(id),
        },
      });
    }

    // For high-risk actions, require biometric
    // In production, check action risk_level

    const now = new Date().toISOString();
    const decision = {
      action_id: id,
      status: "approved" as const,
      resolved_at: now,
      resolved_by: user.device_id,
      notes,
    };

    decisions.set(id, decision);

    // In production:
    // 1. Write to War Room inbox
    // 2. Send push notification to other squad members
    // 3. Update audit log

    return {
      success: true,
      action_id: id,
      status: "approved",
      approved_at: now,
    };
  });

  // Veto action
  fastify.post<VetoRequest>("/:id/veto", {
    onRequest: [fastify.authenticate],
    config: {
      rateLimit: {
        max: 20,
        timeWindow: "1 minute",
      },
    },
  }, async (request, reply) => {
    const { id } = request.params;
    const { reason, biometric_verified } = request.body;
    const user = request.user as { device_id: string; squad_id: string };

    if (!reason) {
      return reply.code(400).send({
        error: {
          code: "INVALID_REQUEST",
          message: "reason is required when vetoing an action",
        },
      });
    }

    // Check if already resolved
    if (decisions.has(id)) {
      return reply.code(409).send({
        error: {
          code: "ACTION_RESOLVED",
          message: "Action has already been approved or vetoed",
          details: decisions.get(id),
        },
      });
    }

    const now = new Date().toISOString();
    const decision = {
      action_id: id,
      status: "vetoed" as const,
      resolved_at: now,
      resolved_by: user.device_id,
      reason,
    };

    decisions.set(id, decision);

    // In production:
    // 1. Write to War Room inbox
    // 2. Send push notification to other squad members
    // 3. Update audit log
    // 4. Notify original claw

    return {
      success: true,
      action_id: id,
      status: "vetoed",
      vetoed_at: now,
    };
  });

  // Get decision history
  fastify.get("/:id/decision", {
    onRequest: [fastify.authenticate],
  }, async (request, reply) => {
    const { id } = request.params as { id: string };
    const decision = decisions.get(id);

    if (!decision) {
      return reply.code(404).send({
        error: {
          code: "NOT_FOUND",
          message: "No decision found for this action",
        },
      });
    }

    return decision;
  });
}
