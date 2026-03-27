export interface WebhookEvent {
    id: string;
    type: string;
    data: {
        object: {
            id: string;
            customer?: string;
            status?: string;
            metadata?: Record<string, string>;
        };
    };
}
export interface SubscriptionChange {
    customerId: string;
    tier: "free" | "pro";
    previousTier: "free" | "pro";
    reason: string;
    timestamp: string;
}
export interface PaymentFailureAlert {
    customerId: string;
    invoiceId: string;
    amount: number;
    currency: string;
    timestamp: string;
}
export interface WebhookHandlerOptions {
    configPath?: string;
    alertDir?: string;
}
export declare class StripeWebhookHandler {
    private configPath;
    private alertDir;
    constructor(options?: WebhookHandlerOptions);
    handleEvent(event: WebhookEvent): SubscriptionChange | PaymentFailureAlert | null;
    private handleSubscriptionCreated;
    private handleSubscriptionDeleted;
    private handlePaymentFailed;
    private getCurrentTier;
    private updateTier;
    private createAlert;
}
export declare function createWebhookHandler(options?: WebhookHandlerOptions): StripeWebhookHandler;
//# sourceMappingURL=webhook-handler.d.ts.map