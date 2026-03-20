// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Bridge Response Schemas
 *
 * Zod schemas for validating responses from bridge_cli.py
 */

import { z } from "zod";

export const BridgeResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
	z.object({
		success: z.boolean(),
		data: dataSchema.optional(),
		error: z.string().optional(),
	});

export const EvolutionStatusSchema = z.object({
	status: z.string(),
	last_cycle: z.string().nullable(),
	tools_deployed: z.number(),
	pending_proposals: z.number(),
});

export const BlueprintInfoSchema = z.object({
	version: z.string(),
	squad_id: z.string(),
	claw_role: z.string(),
	tools_count: z.number(),
	has_attestation: z.boolean(),
});

export const BlueprintListSchema = z.object({
	versions: z.array(z.string()),
	current_version: z.string(),
	total_versions: z.number(),
});

export const BlueprintDiffSchema = z.object({
	tools_added: z.array(z.string()),
	tools_removed: z.array(z.string()),
	tools_modified: z.array(z.string()),
	policy_changes: z.record(z.string(), z.unknown()),
	config_changes: z.record(z.string(), z.unknown()),
});

export const ToolRegistrySchema = z.object({
	tools: z.record(
		z.string(),
		z.object({
			version: z.string().optional(),
			status: z.string().optional(),
			performance_delta: z.number().optional(),
		})
	),
	count: z.number(),
});

export const MarketplaceSearchResultSchema = z.object({
	id: z.string(),
	name: z.string().optional(),
	author: z.string().optional(),
	price: z.string().optional(),
	verified: z.boolean().optional(),
	version: z.string().optional(),
	tool_count: z.number().optional(),
	fork_count: z.number().optional(),
	published_at: z.string().optional(),
	tags: z.array(z.string()).optional(),
});

export const MarketplaceSearchSchema = z.object({
	results: z.array(MarketplaceSearchResultSchema),
	count: z.number(),
});

export const MarketplaceDownloadSchema = z.object({
	success: z.boolean(),
	snapshot: z.record(z.string(), z.unknown()).optional(),
	error: z.string().optional(),
});

export const MarketplacePublishSchema = z.object({
	success: z.boolean(),
	blueprint_id: z.string().optional(),
});

export const MeshFlowStateSchema = z.object({
	signals: z.array(
		z.object({
			signal_type: z.string().optional(),
			source_claw: z.string().optional(),
			destination_claw: z.string().optional(),
			last_transmission: z.string().optional(),
		})
	),
	last_transmission: z.string().nullable(),
	signal_count_this_week: z.number(),
});

export const HealthStatusSchema = z.record(
	z.string(),
	z.object({
		status: z.string().optional(),
		tools_active: z.number().optional(),
		last_cycle: z.string().optional(),
		errors: z.array(z.string()).optional(),
	})
);

export const ProvenanceVerifySchema = z.object({
	valid: z.boolean(),
	attestation_id: z.string().optional(),
	blueprint_id: z.string().optional(),
	blueprint_version: z.string().optional(),
	author_squad_id: z.string().optional(),
	signature_valid: z.boolean().optional(),
	content_valid: z.boolean().optional(),
	timestamp_valid: z.boolean().optional(),
	errors: z.array(z.string()).optional(),
	warnings: z.array(z.string()).optional(),
});

export const ProvenanceKeygenSchema = z.object({
	success: z.boolean(),
	key_file: z.string().optional(),
	public_key: z.string().optional(),
	key_id: z.string().optional(),
});

export const BlueprintRollbackSchema = z.object({
	success: z.boolean(),
	version: z.string(),
});

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

export function validateBridgeResponse<T>(
	schema: z.ZodSchema<T>,
	response: unknown,
): T {
	const result = schema.safeParse(response);
	if (!result.success) {
		throw new Error(`Bridge response validation failed: ${result.error.message}`);
	}
	return result.data;
}
