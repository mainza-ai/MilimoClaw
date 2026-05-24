import type { PluginLogger } from "../index.js";
import type { DigestBrief } from "../warroom/digest.js";
export type NotificationChannel = "telegram" | "discord" | "slack";
export type AlertLevel = "info" | "warning" | "critical";
export interface ChannelStatus {
    name: NotificationChannel;
    active: boolean;
    lastCheck: string;
}
export interface NotificationConfig {
    /** Channels to send notifications to. Empty = all active channels. */
    channels: NotificationChannel[];
    /** Whether to send digest briefs via channels. */
    digestEnabled: boolean;
    /** Whether to send HOLD alerts via channels. */
    holdAlertsEnabled: boolean;
    /** Whether to send cost guard warnings via channels. */
    costGuardAlertsEnabled: boolean;
    /** Minimum alert level to push. */
    minAlertLevel: AlertLevel;
}
export declare class ChannelNotifier {
    private logger;
    private config;
    private channelCache;
    private cacheExpiry;
    constructor(logger: PluginLogger, config?: Partial<NotificationConfig>);
    /** Get active channels (cached for 5 minutes). */
    getActiveChannels(): ChannelStatus[];
    /** Check if any notification channel is available. */
    hasActiveChannels(): boolean;
    /** Get names of active channels. */
    activeChannelNames(): string[];
    /**
     * Send a digest brief (morning/evening) through active channels.
     */
    sendDigestBrief(brief: DigestBrief): boolean;
    /**
     * Send a HOLD alert when a Finance action requires operator approval.
     */
    sendHoldAlert(holdMessage: {
        message_id: string;
        sender_role: string;
        message_type: string;
        amount?: number;
    }): boolean;
    /**
     * Send a general alert through active channels.
     */
    sendAlert(level: AlertLevel, text: string): boolean;
    /**
     * Send a cost guard warning.
     */
    sendCostGuardWarning(remaining: number, limit: number): boolean;
    /**
     * Get a status summary for display in the War Room TUI.
     */
    getStatusSummary(): string;
    /**
     * Update notification config at runtime.
     */
    updateConfig(updates: Partial<NotificationConfig>): void;
    /**
     * Invalidate the channel cache (e.g. after channel add/remove).
     */
    refreshChannels(): void;
}
/**
 * Load notification config from the Milimo config file.
 */
export declare function loadNotificationConfig(): Partial<NotificationConfig>;
//# sourceMappingURL=channel-notifier.d.ts.map