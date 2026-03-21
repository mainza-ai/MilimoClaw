export interface EncryptedMessage {
    iv: string;
    ciphertext: string;
    authTag: string;
    timestamp: string;
}
export interface MessageEncryptionOptions {
    meshSecret: string;
}
export declare class MessageEncryption {
    private meshSecret;
    constructor(options: MessageEncryptionOptions);
    encrypt(plaintext: string, senderRole: string, recipientRole: string): EncryptedMessage;
    decrypt(encrypted: EncryptedMessage, senderRole: string, recipientRole: string): string;
    encryptMessage(message: Record<string, unknown>, senderRole: string, recipientRole: string): Record<string, unknown>;
    decryptMessage(encryptedMessage: Record<string, unknown>): Record<string, unknown>;
    private deriveKey;
    static hashForTesting(data: string): string;
    static generateTestKey(): Buffer;
}
export declare function createTestEncryption(): MessageEncryption;
//# sourceMappingURL=message-encryption.d.ts.map