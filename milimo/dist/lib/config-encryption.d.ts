export interface EncryptedField {
    value: string;
    salt: string;
    iv: string;
    authTag: string;
}
/**
 * Get a machine-specific identifier for key derivation.
 */
export declare function getMachineId(): string;
/**
 * Derive an encryption key from machine ID.
 */
export declare function deriveKey(machineId: string, salt: Buffer): Buffer;
/**
 * Encrypt a sensitive field value.
 */
export declare function encryptValue(plaintext: string): string;
/**
 * Decrypt a sensitive field value.
 */
export declare function decryptValue(encryptedValue: string): string;
/**
 * Check if a value is encrypted.
 */
export declare function isEncrypted(value: string): boolean;
/**
 * Encrypt sensitive fields in a configuration object.
 */
export declare function encryptConfig(config: Record<string, unknown>): Record<string, unknown>;
/**
 * Decrypt sensitive fields in a configuration object.
 */
export declare function decryptConfig(config: Record<string, unknown>): Record<string, unknown>;
//# sourceMappingURL=config-encryption.d.ts.map