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
import { type BridgeResponse, type BridgeCommandOptions } from "./python-bridge.js";
export interface ToolInfo {
    name: string;
    description: string;
    parameters: Record<string, {
        type: string;
        description: string;
        required?: boolean;
    }>;
}
export interface ToolRegistry {
    tools: ToolInfo[];
    total: number;
}
export interface ClawStatusResult {
    role: string;
    health: Record<string, unknown>;
    tool_count: number;
    last_evolution: string | null;
    pending_messages: Array<{
        message_id: string;
        sender: string;
        type: string;
        timestamp: string;
    }>;
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
    nodes: Record<string, {
        status: string;
        address: string;
        last_heartbeat: string | null;
        pending_messages: number;
    }>;
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
        projects?: Array<{
            id: string;
            status: string;
            client_id?: string;
        }>;
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
    report: {
        filename: string;
        content: Record<string, unknown>;
    } | {
        filename: string;
        error: string;
    } | null;
    reports_found: Array<{
        filename: string;
        modified: string;
        size_bytes: number;
    }>;
    reports_dir_exists: boolean;
}
export interface SprintPlanResult {
    status: string;
    plan_path: string;
    sandbox_init?: {
        created_dirs: string[];
        failed: Array<[string, string]>;
    };
}
export interface OpportunityScoringResult {
    status: string;
    request_path: string;
}
export interface WeeklyReportResult {
    generated_at: string;
    week_start: string;
    claws: Record<string, {
        role: string;
        tool_count: number;
        health: unknown;
        pending_messages: number;
    }>;
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
    claws: Record<string, {
        tools: Array<{
            name: string;
            version: string;
        }>;
        count: number;
        last_evolution: string | null;
    }>;
    total_tools: number;
    discovered_at: string;
}
export declare class BridgeTools {
    private options;
    constructor(options: BridgeCommandOptions);
    /**
     * Get detailed status of a specific claw.
     */
    clawStatus(args: {
        role: string;
        squad_id?: string;
    }): BridgeResponse<ClawStatusResult>;
    /**
     * Send a typed message from the assistant to a specific claw via the mesh.
     * Use "assistant_query" for read-only questions and "assistant_task" for action requests.
     */
    sendToClaw(args: {
        role: string;
        type: "assistant_query" | "assistant_task";
        payload: Record<string, unknown>;
        squad_id?: string;
    }): BridgeResponse<SendToClawResult>;
    /**
     * Get live mesh topology, pending message counts, and delivery stats.
     */
    meshFlowState(args?: {
        squad?: string;
    }): BridgeResponse<MeshFlowStateResult>;
    /**
     * List active client projects from the Ops claw sandbox.
     */
    opsActiveProjects(): BridgeResponse<OpsProjectsResult>;
    /**
     * List pending content drafts from the Content claw sandbox.
     */
    contentPendingDrafts(): BridgeResponse<ContentDraftsResult>;
    /**
     * List open PRs from the Build claw using the gh CLI.
     */
    buildOpenPrs(): BridgeResponse<BuildPrsResult>;
    /**
     * Summarize the latest intelligence report from the Analytics claw.
     */
    analyticsLatestReportSummary(): BridgeResponse<AnalyticsReportResult>;
    /**
     * Trigger sprint plan generation by writing to the Build claw's sprint context.
     */
    generateSprintPlan(args?: {
        instructions?: string;
        backlog_source?: string;
    }): BridgeResponse<SprintPlanResult>;
    /**
     * Trigger opportunity scoring by writing to the Analytics claw's context.
     */
    runOpportunityScoring(args?: {
        criteria?: string[];
        scope?: string;
    }): BridgeResponse<OpportunityScoringResult>;
    /**
     * Generate a weekly report by aggregating data from all claws.
     */
    generateWeeklyReport(args?: {
        squad_id?: string;
        week_start?: string;
    }): BridgeResponse<WeeklyReportResult>;
    /**
     * Check deadlines across all claws.
     */
    checkAllDeadlines(): BridgeResponse<DeadlineCheckResult>;
    /**
     * Run a dependency audit on the Build claw's repo.
     */
    runDependencyAudit(): BridgeResponse<DependencyAuditResult>;
    /**
     * Discover what tools each claw currently has deployed.
     */
    discoverTools(args?: {
        squad_id?: string;
    }): BridgeResponse<DiscoverToolsResult>;
    /**
     * Get metadata for all available bridge tools (for assistant discovery).
     */
    getToolRegistry(): ToolRegistry;
}
//# sourceMappingURL=bridge-tools.d.ts.map