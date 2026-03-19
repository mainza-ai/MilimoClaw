// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * JWT Utilities for Mobile Authentication
 */

import crypto from "crypto";

interface JwtPayload {
  squad_id: string;
  device_id: string;
  biometric_verified: boolean;
  iat: number;
  exp?: number;
}

interface TokenOptions {
  expiresIn?: string;
  issuer?: string;
  audience?: string;
}

const ALGORITHM = "HS256";
const TOKEN_EXPIRY = "1h";
const REFRESH_TOKEN_EXPIRY = "7d";

function base64UrlEncode(data: string): string {
  return Buffer.from(data)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

function base64UrlDecode(str: string): string {
  str = str.replace(/-/g, "+").replace(/_/g, "/");
  while (str.length % 4) {
    str += "=";
  }
  return Buffer.from(str, "base64").toString();
}

function createSignature(header: string, payload: string, secret: string): string {
  const data = `${header}.${payload}`;
  return crypto.createHmac("sha256", secret).update(data).digest("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

export function generateToken(
  payload: Omit<JwtPayload, "iat" | "exp">,
  secret: string,
  options: TokenOptions = {}
): string {
  const header = base64UrlEncode(JSON.stringify({ alg: ALGORITHM, typ: "JWT" }));

  const now = Math.floor(Date.now() / 1000);
  const expiresIn = parseExpiry(options.expiresIn || TOKEN_EXPIRY);

  const fullPayload: JwtPayload = {
    ...payload,
    iat: now,
    exp: now + expiresIn,
  };

  const payloadEncoded = base64UrlEncode(JSON.stringify(fullPayload));
  const signature = createSignature(header, payloadEncoded, secret);

  return `${header}.${payloadEncoded}.${signature}`;
}

export function verifyToken(token: string, secret: string): JwtPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  const [header, payload, signature] = parts;
  const expectedSignature = createSignature(header, payload, secret);

  if (signature !== expectedSignature) {
    return null;
  }

  try {
    const decoded = JSON.parse(base64UrlDecode(payload)) as JwtPayload;

    if (decoded.exp && decoded.exp < Math.floor(Date.now() / 1000)) {
      return null;
    }

    return decoded;
  } catch {
    return null;
  }
}

export function generateRefreshToken(): string {
  return crypto.randomBytes(32).toString("base64url");
}

export function hashRefreshToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

export function parseExpiry(expiry: string): number {
  const match = expiry.match(/^(\d+)([smhd])$/);
  if (!match) {
    return 3600;
  }

  const value = parseInt(match[1], 10);
  const unit = match[2];

  switch (unit) {
    case "s":
      return value;
    case "m":
      return value * 60;
    case "h":
      return value * 3600;
    case "d":
      return value * 86400;
    default:
      return 3600;
  }
}

export function decodeToken(token: string): JwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }

    return JSON.parse(base64UrlDecode(parts[1])) as JwtPayload;
  } catch {
    return null;
  }
}

export function getTokenRemainingTime(token: string): number {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    return 0;
  }

  const remaining = decoded.exp - Math.floor(Date.now() / 1000);
  return Math.max(0, remaining);
}

export function isTokenExpired(token: string): boolean {
  return getTokenRemainingTime(token) === 0;
}
