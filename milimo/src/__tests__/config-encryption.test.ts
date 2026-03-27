// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for config encryption
 */

import {
	encryptValue,
	decryptValue,
	isEncrypted,
	encryptConfig,
	decryptConfig,
	getMachineId,
} from "../lib/config-encryption";

describe("Config Encryption", () => {
	describe("getMachineId()", () => {
		it("returns a non-empty string", () => {
			const machineId = getMachineId();
			expect(typeof machineId).toBe("string");
			expect(machineId.length).toBeGreaterThan(0);
		});

		it("returns consistent values across calls", () => {
			const id1 = getMachineId();
			const id2 = getMachineId();
			expect(id1).toBe(id2);
		});
	});

	describe("encryptValue() / decryptValue()", () => {
		it("encrypts a plaintext value", () => {
			const plaintext = "my-secret-value";
			const encrypted = encryptValue(plaintext);

			expect(encrypted).not.toBe(plaintext);
			expect(encrypted.startsWith("enc:v1:")).toBe(true);
		});

		it("decrypts to the original value", () => {
			const plaintext = "my-secret-value";
			const encrypted = encryptValue(plaintext);
			const decrypted = decryptValue(encrypted);

			expect(decrypted).toBe(plaintext);
		});

		it("produces different ciphertext for same plaintext", () => {
			const plaintext = "my-secret-value";
			const encrypted1 = encryptValue(plaintext);
			const encrypted2 = encryptValue(plaintext);

			expect(encrypted1).not.toBe(encrypted2);
		});

		it("handles empty string", () => {
			const plaintext = "";
			const encrypted = encryptValue(plaintext);
			const decrypted = decryptValue(encrypted);

			expect(decrypted).toBe(plaintext);
		});

		it("handles special characters", () => {
			const plaintext = "secret-with-特殊字符-🔐-and\"quotes\"and'apostrophes'";
			const encrypted = encryptValue(plaintext);
			const decrypted = decryptValue(encrypted);

			expect(decrypted).toBe(plaintext);
		});

		it("handles long values", () => {
			const plaintext = "a".repeat(10000);
			const encrypted = encryptValue(plaintext);
			const decrypted = decryptValue(encrypted);

			expect(decrypted).toBe(plaintext);
		});
	});

	describe("isEncrypted()", () => {
		it("returns true for encrypted values", () => {
			const encrypted = encryptValue("secret");
			expect(isEncrypted(encrypted)).toBe(true);
		});

		it("returns false for plaintext values", () => {
			expect(isEncrypted("plaintext")).toBe(false);
			expect(isEncrypted("")).toBe(false);
			expect(isEncrypted("enc:")).toBe(false);
		});
	});

	describe("encryptConfig()", () => {
		it("encrypts sensitive fields", () => {
			const config = {
				squadName: "test-squad",
				meshSecret: "my-mesh-secret",
				apiKey: "my-api-key",
				normalField: "normal-value",
			};

			const encrypted = encryptConfig(config);

			expect(encrypted.squadName).toBe("test-squad");
			expect(encrypted.normalField).toBe("normal-value");
			expect(isEncrypted(encrypted.meshSecret as string)).toBe(true);
			expect(isEncrypted(encrypted.apiKey as string)).toBe(true);
		});

		it("does not re-encrypt already encrypted fields", () => {
			const config = {
				meshSecret: encryptValue("already-encrypted"),
			};

			const encrypted = encryptConfig(config);

			expect(encrypted.meshSecret).toBe(config.meshSecret);
		});

		it("skips empty sensitive fields", () => {
			const config = {
				meshSecret: "",
				apiKey: null,
			};

			const encrypted = encryptConfig(config);

			expect(encrypted.meshSecret).toBe("");
			expect(encrypted.apiKey).toBeNull();
		});
	});

	describe("decryptConfig()", () => {
		it("decrypts encrypted fields", () => {
			const originalSecret = "my-mesh-secret";
			const config = {
				squadName: "test-squad",
				meshSecret: encryptValue(originalSecret),
				normalField: "normal-value",
			};

			const decrypted = decryptConfig(config);

			expect(decrypted.squadName).toBe("test-squad");
			expect(decrypted.normalField).toBe("normal-value");
			expect(decrypted.meshSecret).toBe(originalSecret);
		});

		it("leaves plaintext fields unchanged", () => {
			const config = {
				meshSecret: "plaintext-secret",
			};

			const decrypted = decryptConfig(config);

			expect(decrypted.meshSecret).toBe("plaintext-secret");
		});
	});

	describe("round trip", () => {
		it("encrypt and decrypt preserves all data", () => {
			const original = {
				meshSecret: "secret1",
				apiKey: "key2",
				apiToken: "token3",
				accessToken: "access4",
				refreshToken: "refresh5",
				normalField: "normal",
				number: 123,
				boolean: true,
			};

			const encrypted = encryptConfig(original);
			const decrypted = decryptConfig(encrypted);

			expect(decrypted.meshSecret).toBe(original.meshSecret);
			expect(decrypted.apiKey).toBe(original.apiKey);
			expect(decrypted.apiToken).toBe(original.apiToken);
			expect(decrypted.accessToken).toBe(original.accessToken);
			expect(decrypted.refreshToken).toBe(original.refreshToken);
			expect(decrypted.normalField).toBe(original.normalField);
			expect(decrypted.number).toBe(original.number);
			expect(decrypted.boolean).toBe(original.boolean);
		});
	});

	describe("backwards compatibility", () => {
		it("handles plaintext config fields transparently", () => {
			const config = {
				meshSecret: "plaintext-secret",
			};

			const decrypted = decryptConfig(config);

			expect(decrypted.meshSecret).toBe("plaintext-secret");
		});

		it("handles mixed encrypted and plaintext fields", () => {
			const config = {
				meshSecret: encryptValue("encrypted-secret"),
				apiKey: "plaintext-key",
			};

			const decrypted = decryptConfig(config);

			expect(decrypted.meshSecret).toBe("encrypted-secret");
			expect(decrypted.apiKey).toBe("plaintext-key");
		});
	});
});
