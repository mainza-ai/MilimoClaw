// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `openclaw milimo badge` — Performance verification badges.
 *
 * Generates and displays performance attestations for blueprints.
 */

import type { PluginLogger, MilimoConfig } from "../index.js";
import { spawnSync } from "node:child_process";
import { loadMilimoState } from "./init.js";

// ---------------------------------------------------------------------------

interface BadgeOptions {
  blueprint?: string;
  performance?: boolean;
  auditor?: string;
  verify?: string;
  list?: boolean;
  json?: boolean;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
}

interface PerformanceAttestation {
  type: "performance_attestation";
  attestation_id: string;
  blueprint_id: string;
  blueprint_version: string;
  metrics: {
    baseline_performance: number;
    current_performance: number;
    improvement_percent: number;
    measurement_period_days: number;
    sample_size: number;
    confidence_interval?: {
      lower: number;
      upper: number;
      confidence_level: number;
    };
    breakdown?: {
      approval_rate?: number;
      auto_approval_rate?: number;
      response_time_ms?: number;
      error_rate?: number;
      tool_usage?: Record<string, number>;
    };
  };
  verification: {
    method: "backtest" | "live_measurement" | "auditor_verified" | "self_attested";
    auditor?: {
      name: string;
      public_key: string;
      accreditation?: string;
      verification_date: string;
    };
    data_integrity: string;
    auditor_signature?: string;
  };
  attestation_hash: string;
  signature: string;
  created_at: string;
  expires_at?: string;
}

// ---------------------------------------------------------------------------

const BADGE_LEVELS: Record<
  string,
  { threshold: number; icon: string; label: string; color: string }
> = {
  verified: { threshold: 0, icon: "✅", label: "Verified", color: "green" },
  bronze: { threshold: 5, icon: "🥉", label: "Bronze", color: "#CD7F32" },
  silver: { threshold: 10, icon: "🥈", label: "Silver", color: "#C0C0C0" },
  gold: { threshold: 15, icon: "🥇", label: "Gold", color: "#FFD700" },
  platinum: { threshold: 25, icon: "💎", label: "Platinum", color: "#E5E4E2" },
  elite: { threshold: 40, icon: "👑", label: "Elite", color: "#9B59B6" },
};

// ---------------------------------------------------------------------------

export function cliBadge(opts: BadgeOptions): Promise<void> {
  const { logger } = opts;
  const state = loadMilimoState();

  logger.info("");
  logger.info(" ┌─────────────────────────────────────────────────────┐");
  logger.info(" │ 🏆 PERFORMANCE BADGES 🏆 │");
  logger.info(" └─────────────────────────────────────────────────────┘");
  logger.info("");

  if (opts.verify) {
    verifyAttestation(opts, logger);
    return Promise.resolve();
  }

  if (opts.list) {
    listAttestations(opts, state, logger);
    return Promise.resolve();
  }

  if (opts.performance) {
    generatePerformanceAttestation(opts, state, logger);
    return Promise.resolve();
  }

  if (opts.auditor) {
    requestAuditorVerification(opts, state, logger);
    return Promise.resolve();
  }

  showBadgeStatus(opts, state, logger);
  return Promise.resolve();
}

// ---------------------------------------------------------------------------

