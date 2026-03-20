/**
 * `openclaw milimo payment` — Payment and marketplace operations.
 *
 * Subcommands: checkout, status, balance, history, invoice, connect.
 */
import type { PluginLogger, MilimoConfig } from "../index.js";
interface PaymentCheckoutOptions {
    blueprintId: string;
    successUrl?: string;
    cancelUrl?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface PaymentStatusOptions {
    sessionId?: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface PaymentBalanceOptions {
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface PaymentHistoryOptions {
    limit?: number;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface PaymentInvoiceOptions {
    sessionId: string;
    format?: "text" | "json" | "html";
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
interface PaymentConnectOptions {
    displayName: string;
    email: string;
    logger: PluginLogger;
    pluginConfig: MilimoConfig;
}
export declare function cliPaymentCheckout(opts: PaymentCheckoutOptions): Promise<void>;
export declare function cliPaymentStatus(opts: PaymentStatusOptions): Promise<void>;
export declare function cliPaymentBalance(opts: PaymentBalanceOptions): Promise<void>;
export declare function cliPaymentHistory(opts: PaymentHistoryOptions): Promise<void>;
export declare function cliPaymentInvoice(opts: PaymentInvoiceOptions): Promise<void>;
export declare function cliPaymentConnect(opts: PaymentConnectOptions): Promise<void>;
export {};
//# sourceMappingURL=payment.d.ts.map