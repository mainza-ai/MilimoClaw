// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Action CLI Commands
 *
 * milimo action approve <action_id>
 * milimo action block <action_id>
 *
 * Work without opening TUI. Read pending queue from file,
 * update decision, trigger downstream execution.
 */

import { join } from "node:path";
import { homedir } from "node:os";
import {
  existsSync,
  readdirSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
  mkdirSync,
} from "node:fs";

export interface Logger {
  info: (message: string) => void;
  error: (message: string) => void;
  warn: (message: string) => void;
}

export interface ActionCliOptions {
  logger: Logger;
  pluginConfig: { blueprintDir: string };
}

export interface PendingAction {
  message_id: string;
  sender_role: string;
  recipient_role: string;
  message_type: string;
  payload: Record<string, unknown>;
  squad_id: string;
  timestamp: string;
  needs_approval: boolean;
  file_path: string;
  priority?: string;
}

export function cliActionApprove(options: ActionCliOptions & { actionId: string }): Promise<void> {
  const { logger, actionId } = options;

  const home = homedir();
  const meshDir = join(home, ".milimo", "mesh");
  const warRoomInbox = join(meshDir, "inbox", "war_room");
  const approvedDir = join(meshDir, "approved");
  const logsDir = join(home, ".milimo", "logs");

  if (!existsSync(warRoomInbox)) {
    logger.error("No pending actions found. War Room inbox does not exist.");
    process.exit(1);
  }

  const action = findActionById(warRoomInbox, actionId);

  if (!action) {
    logger.error(`Action not found: ${actionId}`);
    process.exit(1);
  }

  mkdirSync(approvedDir, { recursive: true });

  const fileName = action.file_path.split("/").pop()!;
  const targetPath = join(approvedDir, fileName);

  try {
    renameSync(action.file_path, targetPath);

    logDecision(logsDir, {
      action_id: actionId,
      decision: "APPROVED",
      operator: "cli",
      timestamp: new Date().toISOString(),
      claw: action.sender_role,
      action_type: action.message_type,
    });

    logger.info(`✓ Action approved: ${actionId}`);
    logger.info(` Claw: ${action.sender_role.toUpperCase()}`);
    logger.info(` Type: ${action.message_type}`);

    if (action.message_type === "tool_proposal" && action.payload?.tool_name) {
      logger.info(` Tool: ${action.payload.tool_name as string}`);
    }

    if (action.payload?.amount) {
      logger.info(` Amount: $${action.payload.amount as number}`);
    }
  } catch (error) {
    logger.error(`Failed to approve action: ${(error as Error).message}`);
    process.exit(1);
  }

  return Promise.resolve();
}

export function cliActionBlock(
  options: ActionCliOptions & { actionId: string; reason?: string },
): Promise<void> {
  const { logger, actionId, reason } = options;

  const home = homedir();
  const meshDir = join(home, ".milimo", "mesh");
  const warRoomInbox = join(meshDir, "inbox", "war_room");
  const rejectedDir = join(meshDir, "rejected");
  const logsDir = join(home, ".milimo", "logs");

  if (!existsSync(warRoomInbox)) {
    logger.error("No pending actions found. War Room inbox does not exist.");
    process.exit(1);
  }

  const action = findActionById(warRoomInbox, actionId);

  if (!action) {
    logger.error(`Action not found: ${actionId}`);
    process.exit(1);
  }

  mkdirSync(rejectedDir, { recursive: true });

  const fileName = action.file_path.split("/").pop()!;
  const targetPath = join(rejectedDir, fileName);

  try {
    const rejectedAction = {
      ...action,
      rejected_at: new Date().toISOString(),
      rejection_reason: reason ?? "Blocked via CLI",
    };

    writeFileSync(targetPath, JSON.stringify(rejectedAction, null, 2));
    unlinkSync(action.file_path);

    logDecision(logsDir, {
      action_id: actionId,
      decision: "BLOCKED",
      operator: "cli",
      timestamp: new Date().toISOString(),
      claw: action.sender_role,
      action_type: action.message_type,
      reason: reason,
    });

    logger.info(`✗ Action blocked: ${actionId}`);
    logger.info(` Claw: ${action.sender_role.toUpperCase()}`);
    logger.info(` Type: ${action.message_type}`);

    if (reason) {
      logger.info(` Reason: ${reason}`);
    }
  } catch (error) {
    logger.error(`Failed to block action: ${(error as Error).message}`);
    process.exit(1);
  }

  return Promise.resolve();
}

export function listPendingActions(): PendingAction[] {
  const home = homedir();
  const warRoomInbox = join(home, ".milimo", "mesh", "inbox", "war_room");

  if (!existsSync(warRoomInbox)) {
    return [];
  }

  const actions: PendingAction[] = [];

  try {
    const files = readdirSync(warRoomInbox).filter((f) => f.endsWith(".json"));

    for (const file of files) {
      const filePath = join(warRoomInbox, file);
      try {
        const content = readFileSync(filePath, "utf-8");
        const msg = JSON.parse(content);
        actions.push({
          ...msg,
          file_path: filePath,
        });
      } catch {
        // Ignore parse errors
      }
    }
  } catch {
    // Ignore read errors
  }

  return actions.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
}

function findActionById(inboxDir: string, actionId: string): PendingAction | null {
  try {
    const files = readdirSync(inboxDir).filter((f) => f.endsWith(".json"));

    for (const file of files) {
      const filePath = join(inboxDir, file);
      try {
        const content = readFileSync(filePath, "utf-8");
        const msg = JSON.parse(content);

        if (msg.message_id === actionId || file.includes(actionId)) {
          return {
            ...msg,
            file_path: filePath,
          };
        }
      } catch {
        // Ignore parse errors
      }
    }
  } catch {
    // Ignore read errors
  }

  return null;
}

function logDecision(logsDir: string, entry: Record<string, unknown>): void {
  try {
    const logFile = join(logsDir, "warroom.log");
    const logLine = `${new Date().toISOString()} - cli - INFO - Decision: ${JSON.stringify(entry)}\n`;

    mkdirSync(logsDir, { recursive: true });
    writeFileSync(logFile, logLine, { flag: "a" });
  } catch {
    // Ignore logging errors
  }
}
