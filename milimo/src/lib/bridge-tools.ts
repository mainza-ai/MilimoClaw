// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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

import {
  callPythonBridgeSafe,
  type BridgeResponse,
  type BridgeCommandOptions,
} from "./python-bridge.js";

// ---------------------------------------------------------------------------
// Tool metadata — used for tool discovery by the assistant
// ---------------------------------------------------------------------------

export interface ToolInfo {
  name: string;
  description: string;
  parameters: Record<string, { type: string; description: string; required?: boolean }>;
}

export interface ToolRegistry {
  tools: ToolInfo[];
  total: number;
}

// ---------------------------------------------------------------------------
// Response types for each bridge command
// ---------------------------------------------------------------------------

export interface ClawStatusResult {
  role: string;
  health: Record<string, unknown>;
  tool_count: number;
  last_evolution: string | null;
  pending_messages: Array<{ message_id: string; sender: string; type: string; timestamp: string }>;
  sandbox_exists: boolean;
  sandbox_contents?: string[];
}

export interface SendToClawResult {
  delivered: boolean;
  message_id: string;
  reason: string;
  requires_approval: boolean;
  recipient: string;
  message_type: string;
}

export interface MeshFlowStateResult {
  nodes: Record<
    string,
    { status: string; address: string; last_heartbeat: string | null; pending_messages: number }
  >;
  total_pending: number;
  delivered_this_week: number;
  pending_by_claw: Record<string, number>;
  transport_mode: string;
  last_updated: string;
}

export interface OpsProjectsResult {
  projects: Array<{
    name?: string;
    id: string;
    status: string;
    client_id?: string;
    projects?: Array<{ id: string; status: string; client_id?: string }>;
  }>;
  sandbox_exists: boolean;
}

export interface ContentDraftsResult {
  drafts: Array<{
    id: string;
    status: string;
    platform?: string;
    content_type?: string;
    client_id?: string;
  }>;
  sandbox_exists: boolean;
}

export interface BuildPrsResult {
  prs: Array<{
    number: number;
    title: string;
    author: string;
    createdAt: string;
    updatedAt: string;
    labels: string[];
    url: string;
  }>;
  gh_available: boolean;
}

export interface AnalyticsReportResult {
  report:
    | { filename: string; content: Record<string, unknown> }
    | { filename: string; error: string }
    | null;
  reports_found: Array<{ filename: string; modified: string; size_bytes: number }>;
  reports_dir_exists: boolean;
}

export interface SprintPlanResult {
  status: string;
  plan_path: string;
  sandbox_init?: { created_dirs: string[]; failed: Array<[string, string]> };
}

export interface OpportunityScoringResult {
  status: string;
  request_path: string;
}

export interface WeeklyReportResult {
  generated_at: string;
  week_start: string;
  claws: Record<
    string,
    { role: string; tool_count: number; health: unknown; pending_messages: number }
  >;
  report_path: string;
}

export interface DeadlineCheckResult {
  checked_at: string;
  deadlines: Array<{
    claw: string;
    type: string;
    deadline: string;
    days_remaining: number;
    status: string;
  }>;
  total_deadlines: number;
  overdue_count: number;
}

export interface DependencyAuditResult {
  status: string;
  audit_path: string;
  audits: Array<{
    type: string;
    outdated_count?: number;
    vulnerabilities?: unknown;
    error?: string;
  }>;
  audited_at: string;
}

export interface DiscoverToolsResult {
  claws: Record<
    string,
    {
      tools: Array<{ name: string; version: string }>;
      count: number;
      last_evolution: string | null;
    }
  >;
  total_tools: number;
  discovered_at: string;
}

// ---------------------------------------------------------------------------
// BridgeTools class
// ---------------------------------------------------------------------------

export class BridgeTools {
  private options: BridgeCommandOptions;

  constructor(options: BridgeCommandOptions) {
    this.options = options;
  }

  /**
   * Get detailed status of a specific claw.
   */
  async clawStatus(args: {
    role: string;
    squad_id?: string;
  }): Promise<BridgeResponse<ClawStatusResult>> {
    return callPythonBridgeSafe("claw_status", args, this.options);
  }

