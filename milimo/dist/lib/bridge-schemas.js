"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.BlueprintRollbackSchema = exports.ProvenanceKeygenSchema = exports.ProvenanceVerifySchema = exports.HealthStatusSchema = exports.MeshFlowStateSchema = exports.MarketplacePublishSchema = exports.MarketplaceDownloadSchema = exports.MarketplaceSearchSchema = exports.MarketplaceSearchResultSchema = exports.ToolRegistrySchema = exports.BlueprintDiffSchema = exports.BlueprintListSchema = exports.BlueprintInfoSchema = exports.EvolutionStatusSchema = exports.BridgeResponseSchema = void 0;
exports.validateBridgeResponse = validateBridgeResponse;
/**
 * Bridge Response Schemas
 *
 * Zod schemas for validating responses from bridge_cli.py
 */
const zod_1 = require("zod");
const BridgeResponseSchema = (dataSchema) => zod_1.z.object({
    success: zod_1.z.boolean(),
    data: dataSchema.optional(),
    error: zod_1.z.string().optional(),
});
exports.BridgeResponseSchema = BridgeResponseSchema;
exports.EvolutionStatusSchema = zod_1.z.object({
    status: zod_1.z.string(),
    last_cycle: zod_1.z.string().nullable(),
    tools_deployed: zod_1.z.number(),
    pending_proposals: zod_1.z.number(),
});
exports.BlueprintInfoSchema = zod_1.z.object({
    version: zod_1.z.string(),
    squad_id: zod_1.z.string(),
    claw_role: zod_1.z.string(),
    tools_count: zod_1.z.number(),
    has_attestation: zod_1.z.boolean(),
});
exports.BlueprintListSchema = zod_1.z.object({
    versions: zod_1.z.array(zod_1.z.string()),
    current_version: zod_1.z.string(),
    total_versions: zod_1.z.number(),
});
exports.BlueprintDiffSchema = zod_1.z.object({
    tools_added: zod_1.z.array(zod_1.z.string()),
    tools_removed: zod_1.z.array(zod_1.z.string()),
    tools_modified: zod_1.z.array(zod_1.z.string()),
    policy_changes: zod_1.z.record(zod_1.z.string(), zod_1.z.unknown()),
    config_changes: zod_1.z.record(zod_1.z.string(), zod_1.z.unknown()),
});
exports.ToolRegistrySchema = zod_1.z.object({
    tools: zod_1.z.record(zod_1.z.string(), zod_1.z.object({
        version: zod_1.z.string().optional(),
        status: zod_1.z.string().optional(),
        performance_delta: zod_1.z.number().optional(),
    })),
    count: zod_1.z.number(),
});
exports.MarketplaceSearchResultSchema = zod_1.z.object({
    id: zod_1.z.string(),
    name: zod_1.z.string().optional(),
    author: zod_1.z.string().optional(),
    price: zod_1.z.string().optional(),
    verified: zod_1.z.boolean().optional(),
    version: zod_1.z.string().optional(),
    tool_count: zod_1.z.number().optional(),
    fork_count: zod_1.z.number().optional(),
    published_at: zod_1.z.string().optional(),
    tags: zod_1.z.array(zod_1.z.string()).optional(),
});
exports.MarketplaceSearchSchema = zod_1.z.object({
    results: zod_1.z.array(exports.MarketplaceSearchResultSchema),
    count: zod_1.z.number(),
});
exports.MarketplaceDownloadSchema = zod_1.z.object({
    success: zod_1.z.boolean(),
    snapshot: zod_1.z.record(zod_1.z.string(), zod_1.z.unknown()).optional(),
    error: zod_1.z.string().optional(),
});
exports.MarketplacePublishSchema = zod_1.z.object({
    success: zod_1.z.boolean(),
    blueprint_id: zod_1.z.string().optional(),
});
exports.MeshFlowStateSchema = zod_1.z.object({
    signals: zod_1.z.array(zod_1.z.object({
        signal_type: zod_1.z.string().optional(),
        source_claw: zod_1.z.string().optional(),
        destination_claw: zod_1.z.string().optional(),
        last_transmission: zod_1.z.string().optional(),
    })),
    last_transmission: zod_1.z.string().nullable(),
    signal_count_this_week: zod_1.z.number(),
});
exports.HealthStatusSchema = zod_1.z.record(zod_1.z.string(), zod_1.z.object({
    status: zod_1.z.string().optional(),
    tools_active: zod_1.z.number().optional(),
    last_cycle: zod_1.z.string().optional(),
    errors: zod_1.z.array(zod_1.z.string()).optional(),
}));
exports.ProvenanceVerifySchema = zod_1.z.object({
    valid: zod_1.z.boolean(),
    attestation_id: zod_1.z.string().optional(),
    blueprint_id: zod_1.z.string().optional(),
    blueprint_version: zod_1.z.string().optional(),
    author_squad_id: zod_1.z.string().optional(),
    signature_valid: zod_1.z.boolean().optional(),
    content_valid: zod_1.z.boolean().optional(),
    timestamp_valid: zod_1.z.boolean().optional(),
    errors: zod_1.z.array(zod_1.z.string()).optional(),
    warnings: zod_1.z.array(zod_1.z.string()).optional(),
});
exports.ProvenanceKeygenSchema = zod_1.z.object({
    success: zod_1.z.boolean(),
    key_file: zod_1.z.string().optional(),
    public_key: zod_1.z.string().optional(),
    key_id: zod_1.z.string().optional(),
});
exports.BlueprintRollbackSchema = zod_1.z.object({
    success: zod_1.z.boolean(),
    version: zod_1.z.string(),
});
function validateBridgeResponse(schema, response) {
    const result = schema.safeParse(response);
    if (!result.success) {
        throw new Error(`Bridge response validation failed: ${result.error.message}`);
    }
    return result.data;
}
//# sourceMappingURL=bridge-schemas.js.map