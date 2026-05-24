import type { PluginLogger } from "../index.js";
/**
 * List available channels via NemoClaw native command.
 */
export declare function cliChannelsList(): void;
/**
 * Add a channel via NemoClaw native command.
 */
export declare function cliChannelsAdd(channelType: string): void;
/**
 * Remove a channel via NemoClaw native command.
 */
export declare function cliChannelsRemove(channelType: string): void;
/**
 * Start channel bridges via NemoClaw native command.
 */
export declare function cliChannelsStart(): void;
/**
 * Stop channel bridges via NemoClaw native command.
 */
export declare function cliChannelsStop(): void;
/**
 * Show Milimo notification status.
 */
export declare function cliChannelsStatus(logger: PluginLogger): void;
/**
 * Send a test notification through active channels.
 */
export declare function cliChannelsTest(logger: PluginLogger): void;
//# sourceMappingURL=channels.d.ts.map