  /**
   * Send a typed message from the assistant to a specific claw via the mesh.
   * Use "assistant_query" for read-only questions and "assistant_task" for action requests.
   */
  async sendToClaw(args: {
    role: string;
    type: "assistant_query" | "assistant_task";
    payload: Record<string, unknown>;
    squad_id?: string;
  }): Promise<BridgeResponse<SendToClawResult>> {
    return callPythonBridgeSafe("send_to_claw", args, this.options);
  }

  /**
   * Get live mesh topology, pending message counts, and delivery stats.
   */
  async meshFlowState(args?: { squad?: string }): Promise<BridgeResponse<MeshFlowStateResult>> {
    return callPythonBridgeSafe("mesh_flow_state", args ?? {}, this.options);
  }

  /**
   * List active client projects from the Ops claw sandbox.
   */
  async opsActiveProjects(): Promise<BridgeResponse<OpsProjectsResult>> {
    return callPythonBridgeSafe("ops_active_projects", {}, this.options);
  }

  /**
   * List pending content drafts from the Content claw sandbox.
   */
  async contentPendingDrafts(): Promise<BridgeResponse<ContentDraftsResult>> {
    return callPythonBridgeSafe("content_pending_drafts", {}, this.options);
  }

  /**
   * List open PRs from the Build claw using the gh CLI.
   */
  async buildOpenPrs(): Promise<BridgeResponse<BuildPrsResult>> {
    return callPythonBridgeSafe("build_open_prs", {}, this.options);
  }

  /**
   * Summarize the latest intelligence report from the Analytics claw.
   */
  async analyticsLatestReportSummary(): Promise<BridgeResponse<AnalyticsReportResult>> {
    return callPythonBridgeSafe("analytics_latest_report_summary", {}, this.options);
  }

  /**
   * Trigger sprint plan generation by writing to the Build claw's sprint context.
   */
  async generateSprintPlan(args?: {
    instructions?: string;
    backlog_source?: string;
  }): Promise<BridgeResponse<SprintPlanResult>> {
    return callPythonBridgeSafe("generate_sprint_plan", args ?? {}, this.options);
  }

  /**
   * Trigger opportunity scoring by writing to the Analytics claw's context.
   */
  async runOpportunityScoring(args?: {
    criteria?: string[];
    scope?: string;
  }): Promise<BridgeResponse<OpportunityScoringResult>> {
    return callPythonBridgeSafe("run_opportunity_scoring", args ?? {}, this.options);
  }

  /**
   * Generate a weekly report by aggregating data from all claws.
   */
  async generateWeeklyReport(args?: {
    squad_id?: string;
    week_start?: string;
  }): Promise<BridgeResponse<WeeklyReportResult>> {
    return callPythonBridgeSafe("generate_weekly_report", args ?? {}, this.options);
  }

  /**
   * Check deadlines across all claws.
   */
  async checkAllDeadlines(): Promise<BridgeResponse<DeadlineCheckResult>> {
    return callPythonBridgeSafe("check_all_deadlines", {}, this.options);
  }

  /**
   * Run a dependency audit on the Build claw's repo.
   */
  async runDependencyAudit(): Promise<BridgeResponse<DependencyAuditResult>> {
    return callPythonBridgeSafe("run_dependency_audit", {}, this.options);
  }

  /**
   * Discover what tools each claw currently has deployed.
   */
  async discoverTools(args?: { squad_id?: string }): Promise<BridgeResponse<DiscoverToolsResult>> {
    return callPythonBridgeSafe("discover_tools", args ?? {}, this.options);
  }

  /**
   * Get metadata for all available bridge tools (for assistant discovery).
   */
  getToolRegistry(): ToolRegistry {
    return {
      tools: [
        {
          name: "claw_status",
          description:
            "Get detailed status of a specific claw including health, tools, pending messages, and sandbox state.",
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
          description:
            "Send a typed message from the assistant to a specific claw via the mesh. All messages require operator approval.",
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
          description:
            "Trigger sprint plan generation by writing to the Build claw's sprint context.",
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
          description:
            "Discover what tools each claw currently has deployed, with versions and evolution dates.",
          parameters: {
            squad_id: { type: "string", description: "Squad identifier", required: false },
          },
        },
      ],
      total: 13,
    };
  }
}
