// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Message Encryption
 *
 * AES-256-GCM encryption for inter-claw messages.
 * Key derivation uses PBKDF2 with claw-pair salt.
 */

import { createCipheriv, createDecipheriv, createHash, pbkdf2Sync, randomBytes } from "node:crypto";

export interface EncryptedMessage {
    iv: string;
    ciphertext: string;
    authTag: string;
    timestamp: string;
}

export interface MessageEncryptionOptions {
    meshSecret: string;
}

const ALGORITHM = "aes-256-gcm";
const KEY_LENGTH = 32;
const IV_LENGTH = 16;
const AUTH_TAG_LENGTH = 16;
const PBKDF2_ITERATIONS = 100000;
const SALT_SEPARATOR = ":";

export class MessageEncryption {
    private meshSecret: string;

    constructor(options: MessageEncryptionOptions) {
        this.meshSecret = options.meshSecret;
    }

    public encrypt(plaintext: string, senderRole: string, recipientRole: string): EncryptedMessage {
        const key = this.deriveKey(senderRole, recipientRole);
        const iv = randomBytes(IV_LENGTH);

        const cipher = createCipheriv(ALGORITHM, key, iv);
        const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
        const authTag = cipher.getAuthTag();

        return {
            iv: iv.toString("base64"),
            ciphertext: encrypted.toString("base64"),
            authTag: authTag.toString("base64"),
            timestamp: new Date().toISOString(),
        };
    }

    public decrypt(encrypted: EncryptedMessage, senderRole: string, recipientRole: string): string {
        const key = this.deriveKey(senderRole, recipientRole);

        const iv = Buffer.from(encrypted.iv, "base64");
        const ciphertext = Buffer.from(encrypted.ciphertext, "base64");
        const authTag = Buffer.from(encrypted.authTag, "base64");

        const decipher = createDecipheriv(ALGORITHM, key, iv);
        decipher.setAuthTag(authTag);

        const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);

        return decrypted.toString("utf8");
    }

    public encryptMessage(message: Record<string, unknown>, senderRole: string, recipientRole: string): Record<string, unknown> {
        const plaintext = JSON.stringify(message);
        const encrypted = this.encrypt(plaintext, senderRole, recipientRole);

        return {
            encrypted: true,
            sender_role: senderRole,
            recipient_role: recipientRole,
            ...encrypted,
        };
    }

    public decryptMessage(encryptedMessage: Record<string, unknown>): Record<string, unknown> {
        if (!encryptedMessage.encrypted) {
            return encryptedMessage;
        }

        const senderRole = encryptedMessage.sender_role as string;
        const recipientRole = encryptedMessage.recipient_role as string;

        const encrypted: EncryptedMessage = {
            iv: encryptedMessage.iv as string,
            ciphertext: encryptedMessage.ciphertext as string,
            authTag: encryptedMessage.authTag as string,
            timestamp: encryptedMessage.timestamp as string,
        };

        const decrypted = this.decrypt(encrypted, senderRole, recipientRole);
        return JSON.parse(decrypted);
    }

    private deriveKey(senderRole: string, recipientRole: string): Buffer {
        const salt = Buffer.from(`${senderRole}${SALT_SEPARATOR}${recipientRole}`, "utf8");

        const key = pbkdf2Sync(
            this.meshSecret,
            salt,
            PBKDF2_ITERATIONS,
            KEY_LENGTH,
            "sha256",
        );

        return key;
    }

    public static hashForTesting(data: string): string {
        return createHash("sha256").update(data).digest("hex");
    }

    public static generateTestKey(): Buffer {
        return randomBytes(KEY_LENGTH);
    }
}

export function createTestEncryption(): MessageEncryption {
    return new MessageEncryption({
        meshSecret: "test-mesh-secret-for-testing-purposes-only",
    });
}
