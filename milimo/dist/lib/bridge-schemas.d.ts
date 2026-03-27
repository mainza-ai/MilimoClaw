/**
 * Bridge Response Schemas
 *
 * Zod schemas for validating responses from bridge_cli.py
 */
import { z } from "zod";
export declare const BridgeResponseSchema: <T extends z.ZodTypeAny>(dataSchema: T) => z.ZodObject<{
    success: z.ZodBoolean;
    data: z.ZodOptional<T>;
    error: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export declare const EvolutionStatusSchema: z.ZodObject<{
    status: z.ZodString;
    last_cycle: z.ZodNullable<z.ZodString>;
    tools_deployed: z.ZodNumber;
    pending_proposals: z.ZodNumber;
}, z.core.$strip>;
export declare const BlueprintInfoSchema: z.ZodObject<{
    version: z.ZodString;
    squad_id: z.ZodString;
    claw_role: z.ZodString;
    tools_count: z.ZodNumber;
    has_attestation: z.ZodBoolean;
}, z.core.$strip>;
export declare const BlueprintListSchema: z.ZodObject<{
    versions: z.ZodArray<z.ZodString>;
    current_version: z.ZodString;
    total_versions: z.ZodNumber;
}, z.core.$strip>;
export declare const BlueprintDiffSchema: z.ZodObject<{
    tools_added: z.ZodArray<z.ZodString>;
    tools_removed: z.ZodArray<z.ZodString>;
    tools_modified: z.ZodArray<z.ZodString>;
    policy_changes: z.ZodRecord<z.ZodString, z.ZodUnknown>;
    config_changes: z.ZodRecord<z.ZodString, z.ZodUnknown>;
}, z.core.$strip>;
export declare const ToolRegistrySchema: z.ZodObject<{
    tools: z.ZodRecord<z.ZodString, z.ZodObject<{
        version: z.ZodOptional<z.ZodString>;
        status: z.ZodOptional<z.ZodString>;
        performance_delta: z.ZodOptional<z.ZodNumber>;
    }, z.core.$strip>>;
    count: z.ZodNumber;
}, z.core.$strip>;
export declare const MarketplaceSearchResultSchema: z.ZodObject<{
    id: z.ZodString;
    name: z.ZodOptional<z.ZodString>;
    author: z.ZodOptional<z.ZodString>;
    price: z.ZodOptional<z.ZodString>;
    verified: z.ZodOptional<z.ZodBoolean>;
    version: z.ZodOptional<z.ZodString>;
    tool_count: z.ZodOptional<z.ZodNumber>;
    fork_count: z.ZodOptional<z.ZodNumber>;
    published_at: z.ZodOptional<z.ZodString>;
    tags: z.ZodOptional<z.ZodArray<z.ZodString>>;
}, z.core.$strip>;
export declare const MarketplaceSearchSchema: z.ZodObject<{
    results: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        name: z.ZodOptional<z.ZodString>;
        author: z.ZodOptional<z.ZodString>;
        price: z.ZodOptional<z.ZodString>;
        verified: z.ZodOptional<z.ZodBoolean>;
        version: z.ZodOptional<z.ZodString>;
        tool_count: z.ZodOptional<z.ZodNumber>;
        fork_count: z.ZodOptional<z.ZodNumber>;
        published_at: z.ZodOptional<z.ZodString>;
        tags: z.ZodOptional<z.ZodArray<z.ZodString>>;
    }, z.core.$strip>>;
    count: z.ZodNumber;
}, z.core.$strip>;
export declare const MarketplaceDownloadSchema: z.ZodObject<{
    success: z.ZodBoolean;
    snapshot: z.ZodOptional<z.ZodRecord<z.ZodString, z.ZodUnknown>>;
    error: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export declare const MarketplacePublishSchema: z.ZodObject<{
    success: z.ZodBoolean;
    blueprint_id: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export declare const MeshFlowStateSchema: z.ZodObject<{
    signals: z.ZodArray<z.ZodObject<{
        signal_type: z.ZodOptional<z.ZodString>;
        source_claw: z.ZodOptional<z.ZodString>;
        destination_claw: z.ZodOptional<z.ZodString>;
        last_transmission: z.ZodOptional<z.ZodString>;
    }, z.core.$strip>>;
    last_transmission: z.ZodNullable<z.ZodString>;
    signal_count_this_week: z.ZodNumber;
}, z.core.$strip>;
export declare const HealthStatusSchema: z.ZodRecord<z.ZodString, z.ZodObject<{
    status: z.ZodOptional<z.ZodString>;
    tools_active: z.ZodOptional<z.ZodNumber>;
    last_cycle: z.ZodOptional<z.ZodString>;
    errors: z.ZodOptional<z.ZodArray<z.ZodString>>;
}, z.core.$strip>>;
export declare const ProvenanceVerifySchema: z.ZodObject<{
    valid: z.ZodBoolean;
    attestation_id: z.ZodOptional<z.ZodString>;
    blueprint_id: z.ZodOptional<z.ZodString>;
    blueprint_version: z.ZodOptional<z.ZodString>;
    author_squad_id: z.ZodOptional<z.ZodString>;
    signature_valid: z.ZodOptional<z.ZodBoolean>;
    content_valid: z.ZodOptional<z.ZodBoolean>;
    timestamp_valid: z.ZodOptional<z.ZodBoolean>;
    errors: z.ZodOptional<z.ZodArray<z.ZodString>>;
    warnings: z.ZodOptional<z.ZodArray<z.ZodString>>;
}, z.core.$strip>;
export declare const ProvenanceKeygenSchema: z.ZodObject<{
    success: z.ZodBoolean;
    key_file: z.ZodOptional<z.ZodString>;
    public_key: z.ZodOptional<z.ZodString>;
    key_id: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export declare const BlueprintRollbackSchema: z.ZodObject<{
    success: z.ZodBoolean;
    version: z.ZodString;
}, z.core.$strip>;
export type EvolutionStatus = z.infer<typeof EvolutionStatusSchema>;
export type BlueprintInfo = z.infer<typeof BlueprintInfoSchema>;
export type BlueprintList = z.infer<typeof BlueprintListSchema>;
export type BlueprintDiff = z.infer<typeof BlueprintDiffSchema>;
export type ToolRegistry = z.infer<typeof ToolRegistrySchema>;
export type MarketplaceSearch = z.infer<typeof MarketplaceSearchSchema>;
export type MarketplaceDownload = z.infer<typeof MarketplaceDownloadSchema>;
export type MarketplacePublish = z.infer<typeof MarketplacePublishSchema>;
export type MeshFlowState = z.infer<typeof MeshFlowStateSchema>;
export type HealthStatus = z.infer<typeof HealthStatusSchema>;
export type ProvenanceVerify = z.infer<typeof ProvenanceVerifySchema>;
export type ProvenanceKeygen = z.infer<typeof ProvenanceKeygenSchema>;
export type BlueprintRollback = z.infer<typeof BlueprintRollbackSchema>;
export declare function validateBridgeResponse<T>(schema: z.ZodSchema<T>, response: unknown): T;
//# sourceMappingURL=bridge-schemas.d.ts.map