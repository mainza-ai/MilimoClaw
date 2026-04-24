/**
 * Milimo Claw — Multi-Agent Autonomous Hustle Platform
 *
 * OpenClaw plugin that extends NemoClaw with squad mesh coordination,
 * role-specific claw blueprints, privacy routing, and the War Room TUI.
 *
 * Uses the real OpenClaw plugin API. Types are imported from the NemoClaw
 * plugin's type definitions since they mirror the OpenClaw SDK interfaces.
 */
import type { Command } from "commander";
/** Subset of OpenClawConfig that we actually read. */
export interface OpenClawConfig {
    [key: string]: unknown;
}
/** Logger provided by the plugin host. */
export interface PluginLogger {
    info(message: string): void;
    warn(message: string): void;
    error(message: string): void;
    debug(message: string): void;
}
/** Context passed to slash-command handlers. */
export interface PluginCommandContext {
    senderId?: string;
    channel: string;
    isAuthorizedSender: boolean;
    args?: string;
    commandBody: string;
    config: OpenClawConfig;
    from?: string;
    to?: string;
    accountId?: string;
}
/** Return value from a slash-command handler. */
export interface PluginCommandResult {
    text?: string;
    mediaUrl?: string;
    mediaUrls?: string[];
}
/** Registration shape for a slash command. */
export interface PluginCommandDefinition {
    name: string;
    description: string;
    acceptsArgs?: boolean;
    requireAuth?: boolean;
    handler: (ctx: PluginCommandContext) => PluginCommandResult | Promise<PluginCommandResult>;
}
/** Context passed to the CLI registrar callback. */
export interface PluginCliContext {
    program: Command;
    config: OpenClawConfig;
    workspaceDir?: string;
    logger: PluginLogger;
}
/** CLI registrar callback type. */
export type PluginCliRegistrar = (ctx: PluginCliContext) => void | Promise<void>;
/**
 * The API object injected into the plugin's register function by the OpenClaw
 * host. Only the methods we actually call are listed here.
 */
export interface OpenClawPluginApi {
    id: string;
    name: string;
    version?: string;
    config: OpenClawConfig;
    pluginConfig?: Record<string, unknown>;
    logger: PluginLogger;
    registerCommand: (command: PluginCommandDefinition) => void;
    registerCli: (registrar: PluginCliRegistrar, opts?: {
        commands?: string[];
    }) => void;
    resolvePath: (input: string) => string;
    on: (hookName: string, handler: (...args: unknown[]) => void) => void;
}
/** Valid claw role identifiers. "solo" indicates all claws run on one machine. */
export type ClawRole = "content" | "ops" | "analytics" | "finance" | "build" | "assistant" | "solo";
/** All valid claw roles (excluding "solo" which is a mode indicator). */
export declare const CLAW_ROLES: ClawRole[];
/** Milimo plugin configuration. */
export interface MilimoConfig {
    squadName: string;
    clawRole: ClawRole | "";
    meshSecret: string;
    blueprintDir: string;
    serverUrl?: string;
}
export declare function getPluginConfig(api: OpenClawPluginApi): MilimoConfig;
export default function register(api: OpenClawPluginApi): void;
//# sourceMappingURL=index.d.ts.map
