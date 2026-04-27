// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import {
  writeFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  appendFileSync,
  readdirSync,
  statSync,
  renameSync,
  unlinkSync,
} from "fs";
import { join } from "path";
import { homedir } from "os";
import { gzipSync, gunzipSync } from "zlib";

export interface AuditEntry {
  timestamp: string;
  messageId?: string;
  clawRole?: string;
  actionType: string;
  decision?: "APPROVED" | "REJECTED" | "DELEGATED" | "AUTO";
  operatorId?: string;
  reason?: string;
  details?: Record<string, unknown>;
}

export interface AuditSearchOptions {
  query?: string;
  from?: string;
  to?: string;
  clawRole?: string;
  decision?: string;
  limit?: number;
}

export interface AuditRotationConfig {
  retentionDays: number;
  compress: boolean;
}

const DEFAULT_RETENTION_DAYS = 90;

export class AuditLogger {
  private auditDir: string;
  private auditFile: string;
  private rotationConfig: AuditRotationConfig;
  private lastRotationCheck: Date | null = null;

  constructor(squadId: string, rotationConfig?: Partial<AuditRotationConfig>) {
    const home = process.env.HOME || process.env.USERPROFILE || homedir() || "/tmp";
    this.auditDir = join(home, ".openclaw-data/milimo", "audit", squadId);
    this.auditFile = join(this.auditDir, "warroom.log");
    this.rotationConfig = {
      retentionDays: rotationConfig?.retentionDays ?? DEFAULT_RETENTION_DAYS,
      compress: rotationConfig?.compress ?? true,
    };
    this.ensureDirectory();
  }

  private ensureDirectory(): void {
    if (!existsSync(this.auditDir)) {
      mkdirSync(this.auditDir, { recursive: true });
    }
  }

  public logAction(entry: Omit<AuditEntry, "timestamp">): void {
    // Check for rotation at midnight
    this.checkRotation();

    const fullEntry: AuditEntry = {
      timestamp: new Date().toISOString(),
      ...entry,
    };

    // Append as a single line JSON (JSONL format)
    appendFileSync(this.auditFile, JSON.stringify(fullEntry) + "\n", "utf8");
  }

  public getRecentLogs(limit: number = 50): AuditEntry[] {
    if (!existsSync(this.auditFile)) {
      return [];
    }

    try {
      const content = readFileSync(this.auditFile, "utf8");
      const lines = content.split("\n").filter((line) => line.trim() !== "");

      // Get the last `limit` lines
      const recentLines = lines.slice(-limit);

      return recentLines.map((line) => JSON.parse(line) as AuditEntry);
    } catch {
      return [];
    }
  }

  // ── Log Rotation ───────────────────────────────────────────────────

  public checkRotation(): void {
    const now = new Date();

    // Only check once per hour at most
    if (this.lastRotationCheck) {
      const hoursSinceCheck = (now.getTime() - this.lastRotationCheck.getTime()) / (1000 * 60 * 60);
      if (hoursSinceCheck < 1) {
        return;
      }
    }

    this.lastRotationCheck = now;

    // Check if we need to rotate (midnight crossing)
    if (!existsSync(this.auditFile)) {
      return;
    }

    const stats = statSync(this.auditFile);
    const fileDate = stats.mtime.toISOString().split("T")[0];
    const today = now.toISOString().split("T")[0];

    if (fileDate !== today) {
      this.rotateLog(fileDate);
    }

    // Clean up old logs
    this.cleanupOldLogs();
  }

  private rotateLog(dateStr: string): void {
    if (!existsSync(this.auditFile)) {
      return;
    }

    const rotatedName = `warroom-${dateStr}.log`;
    const rotatedPath = join(this.auditDir, rotatedName);

    try {
      // Rename current log to dated log
      renameSync(this.auditFile, rotatedPath);

      // Compress if enabled
      if (this.rotationConfig.compress) {
        this.compressLog(rotatedPath);
      }

      // Create new empty log
      writeFileSync(this.auditFile, "");
    } catch (error) {
      console.error("Failed to rotate log:", error);
    }
  }

  private compressLog(logPath: string): void {
    try {
      const content = readFileSync(logPath);
      const compressed = gzipSync(content);
      const gzPath = `${logPath}.gz`;

      writeFileSync(gzPath, compressed);
      unlinkSync(logPath);
    } catch (error) {
      console.error("Failed to compress log:", error);
    }
  }

  private cleanupOldLogs(): void {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - this.rotationConfig.retentionDays);

    try {
      const files = readdirSync(this.auditDir);

      for (const file of files) {
        if (file === "warroom.log" || file === "audit.jsonl") {
          continue;
        }

        const filePath = join(this.auditDir, file);
        const stats = statSync(filePath);

        if (stats.mtime < cutoffDate) {
          unlinkSync(filePath);
        }
      }
    } catch (error) {
      console.error("Failed to cleanup old logs:", error);
    }
  }

  // ── Search ─────────────────────────────────────────────────────────

  public searchLogs(options: AuditSearchOptions): AuditEntry[] {
    const results: AuditEntry[] = [];

    const fromDate = options.from ? new Date(options.from) : null;
    const toDate = options.to ? new Date(options.to) : null;
    const query = options.query?.toLowerCase();
    const limit = options.limit ?? 100;

    // Search in current log
    this.searchInFile(this.auditFile, fromDate, toDate, query, options, results);

    // Search in rotated logs
    try {
      const files = readdirSync(this.auditDir)
        .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
        .sort()
        .reverse();

      for (const file of files) {
        if (results.length >= limit) break;

        const filePath = join(this.auditDir, file);
        this.searchInFile(
          filePath,
          fromDate,
          toDate,
          query,
          options,
          results,
          file.endsWith(".gz"),
        );
      }
    } catch {
      // Ignore errors reading directory
    }

    return results.slice(0, limit);
  }

  private searchInFile(
    filePath: string,
    fromDate: Date | null,
    toDate: Date | null,
    query: string | undefined,
    options: AuditSearchOptions,
    results: AuditEntry[],
    compressed: boolean = false,
  ): void {
    if (!existsSync(filePath)) return;

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
        try {
          const entry = JSON.parse(line) as AuditEntry;

          // Filter by date range
          const entryDate = new Date(entry.timestamp);
          if (fromDate && entryDate < fromDate) continue;
          if (toDate && entryDate > toDate) continue;

          // Filter by claw role
          if (options.clawRole && entry.clawRole !== options.clawRole) continue;

          // Filter by decision
          if (options.decision && entry.decision !== options.decision) continue;

          // Filter by query
          if (query) {
            const entryStr = JSON.stringify(entry).toLowerCase();
            if (!entryStr.includes(query)) continue;
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

  public getRotatedLogs(): string[] {
    try {
      return readdirSync(this.auditDir)
        .filter((f) => f.startsWith("warroom-") && (f.endsWith(".log") || f.endsWith(".gz")))
        .sort()
        .reverse();
    } catch {
      return [];
    }
  }
}

export function createAuditLogger(
  squadId: string,
  config?: Partial<AuditRotationConfig>,
): AuditLogger {
  return new AuditLogger(squadId, config);
}
