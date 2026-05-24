import type { OpenClawPluginApi, MilimoConfig } from "../index.js";
/**
 * Register Milimo's lifecycle hooks with the OpenClaw plugin API.
 *
 * Hooks:
 * 1. `before_agent_start` — injects <milimo-squad> context block
 * 2. `before_tool_call` — enforces cost guard daily token budget
 *
 * Both hooks are wrapped in try/catch to ensure the plugin still loads
 * even if the OpenClaw host changes the hook contract.
 */
export declare function registerMilimoRuntimeContext(api: OpenClawPluginApi, pluginConfig: MilimoConfig): void;
//# sourceMappingURL=runtime-context.d.ts.map