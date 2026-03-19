// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Status Routes
 */

import { FastifyInstance } from "fastify";

interface ClawStatus {
  role: string;
  status: string;
  region: string;
  last_heartbeat: string;
  actions_today: number;
}

export async function statusRoutes(fastify: FastifyInstance) {
  // Get War Room status
  fastify.get("/", {
    onRequest: [fastify.authenticate],
  }, async (request) => {
    const user = request.user as { squad_id: string };

    // In production, read from actual mesh coordinator state
    return {
      squad_id: user.squad_id,
      mesh_status: "healthy",
      claws_online: 5,
      pending_count: 3,
      approved_today: 12,
      vetoed_today: 2,
      rate_limit: {
        used: 5,
        limit: 10,
        resets_at: new Date(Date.now() + 86400000).toISOString(),
      },
      last_activity: new Date().toISOString(),
    };
  });

  // Get claw health
  fastify.get("/claws", {
    onRequest: [fastify.authenticate],
  }, async (request) => {
    const user = request.user as { squad_id: string };

    // In production, read from mesh coordinator topology
    const claws: ClawStatus[] = [
      {
        role: "content",
        status: "online",
        region: "us-east-1",
        last_heartbeat: new Date().toISOString(),
        actions_today: 8,
      },
      {
        role: "ops",
        status: "online",
        region: "eu-west-1",
        last_heartbeat: new Date(Date.now() - 60000).toISOString(),
        actions_today: 5,
      },
      {
        role: "finance",
        status: "online",
        region: "us-east-1",
        last_heartbeat: new Date(Date.now() - 30000).toISOString(),
        actions_today: 3,
      },
      {
        role: "build",
        status: "online",
        region: "ap-southeast-1",
        last_heartbeat: new Date(Date.now() - 45000).toISOString(),
        actions_today: 7,
      },
      {
        role: "ops_admin",
        status: "offline",
        region: "us-west-2",
        last_heartbeat: new Date(Date.now() - 3600000).toISOString(),
        actions_today: 0,
      },
    ];

    return { claws };
  });

  // Get mesh health
  fastify.get("/mesh", {
    onRequest: [fastify.authenticate],
  }, async () => {
    return {
      status: "healthy",
      regions: {
        "us-east-1": {
          status: "healthy",
          latency_ms: 0,
          claws_online: 2,
        },
        "eu-west-1": {
          status: "healthy",
          latency_ms: 85,
          claws_online: 1,
        },
        "ap-southeast-1": {
          status: "healthy",
          latency_ms: 180,
          claws_online: 1,
        },
        "us-west-2": {
          status: "isolated",
          latency_ms: null,
          claws_online: 0,
        },
      },
      latency_matrix: {
        "us-east-1": {
          "eu-west-1": 85,
          "ap-southeast-1": 180,
          "us-west-2": 65,
        },
        "eu-west-1": {
          "us-east-1": 85,
          "ap-southeast-1": 165,
          "us-west-2": 140,
        },
      },
    };
  });

  // Get rate limit status
  fastify.get("/rate-limit", {
    onRequest: [fastify.authenticate],
  }, async () => {
    return {
      tier: "free",
      daily_limit: 10,
      used_today: 5,
      remaining: 5,
      resets_at: new Date(Date.now() + 86400000).toISOString(),
      burst_limit: 3,
      burst_used: 1,
      burst_resets_at: new Date(Date.now() + 3600000).toISOString(),
    };
  });

  // Get activity log
  fastify.get("/activity", {
    onRequest: [fastify.authenticate],
  }, async (request) => {
    const { limit = "50" } = request.query as { limit?: string };
    const limitNum = parseInt(limit, 10);

    // In production, read from audit log
    return {
      activities: [
        {
          id: "activity-1",
          type: "approved",
          action_id: "action-123",
          claw_role: "content",
          resolved_by: "mobile:device-abc",
          timestamp: new Date().toISOString(),
        },
        {
          id: "activity-2",
          type: "vetoed",
          action_id: "action-124",
          claw_role: "ops",
          resolved_by: "mobile:device-xyz",
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          reason: "Client requested pause",
        },
      ],
      total: 2,
    };
  });
}
