// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Operator Notifier — System notifications when TUI is closed
 *
 * Platform-specific notification delivery:
 * - macOS: osascript (no new deps)
 * - Linux: notify-send (no new deps)
 * - Fallback: write to ~/.openclaw/milimo/notifications/pending.json
 */

import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { homedir } from "node:os";
import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "node:fs";

export interface NotificationPayload {
  action_id: string;
  claw: string;
  action_type: string;
  summary: string;
  priority: "HOLD" | "REVIEW" | "AUTO";
  timestamp: string;
}

export interface NotificationResult {
  delivered: boolean;
  method: "osascript" | "notify-send" | "pending_file" | "disabled";
  error?: string;
}

const NOTIFICATION_DIR = ".openclaw/milimo/notifications";
const PENDING_FILE = "pending.json";

export class OperatorNotifier {
  private notificationDir: string;
  private pendingFile: string;
  private enabled: boolean;

  constructor(enabled: boolean = true) {
    const home = homedir();
    this.notificationDir = join(home, NOTIFICATION_DIR);
    this.pendingFile = join(this.notificationDir, PENDING_FILE);
    this.enabled = enabled;

    this.ensureNotificationDir();
  }

  public notify(payload: NotificationPayload): NotificationResult {
    if (!this.enabled) {
      return { delivered: false, method: "disabled" };
    }

    if (payload.priority !== "HOLD") {
      return { delivered: false, method: "disabled" };
    }

    const title = "🦀 WAR ROOM";
    const subtitle = `${payload.claw.toUpperCase()} CLAW`;
    const message = `${subtitle} | ${payload.summary}`;

    switch (process.platform) {
      case "darwin":
        return this.notifyMacOS(title, message, payload);
      case "linux":
        return this.notifyLinux(title, message, payload);
      default:
        return this.notifyPendingFile(payload);
    }
  }

  public notifyHoldRelease(actionId: string): NotificationResult {
    if (!this.enabled) {
      return { delivered: false, method: "disabled" };
    }

    const title = "🦀 WAR ROOM";
    const message = `HOLD released — action ${actionId} approved`;

    switch (process.platform) {
      case "darwin":
        return this.notifyMacOS(title, message, { action_id: actionId } as NotificationPayload);
      case "linux":
        return this.notifyLinux(title, message, { action_id: actionId } as NotificationPayload);
      default:
        return { delivered: true, method: "pending_file" };
    }
  }

  private notifyMacOS(
    title: string,
    message: string,
    _payload: NotificationPayload,
  ): NotificationResult {
    const script = `display notification "${this.escapeAppleScript(message)}" with title "${this.escapeAppleScript(title)}"`;

    try {
      const result = spawnSync("osascript", ["-e", script], {
        encoding: "utf-8",
        timeout: 5000,
      });

      if (result.status === 0) {
        return { delivered: true, method: "osascript" };
      }

      return this.notifyPendingFile(_payload);
    } catch (error) {
      return {
        delivered: false,
        method: "osascript",
        error: (error as Error).message,
      };
    }
  }

  private notifyLinux(
    title: string,
    message: string,
    _payload: NotificationPayload,
  ): NotificationResult {
    try {
      const result = spawnSync("notify-send", [title, message], {
        encoding: "utf-8",
        timeout: 5000,
      });

      if (result.status === 0) {
        return { delivered: true, method: "notify-send" };
      }

      return this.notifyPendingFile(_payload);
    } catch (error) {
      return {
        delivered: false,
        method: "notify-send",
        error: (error as Error).message,
      };
    }
  }

  private notifyPendingFile(payload: NotificationPayload): NotificationResult {
    try {
      let pending: NotificationPayload[] = [];

      if (existsSync(this.pendingFile)) {
        try {
          const content = readFileSync(this.pendingFile, "utf-8");
          pending = JSON.parse(content);
          if (!Array.isArray(pending)) {
            pending = [];
          }
        } catch {
          pending = [];
        }
      }

      pending.push(payload);

      writeFileSync(this.pendingFile, JSON.stringify(pending, null, 2));

      return { delivered: true, method: "pending_file" };
    } catch (error) {
      return {
        delivered: false,
        method: "pending_file",
        error: (error as Error).message,
      };
    }
  }

  public getPendingNotifications(): NotificationPayload[] {
    if (!existsSync(this.pendingFile)) {
      return [];
    }

    try {
      const content = readFileSync(this.pendingFile, "utf-8");
      const pending = JSON.parse(content);
      return Array.isArray(pending) ? pending : [];
    } catch {
      return [];
    }
  }

  public clearPendingNotification(actionId: string): void {
    if (!existsSync(this.pendingFile)) {
      return;
    }

    try {
      const content = readFileSync(this.pendingFile, "utf-8");
      let pending: NotificationPayload[] = JSON.parse(content);
      if (!Array.isArray(pending)) {
        pending = [];
      }

      pending = pending.filter((n) => n.action_id !== actionId);

      if (pending.length === 0) {
        unlinkSync(this.pendingFile);
      } else {
        writeFileSync(this.pendingFile, JSON.stringify(pending, null, 2));
      }
    } catch {
      // Ignore errors
    }
  }

  public clearAllPending(): void {
    if (existsSync(this.pendingFile)) {
      try {
        unlinkSync(this.pendingFile);
      } catch {
        // Ignore errors
      }
    }
  }

  private ensureNotificationDir(): void {
    if (!existsSync(this.notificationDir)) {
      try {
        mkdirSync(this.notificationDir, { recursive: true });
      } catch {
        // Ignore errors
      }
    }
  }

  private escapeAppleScript(str: string): string {
    return str.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }
}

export function createNotifier(enabled: boolean = true): OperatorNotifier {
  return new OperatorNotifier(enabled);
}
