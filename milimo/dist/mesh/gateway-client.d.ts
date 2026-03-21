export declare class GatewayDeliveryError extends Error {
    constructor(message: string);
}
export interface GatewayMessage {
    id: string;
    sender_role: string;
    recipient_role: string;
    message_type: string;
    payload: Record<string, unknown>;
    timestamp: string;
    encrypted?: boolean;
}
export interface GatewayClientOptions {
    squadId: string;
    meshSecret: string;
    onMessage?: (message: GatewayMessage) => void;
}
export declare class GatewayClient {
    private squadId;
    private meshSecret;
    private socketPath;
    private socket;
    private connected;
    private fallbackMode;
    private messageHandlers;
    private pendingAcks;
    private retryCount;
    constructor(options: GatewayClientOptions);
    connect(): Promise<void>;
    private setupSocketHandlers;
    private handleIncomingMessage;
    send(message: GatewayMessage): Promise<void>;
    onMessage(handler: (message: GatewayMessage) => void): void;
    disconnect(): void;
    isConnected(): boolean;
    getFallbackMode(): boolean;
    private encryptMessage;
    private decryptMessage;
    private deriveKey;
    private sendFileMessage;
}
export declare function getGatewaySocketPath(): string;
export declare function checkGatewayAvailable(): boolean;
//# sourceMappingURL=gateway-client.d.ts.map