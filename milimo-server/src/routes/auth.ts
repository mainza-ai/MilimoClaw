// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Authentication Routes
 */

import { FastifyInstance } from "fastify";
import { v4 as uuidv4 } from "crypto";

// In-memory refresh token store (replace with Redis/DB in production)
const refreshTokens = new Map<string, { userId: string; expiresAt: number }>();
const REFRESH_TOKEN_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

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
    const userId = `${squad_id}:${device_id}`;

    // Store refresh token for validation
    refreshTokens.set(refreshToken, {
      userId,
      expiresAt: Date.now() + REFRESH_TOKEN_TTL_MS,
    });

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

    // Validate refresh token against store
    const stored = refreshTokens.get(refresh_token);
    if (!stored) {
      return reply.code(401).send({
        error: {
          code: "INVALID_REFRESH_TOKEN",
          message: "Refresh token is invalid or has been revoked",
        },
      });
    }

    // Check expiration
    if (Date.now() > stored.expiresAt) {
      refreshTokens.delete(refresh_token);
      return reply.code(401).send({
        error: {
          code: "EXPIRED_REFRESH_TOKEN",
          message: "Refresh token has expired",
        },
      });
    }

    // Rotate: delete old refresh token, issue new one
    refreshTokens.delete(refresh_token);
    const newRefreshToken = uuidv4();
    refreshTokens.set(newRefreshToken, {
      userId: stored.userId,
      expiresAt: Date.now() + REFRESH_TOKEN_TTL_MS,
    });

    const token = fastify.jwt.sign({
      userId: stored.userId,
      refreshed: true,
      iat: Math.floor(Date.now() / 1000),
    });

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
  }, async (request) => {
    // Invalidate all refresh tokens for this user
    const user = request.user as { userId?: string; squad_id?: string; device_id?: string };
    const userId = user.userId || `${user.squad_id}:${user.device_id}`;
    for (const [token, data] of refreshTokens.entries()) {
      if (data.userId === userId) {
        refreshTokens.delete(token);
      }
    }
    return { success: true };
  });
}
