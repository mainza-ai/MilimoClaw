// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Authentication Routes
 */

import { FastifyInstance } from "fastify";
import { v4 as uuidv4 } from "crypto";

interface AuthTokenRequest {
  Body: {
    squad_id: string;
    device_id: string;
    biometric_verified?: boolean;
  };
}

interface RefreshTokenRequest {
  Body: {
    refresh_token: string;
  };
}

export async function authRoutes(fastify: FastifyInstance) {
  // Generate authentication token
  fastify.post<AuthTokenRequest>("/token", async (request, reply) => {
    const { squad_id, device_id, biometric_verified } = request.body;

    if (!squad_id || !device_id) {
      return reply.code(400).send({
        error: {
          code: "INVALID_REQUEST",
          message: "squad_id and device_id are required",
        },
      });
    }

    // Generate tokens
    const token = fastify.jwt.sign({
      squad_id,
      device_id,
      biometric_verified: biometric_verified || false,
      iat: Math.floor(Date.now() / 1000),
    });

    const refreshToken = uuidv4();

    return {
      token,
      refresh_token: refreshToken,
      expires_in: 3600,
    };
  });

  // Refresh authentication token
  fastify.post<RefreshTokenRequest>("/refresh", async (request, reply) => {
    const { refresh_token } = request.body;

    if (!refresh_token) {
      return reply.code(400).send({
        error: {
          code: "INVALID_REQUEST",
          message: "refresh_token is required",
        },
      });
    }

    // In production, verify refresh token from database
    // For now, generate a new token

    const token = fastify.jwt.sign({
      refreshed: true,
      iat: Math.floor(Date.now() / 1000),
    });

    const newRefreshToken = uuidv4();

    return {
      token,
      refresh_token: newRefreshToken,
      expires_in: 3600,
    };
  });

  // Verify token
  fastify.get("/verify", {
    onRequest: [fastify.authenticate],
  }, async (request) => {
    return {
      valid: true,
      payload: request.user,
    };
  });

  // Logout
  fastify.post("/logout", {
    onRequest: [fastify.authenticate],
  }, async () => {
    // In production, invalidate refresh token in database
    return { success: true };
  });
}