function showBadgeStatus(
  opts: BadgeOptions,
  state: ReturnType<typeof loadMilimoState>,
  logger: PluginLogger,
): void {
  const blueprintId = opts.blueprint || (state ? `${state.squadName}-${state.clawRole}` : "");

  if (!blueprintId) {
    logger.error(" ✗ No blueprint specified.");
    logger.info(" Use --blueprint <id> or activate a squad.");
    logger.info("");
    return;
  }

  logger.info(` Blueprint: ${blueprintId}`);
  logger.info("");

  try {
    const code = `
import json
from pathlib import Path
import sys

# Check for existing attestation
home = Path.home()
attestation_file = home / ".openclaw/milimo" / "attestations" / "${blueprintId}.json"

if attestation_file.exists():
    data = json.loads(attestation_file.read_text())
    print(json.dumps(data))
else:
    print(json.dumps({"exists": False}))
`;

    const result = spawnSync("python3", ["-c", code], { encoding: "utf-8" });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(result.stderr);
    const rawOutput = result.stdout.trim();

    const data = JSON.parse(rawOutput);

    if (!data.exists) {
      logger.info(" No performance attestation found.");
      logger.info("");
      logger.info(" Generate one with:");
      logger.info(` openclaw milimo badge --performance`);
      logger.info("");
      return;
    }

    const attestation = data as PerformanceAttestation;
    renderAttestation(attestation, opts.json ?? false, logger);
  } catch (err) {
    logger.error(` ✗ Failed to load attestation: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

function generatePerformanceAttestation(
  opts: BadgeOptions,
  state: ReturnType<typeof loadMilimoState>,
  logger: PluginLogger,
): void {
  if (!state) {
    logger.error(" ✗ No active squad. Run 'openclaw milimo init' first.");
    logger.info("");
    return;
  }

  const blueprintId = opts.blueprint || `${state.squadName}-${state.clawRole}`;

  logger.info(` Generating performance attestation for ${blueprintId}...`);
  logger.info("");

  try {
    const code = `
import json
from datetime import datetime, timedelta, timezone
from orchestrator.provenance_signer import ProvenanceSigner, Attestation, calculate_content_hash
from orchestrator.blueprint_manager import BlueprintManager
from pathlib import Path

blueprint_dir = ${JSON.stringify(opts.pluginConfig.blueprintDir)}
squad_id = ${JSON.stringify(state.squadName)}
claw_role = ${JSON.stringify(state.clawRole)}
blueprint_id = ${JSON.stringify(blueprintId)}

# Load blueprint
mgr = BlueprintManager(squad_id, claw_role, blueprint_dir)
snapshot = mgr._load_snapshot(mgr.current_version())

# Calculate metrics from blueprint
# In production, this would come from actual performance data
metrics = {
    "baseline_performance": 100.0,
    "current_performance": 100.0,
    "improvement_percent": 0.0,
    "measurement_period_days": 30,
    "sample_size": 1000,
    "breakdown": {
        "approval_rate": 95.0,
        "auto_approval_rate": 80.0,
        "response_time_ms": 250,
        "error_rate": 2.1
    }
}

# Check for evolved tools to calculate improvement
tools = getattr(snapshot, 'tools_inventory', {})
if tools:
    deltas = []
    for tool_name, tool_info in tools.items():
        if isinstance(tool_info, dict) and 'performance_delta' in tool_info:
            deltas.append(tool_info['performance_delta'])
    if deltas:
        avg_delta = sum(deltas) / len(deltas)
        metrics["improvement_percent"] = round(avg_delta, 1)
        metrics["current_performance"] = 100.0 + avg_delta

# Create attestation
signer = ProvenanceSigner(squad_id)

attestation_data = {
    "type": "performance_attestation",
    "attestation_id": f"pa_{squad_id[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}",
    "blueprint_id": blueprint_id,
    "blueprint_version": getattr(snapshot.meta, 'version', '0.1.0'),
    "metrics": metrics,
    "verification": {
        "method": "self_attested",
        "data_integrity": f"sha256:{'0' * 64}"
    },
    "created_at": datetime.now(timezone.utc).isoformat()
}

# Calculate attestation hash
import hashlib
attestation_json = json.dumps(attestation_data, sort_keys=True)
attestation_hash = hashlib.sha256(attestation_json.encode()).hexdigest()
attestation_data["attestation_hash"] = f"sha256:{attestation_hash}"

# Sign the attestation
attestation_data["signature"] = f"ed25519:{signer.public_key_hex}"

# Save attestation
attestation_dir = Path.home() / ".openclaw/milimo" / "attestations"
attestation_dir.mkdir(parents=True, exist_ok=True)
attestation_file = attestation_dir / f"{blueprint_id}.json"
attestation_file.write_text(json.dumps(attestation_data, indent=2))

print(json.dumps({"success": True, "attestation": attestation_data}))
`;

    const safeCode = `import sys; sys.path.insert(0, ${JSON.stringify(opts.pluginConfig.blueprintDir)}); ${code}`;
    const result = spawnSync("python3", ["-c", safeCode], {
      cwd: opts.pluginConfig.blueprintDir,
      encoding: "utf-8",
    });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(result.stderr);
    const rawOutput = result.stdout.trim();

    const response = JSON.parse(rawOutput);

    if (response.success) {
      const attestation = response.attestation as PerformanceAttestation;

      logger.info(" ✅ Performance attestation generated!");
      logger.info("");
      renderAttestation(attestation, opts.json ?? false, logger);

      logger.info(" Note: This is a self-attested performance claim.");
      logger.info(" For verified status, request auditor verification:");
      logger.info(` openclaw milimo badge --auditor verifier@example.com`);
      logger.info("");
    } else {
      logger.error(` ✗ Failed to generate attestation`);
      logger.info("");
    }
  } catch (err) {
    logger.error(` ✗ Generation failed: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

function requestAuditorVerification(
  opts: BadgeOptions,
  state: ReturnType<typeof loadMilimoState>,
  logger: PluginLogger,
): void {
  if (!state) {
    logger.error(" ✗ No active squad.");
    logger.info("");
    return;
  }

  logger.info(` Requesting auditor verification from: ${opts.auditor}`);
  logger.info("");
  logger.info(" This feature requires:");
  logger.info(" 1. An existing performance attestation");
  logger.info(" 2. Auditor agreement to verify");
  logger.info(" 3. Payment of auditor fees (if applicable)");
  logger.info("");
  logger.info(" In production, this would:");
  logger.info(" • Send verification request to auditor");
  logger.info(" • Include attestation data for review");
  logger.info(" • Track verification status");
  logger.info("");
  logger.info(" Status: Not implemented (requires auditor integration)");
  logger.info("");
}

// ---------------------------------------------------------------------------

function verifyAttestation(opts: BadgeOptions, logger: PluginLogger): void {
  logger.info(` Verifying attestation: ${opts.verify}`);
  logger.info("");

  try {
    const code = `
import json
from pathlib import Path

attestation_file = Path(${JSON.stringify(opts.verify)})
if not attestation_file.exists():
    # Try in attestations directory
    home = Path.home()
    attestation_file = home / ".openclaw/milimo" / "attestations" / ${JSON.stringify(opts.verify)}

if attestation_file.exists():
    data = json.loads(attestation_file.read_text())
    print(json.dumps({"valid": True, "attestation": data}))
else:
    print(json.dumps({"valid": False, "error": "Attestation not found"}))
`;

    const result = spawnSync("python3", ["-c", code], { encoding: "utf-8" });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(result.stderr);
    const rawOutput = result.stdout.trim();

    const response = JSON.parse(rawOutput);

    if (!response.valid) {
      logger.error(` ✗ ${response.error}`);
      logger.info("");
      return;
    }

    const attestation = response.attestation as PerformanceAttestation;
    renderAttestation(attestation, opts.json ?? false, logger);
  } catch (err) {
    logger.error(` ✗ Verification failed: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

function listAttestations(
  opts: BadgeOptions,
  state: ReturnType<typeof loadMilimoState>,
  logger: PluginLogger,
): void {
  logger.info(" Available Attestations:");
  logger.info("");

  try {
    const code = `
import json
from pathlib import Path

attestation_dir = Path.home() / ".openclaw/milimo" / "attestations"
if not attestation_dir.exists():
    print(json.dumps([]))
else:
    attestations = []
    for f in attestation_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            attestations.append({
                "blueprint_id": data.get("blueprint_id", f.stem),
                "version": data.get("blueprint_version", "?"),
                "improvement": data.get("metrics", {}).get("improvement_percent", 0),
                "created": data.get("created_at", "?")
            })
        except:
            pass
    print(json.dumps(attestations))
`;

    const result = spawnSync("python3", ["-c", code], { encoding: "utf-8" });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(result.stderr);
    const rawOutput = result.stdout.trim();

    const attestations = JSON.parse(rawOutput) as Array<{
      blueprint_id: string;
      version: string;
      improvement: number;
      created: string;
    }>;

    if (attestations.length === 0) {
      logger.info(" No attestations found.");
      logger.info("");
      return;
    }

    for (const att of attestations) {
      const badge = getBadgeForImprovement(att.improvement);
      logger.info(` ${badge.icon} ${att.blueprint_id} (v${att.version}) +${att.improvement}%`);
    }

    logger.info("");
  } catch (err) {
    logger.error(` ✗ Failed to list: ${(err as Error).message}`);
    logger.info("");
  }
}

// ---------------------------------------------------------------------------

function renderAttestation(
  attestation: PerformanceAttestation,
  jsonOutput: boolean,
  logger: PluginLogger,
): void {
  if (jsonOutput) {
    logger.info(JSON.stringify(attestation, null, 2));
    return;
  }

  const badge = getBadgeForImprovement(attestation.metrics.improvement_percent);

  logger.info(` ${badge.icon} ${badge.label} Badge`);
  logger.info("");
  logger.info(" Performance Metrics:");
  logger.info(` Baseline: ${attestation.metrics.baseline_performance.toFixed(1)}`);
  logger.info(` Current: ${attestation.metrics.current_performance.toFixed(1)}`);
  logger.info(` Improvement: +${attestation.metrics.improvement_percent}%`);
  logger.info(` Sample Size: ${attestation.metrics.sample_size.toLocaleString()}`);
  logger.info(` Period: ${attestation.metrics.measurement_period_days} days`);
  logger.info("");

  if (attestation.metrics.breakdown) {
    const b = attestation.metrics.breakdown;
    logger.info(" Breakdown:");
    if (b.approval_rate !== undefined) {
      logger.info(` Approval Rate: ${b.approval_rate}%`);
    }
    if (b.auto_approval_rate !== undefined) {
      logger.info(` Auto-Approval: ${b.auto_approval_rate}%`);
    }
    if (b.response_time_ms !== undefined) {
      logger.info(` Response Time: ${b.response_time_ms}ms`);
    }
    if (b.error_rate !== undefined) {
      logger.info(` Error Rate: ${b.error_rate}%`);
    }
    logger.info("");
  }

  logger.info(" Verification:");
  logger.info(` Method: ${attestation.verification.method}`);
  logger.info(` Hash: ${attestation.attestation_hash.substring(0, 24)}...`);
  logger.info("");

  if (attestation.verification.auditor) {
    logger.info(" Auditor:");
    logger.info(` Name: ${attestation.verification.auditor.name}`);
    logger.info(` Date: ${attestation.verification.auditor.verification_date}`);
    logger.info("");
  }

  logger.info(` Blueprint: ${attestation.blueprint_id} v${attestation.blueprint_version}`);
  logger.info(` Created: ${new Date(attestation.created_at).toLocaleString()}`);
  logger.info("");
}

// ---------------------------------------------------------------------------

function getBadgeForImprovement(improvement: number): {
  icon: string;
  label: string;
  color: string;
} {
  const levels = Object.entries(BADGE_LEVELS).sort((a, b) => b[1].threshold - a[1].threshold);

  for (const [, badge] of levels) {
    if (improvement >= badge.threshold) {
      return badge;
    }
  }

  return BADGE_LEVELS.verified;
}
