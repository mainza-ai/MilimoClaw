"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.MessageEncryption = void 0;
exports.createTestEncryption = createTestEncryption;
/**
 * Message Encryption
 *
 * AES-256-GCM encryption for inter-claw messages.
 * Key derivation uses PBKDF2 with claw-pair salt.
 */
const node_crypto_1 = require("node:crypto");
const ALGORITHM = "aes-256-gcm";
const KEY_LENGTH = 32;
const IV_LENGTH = 16;
const PBKDF2_ITERATIONS = 100000;
const SALT_SEPARATOR = ":";
class MessageEncryption {
    meshSecret;
    constructor(options) {
        this.meshSecret = options.meshSecret;
    }
    encrypt(plaintext, senderRole, recipientRole) {
        const key = this.deriveKey(senderRole, recipientRole);
        const iv = (0, node_crypto_1.randomBytes)(IV_LENGTH);
        const cipher = (0, node_crypto_1.createCipheriv)(ALGORITHM, key, iv);
        const encrypted = Buffer.concat([cipher.update(plaintext, "utf8"), cipher.final()]);
        const authTag = cipher.getAuthTag();
        return {
            iv: iv.toString("base64"),
            ciphertext: encrypted.toString("base64"),
            authTag: authTag.toString("base64"),
            timestamp: new Date().toISOString(),
        };
    }
    decrypt(encrypted, senderRole, recipientRole) {
        const key = this.deriveKey(senderRole, recipientRole);
        const iv = Buffer.from(encrypted.iv, "base64");
        const ciphertext = Buffer.from(encrypted.ciphertext, "base64");
        const authTag = Buffer.from(encrypted.authTag, "base64");
        const decipher = (0, node_crypto_1.createDecipheriv)(ALGORITHM, key, iv);
        decipher.setAuthTag(authTag);
        const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
        return decrypted.toString("utf8");
    }
    encryptMessage(message, senderRole, recipientRole) {
        const plaintext = JSON.stringify(message);
        const encrypted = this.encrypt(plaintext, senderRole, recipientRole);
        return {
            encrypted: true,
            sender_role: senderRole,
            recipient_role: recipientRole,
            ...encrypted,
        };
    }
    decryptMessage(encryptedMessage) {
        if (!encryptedMessage.encrypted) {
            return encryptedMessage;
        }
        const senderRole = encryptedMessage.sender_role;
        const recipientRole = encryptedMessage.recipient_role;
        const encrypted = {
            iv: encryptedMessage.iv,
            ciphertext: encryptedMessage.ciphertext,
            authTag: encryptedMessage.authTag,
            timestamp: encryptedMessage.timestamp,
        };
        const decrypted = this.decrypt(encrypted, senderRole, recipientRole);
        return JSON.parse(decrypted);
    }
    deriveKey(senderRole, recipientRole) {
        const salt = Buffer.from(`${senderRole}${SALT_SEPARATOR}${recipientRole}`, "utf8");
        const key = (0, node_crypto_1.pbkdf2Sync)(this.meshSecret, salt, PBKDF2_ITERATIONS, KEY_LENGTH, "sha256");
        return key;
    }
    static hashForTesting(data) {
        return (0, node_crypto_1.createHash)("sha256").update(data).digest("hex");
    }
    static generateTestKey() {
        return (0, node_crypto_1.randomBytes)(KEY_LENGTH);
    }
}
exports.MessageEncryption = MessageEncryption;
function createTestEncryption() {
    return new MessageEncryption({
        meshSecret: "test-mesh-secret-for-testing-purposes-only",
    });
}
//# sourceMappingURL=message-encryption.js.map