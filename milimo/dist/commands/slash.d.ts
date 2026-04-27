/**
 * Handler for the /milimo slash command (chat interface).
 *
 * Supports subcommands:
 * /milimo status - show squad and claw status
 * /milimo role - show current claw role details
 * /milimo finals - show finals mode status
 * /milimo approve <action_id> - approve a pending War Room action
 * /milimo veto <action_id> - block a pending action
 * /milimo health - print one-line health summary per claw
 * /milimo evolution - list last tool built by each claw
 * /milimo - show help
 */
import type { PluginCommandContext, PluginCommandResult, OpenClawPluginApi } from "../index.js";
export declare function handleSlashCommand(ctx: PluginCommandContext, api: OpenClawPluginApi): PluginCommandResult;
//# sourceMappingURL=slash.d.ts.map