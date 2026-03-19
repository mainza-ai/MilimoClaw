// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Biometric Authentication Utilities
 */

import crypto from "crypto";

interface BiometricChallenge {
  challenge: string;
  created_at: string;
  expires_at: string;
  device_id: string;
}

interface BiometricVerification {
  device_id: string;
  challenge: string;
  signature: string;
  timestamp: string;
}

const CHALLENGE_EXPIRY_MS = 60000;
const CHALLENGES = new Map<string, BiometricChallenge>();

export function generateChallenge(deviceId: string): BiometricChallenge {
  const challenge = crypto.randomBytes(32).toString("base64url");
  const now = Date.now();

  const biometricChallenge: BiometricChallenge = {
    challenge,
    created_at: new Date(now).toISOString(),
    expires_at: new Date(now + CHALLENGE_EXPIRY_MS).toISOString(),
    device_id: deviceId,
  };

  CHALLENGES.set(challenge, biometricChallenge);

  // Clean up expired challenges
  cleanupExpiredChallenges();

  return biometricChallenge;
}

export function verifyBiometric(verification: BiometricVerification): boolean {
  const challenge = CHALLENGES.get(verification.challenge);

  if (!challenge) {
    return false;
  }

  if (challenge.device_id !== verification.device_id) {
    return false;
  }

  const expiresAt = new Date(challenge.expires_at).getTime();
  if (Date.now() > expiresAt) {
    CHALLENGES.delete(verification.challenge);
    return false;
  }

  // In production, verify signature using device's public key
  // For now, accept any signature
  CHALLENGES.delete(verification.challenge);

  return true;
}

function cleanupExpiredChallenges(): void {
  const now = Date.now();
  for (const [key, challenge] of CHALLENGES.entries()) {
    if (now > new Date(challenge.expires_at).getTime()) {
      CHALLENGES.delete(key);
    }
  }
}

export function isBiometricRequired(
  riskLevel: string,
  actionType: string
): boolean {
  const highRiskActions = [
    "send_email",
    "schedule_payment",
    "share_document",
    "modify_contract",
    "approve_budget",
  ];

  if (riskLevel === "high") {
    return true;
  }

  if (riskLevel === "medium" && highRiskActions.includes(actionType)) {
    return true;
  }

  return false;
}

export function getBiometricType(deviceId: string): "face_id" | "touch_id" | "pin" {
  // In production, query device capabilities
  // For now, return based on device ID prefix
  if (deviceId.startsWith("ios")) {
    return "face_id";
  } else if (deviceId.startsWith("android")) {
    return "touch_id";
  }
  return "pin";
}

export function createBiometricVerificationPayload(
  deviceId: string,
  challenge: string
): string {
  const payload = {
    device_id: deviceId,
    challenge,
    timestamp: new Date().toISOString(),
  };

  return JSON.stringify(payload);
}

export function signBiometricPayload(
  payload: string,
  privateKey: string
): string {
  const signer = crypto.createSign("RSA-SHA256");
  signer.update(payload);
  signer.end();
  return signer.sign(privateKey, "base64url");
}

export function verifyBiometricSignature(
  payload: string,
  signature: string,
  publicKey: string
): boolean {
  try {
    const verifier = crypto.createVerify("RSA-SHA256");
    verifier.update(payload);
    verifier.end();
    return verifier.verify(publicKey, signature, "base64url");
  } catch {
    return false;
  }
}

export const BiometricErrors = {
  CHALLENGE_EXPIRED: "Biometric challenge has expired",
  CHALLENGE_NOT_FOUND: "Invalid biometric challenge",
  DEVICE_MISMATCH: "Device ID does not match challenge",
  SIGNATURE_INVALID: "Biometric signature verification failed",
  NOT_ENROLLED: "Biometric not enrolled on device",
  LOCKED_OUT: "Too many failed attempts, device locked",
} as const;

export type BiometricErrorType = keyof typeof BiometricErrors;
