// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Configuration Encryption
 *
 * Encrypts sensitive configuration fields (meshSecret, API keys, tokens)
 * using Node.js built-in crypto module.
 *
 * Key derivation uses machine-specific identifier:
 * - Linux: /etc/machine-id
 * - macOS: hardware UUID from system_profiler
 *
 * Encrypted fields are prefixed with "enc:v1:" in the config file.
 */

import { createCipheriv, createDecipheriv, createHash, randomBytes, scryptSync } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { platform, hostname } from "node:os";

const ALGORITHM = "aes-256-gcm";
const KEY_LENGTH = 32;
const SALT_LENGTH = 16;
const IV_LENGTH = 16;
const AUTH_TAG_LENGTH = 16;
const ENCRYPTION_PREFIX = "enc:v1:";

export interface EncryptedField {
  value: string;
  salt: string;
  iv: string;
  authTag: string;
}

/**
 * Get a machine-specific identifier for key derivation.
 */
export function getMachineId(): string {
  const currentPlatform = platform();

  if (currentPlatform === "linux") {
    const machineIdPath = "/etc/machine-id";
    if (existsSync(machineIdPath)) {
      return readFileSync(machineIdPath, "utf-8").trim();
    }
    const dbusPath = "/var/lib/dbus/machine-id";
    if (existsSync(dbusPath)) {
      return readFileSync(dbusPath, "utf-8").trim();
    }
  }

  if (currentPlatform === "darwin") {
    const dbusPath = "/var/lib/dbus/machine-id";
    if (existsSync(dbusPath)) {
      return readFileSync(dbusPath, "utf-8").trim();
    }
    try {
      const ioPlatfromBytes = readFileSync(
        "/System/Library/CoreServices/SystemVersion.plist",
        "utf-8",
      );
      const uuidMatch = ioPlatfromBytes.match(/IOPlatformUUID[^<]*<string>([^<]+)<\/string>/);
      if (uuidMatch?.[1]) {
        return uuidMatch[1];
      }
    } catch {
      // fall through
    }
  }

  const fallback = process.env.USER ?? process.env.USERNAME ?? hostname() ?? "default";
  return createHash("sha256").update(`milimo-${hostname()}-${fallback}`).digest("hex");
}

/**
 * Derive an encryption key from machine ID.
 */
export function deriveKey(machineId: string, salt: Buffer): Buffer {
  return scryptSync(machineId, salt, KEY_LENGTH);
}

/**
 * Encrypt a sensitive field value.
 */
export function encryptValue(plaintext: string): string {
  const machineId = getMachineId();
  const salt = randomBytes(SALT_LENGTH);
  const key = deriveKey(machineId, salt);
  const iv = randomBytes(IV_LENGTH);

  const cipher = createCipheriv(ALGORITHM, key, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, "utf-8"), cipher.final()]);
  const authTag = cipher.getAuthTag();

  const combined = Buffer.concat([salt, iv, authTag, encrypted]);
  return ENCRYPTION_PREFIX + combined.toString("base64");
}

/**
 * Decrypt a sensitive field value.
 */
export function decryptValue(encryptedValue: string): string {
  if (!encryptedValue.startsWith(ENCRYPTION_PREFIX)) {
    return encryptedValue;
  }

  const base64Data = encryptedValue.slice(ENCRYPTION_PREFIX.length);
  const data = Buffer.from(base64Data, "base64");

  const salt = data.subarray(0, SALT_LENGTH);
  const iv = data.subarray(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  const authTag = data.subarray(SALT_LENGTH + IV_LENGTH, SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH);
  const encrypted = data.subarray(SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH);

  const machineId = getMachineId();
  const key = deriveKey(machineId, salt);

  const decipher = createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(authTag);

  try {
    const decrypted = Buffer.concat([decipher.update(encrypted), decipher.final()]);
    return decrypted.toString("utf-8");
  } catch {
    throw new Error("Decryption failed: invalid ciphertext or wrong key");
  }
}

/**
 * Check if a value is encrypted.
 */
export function isEncrypted(value: string): boolean {
  return typeof value === "string" && value.startsWith(ENCRYPTION_PREFIX);
}

/**
 * Encrypt sensitive fields in a configuration object.
 */
export function encryptConfig(config: Record<string, unknown>): Record<string, unknown> {
  const sensitiveFields = ["meshSecret", "apiKey", "apiToken", "accessToken", "refreshToken"];

  const encrypted = { ...config };

  for (const field of sensitiveFields) {
    const value = encrypted[field];
    if (typeof value === "string" && value.length > 0 && !isEncrypted(value)) {
      encrypted[field] = encryptValue(value);
    }
  }

  return encrypted;
}

/**
 * Decrypt sensitive fields in a configuration object.
 */
export function decryptConfig(config: Record<string, unknown>): Record<string, unknown> {
  const sensitiveFields = ["meshSecret", "apiKey", "apiToken", "accessToken", "refreshToken"];

  const decrypted = { ...config };

  for (const field of sensitiveFields) {
    const value = decrypted[field];
    if (typeof value === "string" && isEncrypted(value)) {
      try {
        decrypted[field] = decryptValue(value);
      } catch {
        decrypted[field] = "";
      }
    }
  }

  return decrypted;
}
