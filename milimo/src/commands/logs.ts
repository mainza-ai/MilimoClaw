// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Logs CLI Commands
 *
 * milimo logs search --query <text> --from <date> --to <date>
 */

import { join } from "node:path";
import { homedir } from "node:os";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { gunzipSync } from "node:zlib";

export interface Logger {
  info: (message: string) => void;
  error: (message: string) => void;
  warn: (message: string) => void;
}

export interface LogsSearchOptions {
  query?: string;
  from?: string;
  to?: string;
  clawRole?: string;
  decision?: string;
  limit?: number;
  json?: boolean;
  squad?: string;
  logger: Logger;
  pluginConfig: { blueprintDir: string };
}

interface AuditEntry {
  timestamp: string;
  messageId?: string;
  clawRole?: string;
  actionType: string;
  decision?: string;
  operatorId?: string;
  reason?: string;
  details?: Record<string, unknown>;
}

export async function cliLogsSearch(options: LogsSearchOptions): Promise<void> {
  const { logger, query, from, to, clawRole, decision, limit = 100, json, squad } = options;

  const squadId = squad || process.env.MILIMO_SQUAD || "default";
  const home = homedir();
  const auditDir = join(home, ".milimo", "audit", squadId);

  if (!existsSync(auditDir)) {
    logger.error(`No audit logs found for squad: ${squadId}`);
    return;
  }

  const results: AuditEntry[] = [];
  const fromDate = from ? new Date(from) : null;
  const toDate = to ? new Date(to) : null;

  // Search in current log
  const currentLog = join(auditDir, "warroom.log");
  if (existsSync(currentLog)) {
    searchInFile(currentLog, fromDate, toDate, query, clawRole, decision, limit, results, false);
  }

  // Search in rotated logs
  try {
    const files = readdirSync(auditDir)
      .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
      .sort()
      .reverse();

    for (const file of files) {
      if (results.length >= limit) break;
      const filePath = join(auditDir, file);
      searchInFile(filePath, fromDate, toDate, query, clawRole, decision, limit, results, file.endsWith(".gz"));
    }
  } catch (error) {
    logger.error(`Failed to read rotated logs: ${(error as Error).message}`);
  }

  if (json) {
    logger.info(JSON.stringify(results.slice(0, limit), null, 2));
  } else if (results.length === 0) {
    logger.info("No matching log entries found.");
  } else {
    logger.info(`Found ${results.length} matching entries:\n`);
    for (const entry of results.slice(0, limit)) {
      const timestamp = entry.timestamp;
      const claw = entry.clawRole?.toUpperCase().padEnd(10) || "UNKNOWN   ";
      const action = entry.actionType.padEnd(20);
      const dec = entry.decision?.padEnd(10) || "N/A       ";
      const msg = entry.messageId?.substring(0, 8) || "N/A";

      logger.info(`${timestamp} | ${claw} | ${action} | ${dec} | ${msg}`);

      if (entry.reason) {
        logger.info(`  Reason: ${entry.reason}`);
      }
      if (entry.details && Object.keys(entry.details).length > 0) {
        logger.info(`  Details: ${JSON.stringify(entry.details)}`);
      }
    }
  }
}

function searchInFile(
  filePath: string,
  fromDate: Date | null,
  toDate: Date | null,
  query: string | undefined,
  clawRole: string | undefined,
  decision: string | undefined,
  limit: number,
  results: AuditEntry[],
  compressed: boolean,
): void {
  try {
    let content: string;

    if (compressed) {
      const compressedData = readFileSync(filePath);
      content = gunzipSync(compressedData).toString("utf8");
    } else {
      content = readFileSync(filePath, "utf8");
    }

    const lines = content.split("\n").filter((l) => l.trim() !== "");

    for (const line of lines) {
      if (results.length >= limit) break;

      try {
        const entry = JSON.parse(line) as AuditEntry;

        // Filter by date range
        const entryDate = new Date(entry.timestamp);
        if (fromDate && entryDate < fromDate) continue;
        if (toDate && entryDate > toDate) continue;

        // Filter by claw role
        if (clawRole && entry.clawRole !== clawRole) continue;

        // Filter by decision
        if (decision && entry.decision !== decision) continue;

        // Filter by query
        if (query) {
          const entryStr = JSON.stringify(entry).toLowerCase();
          if (!entryStr.includes(query.toLowerCase())) continue;
        }

        results.push(entry);
      } catch {
        // Skip malformed entries
      }
    }
  } catch {
    // Ignore errors reading file
  }
}

export async function cliLogsList(options: {
  squad?: string;
  logger: Logger;
  pluginConfig: { blueprintDir: string };
}): Promise<void> {
  const { logger, squad } = options;

  const squadId = squad || process.env.MILIMO_SQUAD || "default";
  const home = homedir();
  const auditDir = join(home, ".milimo", "audit", squadId);

  if (!existsSync(auditDir)) {
    logger.error(`No audit logs found for squad: ${squadId}`);
    return;
  }

  try {
    const files = readdirSync(auditDir)
      .filter((f) => f.startsWith("warroom") && (f.endsWith(".log") || f.endsWith(".gz")))
      .sort()
      .reverse();

    if (files.length === 0) {
      logger.info("No log files found.");
      return;
    }

    logger.info(`Log files for squad ${squadId}:\n`);
    for (const file of files) {
      const filePath = join(auditDir, file);
      const stats = statSync(filePath);
      const sizeKB = Math.round(stats.size / 1024);
      const modified = stats.mtime.toISOString().split("T")[0];
      logger.info(`  ${file.padEnd(30)} ${sizeKB.toString().padStart(6)} KB  ${modified}`);
    }
  } catch (error) {
    logger.error(`Failed to list logs: ${(error as Error).message}`);
  }
}
