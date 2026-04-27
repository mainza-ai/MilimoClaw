"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.BridgeTools = void 0;
/**
 * Milimo Claw — Bridge Tool Registry
 *
 * Typed wrapper around the Python bridge CLI that exposes all available
 * commands as discoverable tools for the assistant (Lucy). Each method
 * maps directly to a bridge_cli.py handler.
 *
 * Usage:
 *   const tools = new BridgeTools({ blueprintDir: "/opt/milimo-blueprint" });
 *   const status = await tools.clawStatus({ role: "build" });
 *   const result = await tools.sendToClaw({ role: "ops", type: "assistant_query", payload: { query: "..." } });
 */
const python_bridge_js_1 = require("./python-bridge.js");
// ---------------------------------------------------------------------------
// BridgeTools class
// ---------------------------------------------------------------------------
class BridgeTools {
    options;
    constructor(options) {
        this.options = options;
    }
    /**
     * Get detailed status of a specific claw.
     */
    clawStatus(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("claw_status", args, this.options);
    }
    /**
     * Send a typed message from the assistant to a specific claw via the mesh.
     * Use "assistant_query" for read-only questions and "assistant_task" for action requests.
     */
    sendToClaw(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("send_to_claw", args, this.options);
    }
    /**
     * Get live mesh topology, pending message counts, and delivery stats.
     */
    meshFlowState(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("mesh_flow_state", args ?? {}, this.options);
    }
    /**
     * List active client projects from the Ops claw sandbox.
     */
    opsActiveProjects() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("ops_active_projects", {}, this.options);
    }
    /**
     * List pending content drafts from the Content claw sandbox.
     */
    contentPendingDrafts() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("content_pending_drafts", {}, this.options);
    }
    /**
     * List open PRs from the Build claw using the gh CLI.
     */
    buildOpenPrs() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("build_open_prs", {}, this.options);
    }
    /**
     * Summarize the latest intelligence report from the Analytics claw.
     */
    analyticsLatestReportSummary() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("analytics_latest_report_summary", {}, this.options);
    }
    /**
     * Trigger sprint plan generation by writing to the Build claw's sprint context.
     */
    generateSprintPlan(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("generate_sprint_plan", args ?? {}, this.options);
    }
    /**
     * Trigger opportunity scoring by writing to the Analytics claw's context.
     */
    runOpportunityScoring(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("run_opportunity_scoring", args ?? {}, this.options);
    }
    /**
     * Generate a weekly report by aggregating data from all claws.
     */
    generateWeeklyReport(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("generate_weekly_report", args ?? {}, this.options);
    }
    /**
     * Check deadlines across all claws.
     */
    checkAllDeadlines() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("check_all_deadlines", {}, this.options);
    }
    /**
     * Run a dependency audit on the Build claw's repo.
     */
    runDependencyAudit() {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("run_dependency_audit", {}, this.options);
    }
    /**
     * Discover what tools each claw currently has deployed.
     */
    discoverTools(args) {
        return (0, python_bridge_js_1.callPythonBridgeSafe)("discover_tools", args ?? {}, this.options);
    }
    /**
     * Get metadata for all available bridge tools (for assistant discovery).
     */
    getToolRegistry() {
        return {
            tools: [
                {
                    name: "claw_status",
                    description: "Get detailed status of a specific claw including health, tools, pending messages, and sandbox state.",
                    parameters: {
                        role: {
                            type: "string",
                            description: "Claw role: content, ops, analytics, finance, build, assistant",
                            required: true,
                        },
                        squad_id: { type: "string", description: "Squad identifier", required: false },
                    },
                },
                {
                    name: "send_to_claw",
                    description: "Send a typed message from the assistant to a specific claw via the mesh. All messages require operator approval.",
                    parameters: {
                        role: { type: "string", description: "Target claw role", required: true },
                        type: {
                            type: "string",
                            description: "Message type: assistant_query or assistant_task",
                            required: true,
                        },
                        payload: { type: "object", description: "Message payload", required: true },
                        squad_id: { type: "string", description: "Squad identifier", required: false },
                    },
                },
                {
                    name: "mesh_flow_state",
                    description: "Get live mesh topology, pending message counts, and delivery statistics.",
                    parameters: {
                        squad: { type: "string", description: "Squad identifier", required: false },
                    },
                },
                {
                    name: "ops_active_projects",
                    description: "List active client projects from the Ops claw sandbox.",
                    parameters: {},
                },
                {
                    name: "content_pending_drafts",
                    description: "List pending content drafts from the Content claw sandbox.",
                    parameters: {},
                },
                {
                    name: "build_open_prs",
                    description: "List open PRs from the Build claw using the gh CLI.",
                    parameters: {},
                },
                {
                    name: "analytics_latest_report_summary",
                    description: "Summarize the latest intelligence report from the Analytics claw.",
                    parameters: {},
                },
                {
                    name: "generate_sprint_plan",
                    description: "Trigger sprint plan generation by writing to the Build claw's sprint context.",
                    parameters: {
                        instructions: {
                            type: "string",
                            description: "Instructions for the sprint plan",
                            required: false,
                        },
                        backlog_source: {
                            type: "string",
                            description: "Source for backlog items",
                            required: false,
                        },
                    },
                },
                {
                    name: "run_opportunity_scoring",
                    description: "Trigger opportunity scoring by writing to the Analytics claw's context.",
                    parameters: {
                        criteria: { type: "array", description: "Scoring criteria", required: false },
                        scope: { type: "string", description: "Scope of scoring", required: false },
                    },
                },
                {
                    name: "generate_weekly_report",
                    description: "Generate a weekly report by aggregating data from all claws.",
                    parameters: {
                        squad_id: { type: "string", description: "Squad identifier", required: false },
                        week_start: {
                            type: "string",
                            description: "Week start date (YYYY-MM-DD)",
                            required: false,
                        },
                    },
                },
                {
                    name: "check_all_deadlines",
                    description: "Check deadlines across all claws and report overdue items.",
                    parameters: {},
                },
                {
                    name: "run_dependency_audit",
                    description: "Run a dependency audit on the Build claw's repo (Python and Node.js).",
                    parameters: {},
                },
                {
                    name: "discover_tools",
                    description: "Discover what tools each claw currently has deployed, with versions and evolution dates.",
                    parameters: {
                        squad_id: { type: "string", description: "Squad identifier", required: false },
                    },
                },
            ],
            total: 13,
        };
    }
}
exports.BridgeTools = BridgeTools;
//# sourceMappingURL=bridge-tools.js.map