// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo verify` — Blueprint provenance verification.
 *
 * Verifies cryptographic signatures and provenance chains
 * for blueprints to ensure authenticity and integrity.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { execSync } from "node:child_process";
import type { PluginLogger, MilimoConfig } from "../index.js";
import { loadMilimoState } from "./init.js";

// ---------------------------------------------------------------------------

interface VerifyOptions {
  blueprintId?: string;
  version?: string;
  chain?: boolean;
  strict?: boolean;
  json?: boolean;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface AttestationInfo {
  version: string;
  blueprintId: string;
  blueprintVersion: string;
  contentHash: string;
  timestamp: string;
  author: {
    squadId: string;
    publicKey: string;
    keyId: string;
  };
  parentAttestation?: string;
  signature: string;
}

interface VerificationResult {
  valid: boolean;
  attestationId: string;
  blueprintId: string;
  blueprintVersion: string;
  authorSquadId: string;
  signatureValid: boolean;
  contentValid: boolean;
  timestampValid: boolean;
  errors: string[];
  warnings: string[];
}

interface ChainResult {
  valid: boolean;
  chainLength: number;
  genesisAttestationId: string;
  latestAttestationId: string;
  authorSquadIds: string[];
  versionSequence: string[];
  forks: string[];
  errors: string[];
  warnings: string[];
}

// ---------------------------------------------------------------------------

function callPythonVerify(
  blueprintDir: string,
  code: string
): string {
  const cmd = `python3 -c "import sys; sys.path.insert(0, '${blueprintDir}'); ${code}"`;
  return execSync(cmd, { cwd: blueprintDir, encoding: "utf-8" }).trim();
}

// ---------------------------------------------------------------------------

export async function cliVerify(opts: VerifyOptions): Promise<void> {
  const { logger, pluginConfig } = opts;
  const state = loadMilimoState();
  const blueprintDir = pluginConfig.blueprintDir;

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │          🔐  PROVENANCE VERIFICATION  🔐           │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");

  if (!state && !opts.blueprintId) {
    logger.error("  ✗ No blueprint specified and no active squad.");
    logger.info("    Run with --blueprint <id> or activate a squad first.");
    logger.info("");
    return;
  }

  const blueprintId = opts.blueprintId || (state ? `${state.squadName}-${state.clawRole}` : "");
  const version = opts.version || (state ? state.blueprintVersion : "latest");

  if (opts.chain) {
    await verifyChain(opts, blueprintDir, blueprintId, logger);
    return;
  }

  logger.info(`  Blueprint: ${blueprintId}`);
  logger.info(`  Version: ${version}`);
  logger.info("");

  try {
    const code = `
from orchestrator.provenance_verifier import ProvenanceVerifier, verify_attestation
from orchestrator.provenance_signer import Attestation
from orchestrator.blueprint_manager import BlueprintManager
import json

mgr = BlueprintManager('${state?.squadName || "default"}', '${state?.clawRole || "content"}', '${blueprintDir}')
snapshot = mgr._load_snapshot('${version}' if '${version}' != 'latest' else mgr.current_version())

# Get attestation from snapshot
attestation_data = snapshot.integrity.get('attestation', {}) if hasattr(snapshot, 'integrity') else {}
if not attestation_data:
    print(json.dumps({'valid': False, 'errors': ['No attestation found in blueprint']}))
else:
    attestation = Attestation.from_dict(attestation_data)
    verifier = ProvenanceVerifier(strict_mode=${opts.strict ? "True" : "False"})
    result = verifier.verify(attestation)
    result_dict = result.to_dict()
    
    # Verify content if we have the blueprint
    content_result = verifier.verify_content(attestation, snapshot)
    result_dict['content_valid'] = content_result.valid
    result_dict['content_expected_hash'] = content_result.expected_hash[:16] + '...'
    result_dict['content_computed_hash'] = content_result.computed_hash[:16] + '...'
    
    print(json.dumps(result_dict))
`;

    const result = callPythonVerify(blueprintDir, code);
    const verifyResult = JSON.parse(result) as VerificationResult & {
      content_valid: boolean;
      content_expected_hash: string;
      content_computed_hash: string;
    };

    if (opts.json) {
      logger.info(JSON.stringify(verifyResult, null, 2));
      return;
    }

    renderVerificationResult(verifyResult, logger);

  } catch (err) {
    logger.error(`  ✗ Verification failed: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

async function verifyChain(
  opts: VerifyOptions,
  blueprintDir: string,
  blueprintId: string,
  logger: PluginLogger
): Promise<void> {
  logger.info("  Validating provenance chain...");
  logger.info("");

  try {
    const state = loadMilimoState();
    const code = `
from orchestrator.chain_validator import ChainValidator, validate_provenance_chain
from orchestrator.provenance_signer import Attestation
from orchestrator.blueprint_manager import BlueprintManager
import json
import os

mgr = BlueprintManager('${state?.squadName || "default"}', '${state?.clawRole || "content"}', '${blueprintDir}')

# Load all version attestations
attestations = []
versions_dir = mgr._versions_dir
if versions_dir.exists():
    for version_file in sorted(versions_dir.glob('*.json')):
        data = json.loads(version_file.read_text())
        if 'integrity' in data and 'attestation' in data['integrity']:
            att_data = data['integrity']['attestation']
            attestations.append(Attestation.from_dict(att_data))

if not attestations:
    print(json.dumps({'valid': False, 'errors': ['No attestations found in version history']}))
else:
    validator = ChainValidator(strict_mode=${opts.strict ? "True" : "False"})
    result = validator.validate_chain(attestations)
    print(json.dumps(result.to_dict()))
`;

    const result = callPythonVerify(blueprintDir, code);
    const chainResult = JSON.parse(result) as ChainResult;

    if (opts.json) {
      logger.info(JSON.stringify(chainResult, null, 2));
      return;
    }

    renderChainResult(chainResult, logger);

  } catch (err) {
    logger.error(`  ✗ Chain validation failed: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

function renderVerificationResult(
  result: VerificationResult & {
    content_valid: boolean;
    content_expected_hash: string;
    content_computed_hash: string;
  },
  logger: PluginLogger
): void {
  const statusIcon = result.valid ? "✅" : "❌";
  const statusText = result.valid ? "VALID" : "INVALID";

  logger.info(`  Status: ${statusIcon} ${statusText}`);
  logger.info("");
  logger.info("  Details:");
  logger.info(`    Signature: ${result.signatureValid ? "✅ Valid" : "❌ Invalid"}`);
  logger.info(`    Content:   ${result.content_valid ? "✅ Valid" : "❌ Invalid"}`);
  logger.info(`    Timestamp: ${result.timestampValid ? "✅ Valid" : "⚠️  Suspicious"}`);
  logger.info("");

  if (result.content_expected_hash !== result.content_computed_hash) {
    logger.info("  Content Hash Comparison:");
    logger.info(`    Expected: ${result.content_expected_hash}`);
    logger.info(`    Computed: ${result.content_computed_hash}`);
    logger.info("");
  }

  if (result.errors.length > 0) {
    logger.info("  Errors:");
    for (const err of result.errors) {
      logger.info(`    ❌ ${err}`);
    }
    logger.info("");
  }

  if (result.warnings.length > 0) {
    logger.info("  Warnings:");
    for (const warn of result.warnings) {
      logger.info(`    ⚠️  ${warn}`);
    }
    logger.info("");
  }

  logger.info(`  Blueprint ID: ${result.blueprintId}`);
  logger.info(`  Version: ${result.blueprintVersion}`);
  logger.info(`  Author: ${result.authorSquadId}`);
  logger.info("");
}

// ---------------------------------------------------------------------------

function renderChainResult(
  result: ChainResult,
  logger: PluginLogger
): void {
  const statusIcon = result.valid ? "✅" : "❌";
  const statusText = result.valid ? "VALID" : "INVALID";

  logger.info(`  Chain Status: ${statusIcon} ${statusText}`);
  logger.info("");

  if (result.chainLength > 0) {
    logger.info("  Chain Summary:");
    logger.info(`    Attestations: ${result.chainLength}`);
    logger.info(`    Genesis: ${result.genesisAttestationId.substring(0, 16)}...`);
    logger.info(`    Latest:  ${result.latestAttestationId.substring(0, 16)}...`);
    logger.info(`    Authors: ${result.authorSquadIds.join(", ")}`);
    logger.info("");
  }

  if (result.versionSequence.length > 0) {
    logger.info("  Version Sequence:");
    logger.info(`    ${result.versionSequence.join(" → ")}`);
    logger.info("");
  }

  if (result.forks.length > 0) {
    logger.info("  Forks Detected:");
    for (const fork of result.forks) {
      logger.info(`    🔀 ${fork.substring(0, 16)}...`);
    }
    logger.info("");
  }

  if (result.errors.length > 0) {
    logger.info("  Errors:");
    for (const err of result.errors) {
      logger.info(`    ❌ ${err}`);
    }
    logger.info("");
  }

  if (result.warnings.length > 0) {
    logger.info("  Warnings:");
    for (const warn of result.warnings) {
      logger.info(`    ⚠️  ${warn}`);
    }
    logger.info("");
  }
}

// ---------------------------------------------------------------------------
// Key Generation
// ---------------------------------------------------------------------------

interface KeygenOptions {
  squad: string;
  force?: boolean;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

export async function cliProvenanceKeygen(opts: KeygenOptions): Promise<void> {
  const { logger } = opts;

  logger.info("");
  logger.info("  ┌─────────────────────────────────────────────────────┐");
  logger.info("  │          🔑  PROVENANCE KEY GENERATION  🔑         │");
  logger.info("  └─────────────────────────────────────────────────────┘");
  logger.info("");
  logger.info(`  Squad: ${opts.squad}`);
  logger.info("");

  try {
    const home = process.env.HOME || process.env.USERPROFILE || "/tmp";
    const keyDir = path.join(home, ".milimo", "keys");
    const keyFile = path.join(keyDir, `${opts.squad}.json`);

    if (fs.existsSync(keyFile) && !opts.force) {
      logger.error(`  ✗ Key file already exists: ${keyFile}`);
      logger.info("    Use --force to regenerate.");
      logger.info("");
      return;
    }

    fs.mkdirSync(keyDir, { recursive: true });

    const code = `
from orchestrator.provenance_signer import generate_key_pair, save_key_pair
import json

private_key, public_key = generate_key_pair()
key_file = save_key_pair('${opts.squad}', private_key, public_key)

print(json.dumps({
    'success': True,
    'key_file': str(key_file),
    'public_key': public_key.hex(),
    'key_id': public_key[:8].hex()
}))
`;

    const result = execSync(
      `python3 -c "import sys; sys.path.insert(0, '${opts.pluginConfig.blueprintDir}'); ${code}"`,
      { cwd: opts.pluginConfig.blueprintDir, encoding: "utf-8" }
    ).trim();

    const keyInfo = JSON.parse(result) as {
      success: boolean;
      key_file: string;
      public_key: string;
      key_id: string;
    };

    logger.info(`  ✅ Key pair generated`);
    logger.info(`    Key file: ${keyInfo.key_file}`);
    logger.info(`    Key ID:   ${keyInfo.key_id}`);
    logger.info("");
    logger.info("  Your blueprint attestations will now be signed with this key.");
    logger.info("");

  } catch (err) {
    logger.error(`  ✗ Key generation failed: ${(err as Error).message}`);
    logger.info("");
  }
}
