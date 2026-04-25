// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for MessageEncryption
 */

import { MessageEncryption, createTestEncryption } from "../mesh/message-encryption";

describe("MessageEncryption", () => {
  const encryption = createTestEncryption();

  describe("encrypt()", () => {
    it("returns base64 encoded values", () => {
      const plaintext = "Hello, World!";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");

      expect(encrypted.iv).toBeDefined();
      expect(encrypted.ciphertext).toBeDefined();
      expect(encrypted.authTag).toBeDefined();
      expect(encrypted.timestamp).toBeDefined();
    });

    it("generates unique IV for each encryption", () => {
      const plaintext = "Same message";
      const encrypted1 = encryption.encrypt(plaintext, "content", "ops");
      const encrypted2 = encryption.encrypt(plaintext, "content", "ops");

      expect(encrypted1.iv).not.toBe(encrypted2.iv);
      expect(encrypted1.ciphertext).not.toBe(encrypted2.ciphertext);
    });

    it("includes timestamp in encrypted message", () => {
      const plaintext = "Test message";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");

      const timestamp = new Date(encrypted.timestamp);
      expect(timestamp.getTime()).toBeLessThanOrEqual(Date.now());
    });
  });

  describe("decrypt()", () => {
    it("recovers original plaintext", () => {
      const plaintext = "Secret message for testing";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");
      const decrypted = encryption.decrypt(encrypted, "content", "ops");

      expect(decrypted).toBe(plaintext);
    });

    it("fails with wrong key derivation", () => {
      const plaintext = "Secret message";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");

      expect(() => {
        encryption.decrypt(encrypted, "ops", "content");
      }).toThrow();
    });

    it("fails with tampered auth tag", () => {
      const plaintext = "Tamper test";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");
      const tamperedAuthTag = Buffer.from(encrypted.authTag, "base64");
      tamperedAuthTag[0] = (tamperedAuthTag[0] ?? 0) ^ 0xff;

      expect(() => {
        encryption.decrypt(
          {
            ...encrypted,
            authTag: tamperedAuthTag.toString("base64"),
          },
          "content",
          "ops",
        );
      }).toThrow();
    });
  });

  describe("encryptMessage()", () => {
    it("encrypts JSON message", () => {
      const message = {
        id: "msg-123",
        type: "deliverable",
        payload: { data: "test" },
      };

      const encrypted = encryption.encryptMessage(message, "content", "ops");

      expect(encrypted.encrypted).toBe(true);
      expect(encrypted.sender_role).toBe("content");
      expect(encrypted.recipient_role).toBe("ops");
      expect(encrypted.iv).toBeDefined();
      expect(encrypted.ciphertext).toBeDefined();
    });
  });

  describe("decryptMessage()", () => {
    it("decrypts and parses JSON message", () => {
      const original = {
        id: "msg-456",
        type: "signal",
        payload: { alert: "test" },
      };

      const encrypted = encryption.encryptMessage(original, "analytics", "ops");
      const decrypted = encryption.decryptMessage(encrypted);

      expect(decrypted.id).toBe("msg-456");
      expect(decrypted.type).toBe("signal");
      expect(decrypted.payload).toEqual({ alert: "test" });
    });

    it("returns original message if not encrypted", () => {
      const plainMessage = {
        id: "plain-msg",
        type: "brief",
      };

      const result = encryption.decryptMessage(plainMessage);

      expect(result).toEqual(plainMessage);
    });
  });

  describe("key derivation", () => {
    it("produces consistent keys for same roles", () => {
      const key1 = (
        encryption as unknown as { deriveKey: (s: string, r: string) => Buffer }
      ).deriveKey("content", "ops");
      const key2 = (
        encryption as unknown as { deriveKey: (s: string, r: string) => Buffer }
      ).deriveKey("content", "ops");

      expect(key1.equals(key2)).toBe(true);
    });

    it("produces different keys for different role pairs", () => {
      const key1 = (
        encryption as unknown as { deriveKey: (s: string, r: string) => Buffer }
      ).deriveKey("content", "ops");
      const key2 = (
        encryption as unknown as { deriveKey: (s: string, r: string) => Buffer }
      ).deriveKey("ops", "content");

      expect(key1.equals(key2)).toBe(false);
    });

    it("produces 32-byte keys", () => {
      const key = (
        encryption as unknown as { deriveKey: (s: string, r: string) => Buffer }
      ).deriveKey("content", "ops");

      expect(key.length).toBe(32);
    });
  });

  describe("cross-role encryption", () => {
    it("encrypts for each role pair", () => {
      const roles = ["content", "ops", "analytics", "finance", "build"];

      for (const sender of roles) {
        for (const recipient of roles) {
          if (sender !== recipient) {
            const plaintext = `Message from ${sender} to ${recipient}`;
            const encrypted = encryption.encrypt(plaintext, sender, recipient);
            const decrypted = encryption.decrypt(encrypted, sender, recipient);

            expect(decrypted).toBe(plaintext);
          }
        }
      }
    });
  });

  describe("authTag verification", () => {
    it("verifies integrity with correct authTag", () => {
      const plaintext = "Integrity test";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");
      const decrypted = encryption.decrypt(encrypted, "content", "ops");

      expect(decrypted).toBe(plaintext);
    });

    it("rejects modified ciphertext", () => {
      const plaintext = "Modification test";
      const encrypted = encryption.encrypt(plaintext, "content", "ops");

      const modifiedCiphertext = Buffer.from(encrypted.ciphertext, "base64");
      modifiedCiphertext[0] = (modifiedCiphertext[0] ?? 0) ^ 0xff;

      expect(() => {
        encryption.decrypt(
          {
            ...encrypted,
            ciphertext: modifiedCiphertext.toString("base64"),
          },
          "content",
          "ops",
        );
      }).toThrow();
    });
  });

  describe("static helpers", () => {
    it("generates consistent hash", () => {
      const hash1 = MessageEncryption.hashForTesting("test data");
      const hash2 = MessageEncryption.hashForTesting("test data");

      expect(hash1).toBe(hash2);
    });

    it("generates different hashes for different data", () => {
      const hash1 = MessageEncryption.hashForTesting("data 1");
      const hash2 = MessageEncryption.hashForTesting("data 2");

      expect(hash1).not.toBe(hash2);
    });

    it("generates 32-byte test keys", () => {
      const key = MessageEncryption.generateTestKey();

      expect(key.length).toBe(32);
    });
  });
});
