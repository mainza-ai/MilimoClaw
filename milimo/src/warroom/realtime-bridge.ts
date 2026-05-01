// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Realtime Bridge — WebSocket Server for Real-Time War Room Updates
 *
 * Provides event-driven updates instead of polling for:
 * - New actions queued (any mode)
 * - Claw status changes (active/idle/processing)
 * - Evolution cycle stage completion
 *
 * WebSocket server on localhost:9876
 */

import { createServer, type Server as HttpServer } from "node:http";
import { WebSocketServer, WebSocket } from "ws";
import { randomUUID } from "node:crypto";
import { join } from "node:path";
import { existsSync, readdirSync, readFileSync, watch, type FSWatcher } from "node:fs";
import { homedir } from "node:os";

export interface RealtimeEvent {
  type: "action_queued" | "status_change" | "evolution_event" | "revenue_update";
  timestamp: string;
  data: RealtimeEventData;
}

export type RealtimeEventData =
  | ActionQueuedEvent
  | StatusChangeEvent
  | EvolutionEvent
  | RevenueUpdateEvent;

export interface ActionQueuedEvent {
  action_id: string;
  claw: string;
  action_type: string;
  priority: "HOLD" | "REVIEW" | "AUTO";
  message_type: string;
  payload: Record<string, unknown>;
}

export interface StatusChangeEvent {
  claw: string;
  previous_status: "active" | "idle" | "processing" | "error";
  new_status: "active" | "idle" | "processing" | "error";
  tool_count: number;
}

export interface EvolutionEvent {
  claw: string;
  stage: "observe" | "identify" | "propose" | "build" | "deploy";
  status: "started" | "completed" | "failed";
  tool_id?: string;
  improvement_pct?: number;
}

export interface RevenueUpdateEvent {
  week_revenue: number;
  week_over_week_pct: number;
  invoices_paid: number;
  invoices_pending: number;
}

export interface RealtimeBridgeOptions {
  port?: number;
  squadId: string;
  blueprintDir?: string;
}

type ActionHandler = (event: ActionQueuedEvent) => void;
type StatusHandler = (event: StatusChangeEvent) => void;
type EvolutionHandler = (event: EvolutionEvent) => void;
type RevenueHandler = (event: RevenueUpdateEvent) => void;

const DEFAULT_PORT = 9876;

export class RealtimeBridge {
  private port: number;
  private squadId: string;
  private blueprintDir: string;
  private server: HttpServer | null = null;
  private wss: WebSocketServer | null = null;
  private clients: Set<WebSocket> = new Set();
  private actionHandlers: ActionHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private evolutionHandlers: EvolutionHandler[] = [];
  private revenueHandlers: RevenueHandler[] = [];
  private fileWatchers: FSWatcher[] = [];
  private clawStatusCache: Map<string, "active" | "idle" | "processing" | "error"> = new Map();
  private running: boolean = false;

  constructor(options: RealtimeBridgeOptions) {
    this.port = options.port ?? DEFAULT_PORT;
    this.squadId = options.squadId;
    this.blueprintDir = options.blueprintDir ?? process.cwd();
  }

  public start(): void {
    if (this.running) return;

    this.server = createServer();
    this.wss = new WebSocketServer({ server: this.server });

    this.wss.on("connection", (ws: WebSocket) => {
      this.clients.add(ws);

      ws.on("close", () => {
        this.clients.delete(ws);
      });

      ws.on("error", () => {
        this.clients.delete(ws);
      });

      this.sendInitialState(ws);
    });

    this.server.listen(this.port, () => {
      this.running = true;
      this.setupFileWatchers();
    });
  }

  public stop(): void {
    this.running = false;

    for (const watcher of this.fileWatchers) {
      watcher.close();
    }
    this.fileWatchers = [];

    for (const client of this.clients) {
      client.close();
    }
    this.clients.clear();

    this.wss?.close();
    this.server?.close();
    this.wss = null;
    this.server = null;
  }

  public onAction(handler: ActionHandler): void {
    this.actionHandlers.push(handler);
  }

  public onHealthUpdate(handler: StatusHandler): void {
    this.statusHandlers.push(handler);
  }

  public onEvolutionEvent(handler: EvolutionHandler): void {
    this.evolutionHandlers.push(handler);
  }

  public onRevenueUpdate(handler: RevenueHandler): void {
    this.revenueHandlers.push(handler);
  }

  public broadcast(event: RealtimeEvent): void {
    const message = JSON.stringify(event);
    for (const client of this.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    }
  }

  private sendInitialState(ws: WebSocket): void {
    const home = homedir();
    const meshDir = join(home, ".openclaw/milimo", "mesh");

    const initialState = {
      type: "initial_state",
      timestamp: new Date().toISOString(),
      data: {
        squad_id: this.squadId,
        pending_actions: this.getPendingActions(meshDir),
        claw_status: this.getClawStatuses(),
      },
    };

    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(initialState));
    }
  }

  private setupFileWatchers(): void {
    const home = homedir();
    const baseDir = join(home, ".openclaw/milimo");

    const watchPaths = [
      join(baseDir, "mesh", "inbox", "war_room"),
      join(baseDir, "queue", "pending"),
      join(baseDir, "logs"),
      join(baseDir, "tools", this.squadId),
      join(baseDir, "finance", "revenue"),
    ];

    for (const watchPath of watchPaths) {
      if (existsSync(watchPath)) {
        try {
          const watcher = watch(watchPath, (eventType, filename) => {
            if (eventType === "rename" && filename) {
              this.handleFileChange(watchPath, filename);
            }
          });
          this.fileWatchers.push(watcher);
        } catch {
          // Ignore watch errors
        }
      }
    }

    const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];
    for (const role of clawRoles) {
      const registryPath = join(baseDir, "tools", this.squadId, role, "registry.json");
      if (existsSync(registryPath)) {
        try {
          const watcher = watch(registryPath, () => {
            this.checkClawStatusChange(role);
          });
          this.fileWatchers.push(watcher);
        } catch {
          // Ignore watch errors
        }
      }
    }
  }

  private handleFileChange(watchPath: string, filename: string): void {
    if (!filename.endsWith(".json")) return;

    const filePath = join(watchPath, filename);

    if (watchPath.includes("inbox") || watchPath.includes("pending")) {
      this.checkForNewAction(filePath);
    } else if (watchPath.includes("revenue")) {
      this.checkForRevenueUpdate();
    }
  }

  private checkForNewAction(filePath: string): void {
    try {
      if (!existsSync(filePath)) return;

      const content = readFileSync(filePath, "utf-8");
      const msg = JSON.parse(content);

      const event: RealtimeEvent = {
        type: "action_queued",
        timestamp: new Date().toISOString(),
        data: {
          action_id: msg.message_id ?? randomUUID(),
          claw: msg.sender_role ?? "unknown",
          action_type: msg.action_type ?? msg.message_type ?? "unknown",
          priority: msg.priority ?? "REVIEW",
          message_type: msg.message_type ?? "unknown",
          payload: msg.payload ?? {},
        },
      };

      this.broadcast(event);

      for (const handler of this.actionHandlers) {
        handler(event.data as ActionQueuedEvent);
      }
    } catch {
      // Ignore parse errors
    }
  }

  private checkClawStatusChange(role: string): void {
    const home = homedir();
    const baseDir = join(home, ".openclaw/milimo");
    const registryPath = join(baseDir, "tools", this.squadId, role, "registry.json");

    let newStatus: "active" | "idle" | "processing" | "error" = "idle";
    let toolCount = 0;

    try {
      if (existsSync(registryPath)) {
        const content = readFileSync(registryPath, "utf-8");
        const data = JSON.parse(content);
        toolCount = Object.keys(data.tools ?? {}).length;
        newStatus = toolCount > 0 ? "active" : "idle";
      }
    } catch {
      newStatus = "error";
    }

    const pendingDir = join(baseDir, "queue", "pending");
    if (existsSync(pendingDir)) {
      try {
        for (const file of readdirSync(pendingDir)) {
          if (!file.endsWith(".json")) continue;
          try {
            const msg = JSON.parse(readFileSync(join(pendingDir, file), "utf-8"));
            if (msg.sender_role === role && msg.priority === "HOLD") {
              newStatus = "processing";
              break;
            }
          } catch {
            // Ignore parse errors
          }
        }
      } catch {
        // Ignore read errors
      }
    }

    const previousStatus = this.clawStatusCache.get(role);
    this.clawStatusCache.set(role, newStatus);

    if (previousStatus && previousStatus !== newStatus) {
      const event: RealtimeEvent = {
        type: "status_change",
        timestamp: new Date().toISOString(),
        data: {
          claw: role,
          previous_status: previousStatus,
          new_status: newStatus,
          tool_count: toolCount,
        },
      };

      this.broadcast(event);

      for (const handler of this.statusHandlers) {
        handler(event.data as StatusChangeEvent);
      }
    }
  }

  private checkForRevenueUpdate(): void {
    const home = homedir();
    const summaryPath = join(home, ".openclaw/milimo", "finance", "revenue", "weekly_summary.json");

    try {
      if (!existsSync(summaryPath)) return;

      const content = readFileSync(summaryPath, "utf-8");
      const data = JSON.parse(content);
      const currentWeek = data.current_week ?? {};

      const event: RealtimeEvent = {
        type: "revenue_update",
        timestamp: new Date().toISOString(),
        data: {
          week_revenue: parseFloat(currentWeek.total_revenue) ?? 0,
          week_over_week_pct: parseFloat(data.week_over_week_pct) ?? 0,
          invoices_paid: parseInt(currentWeek.invoices_paid, 10) ?? 0,
          invoices_pending: parseInt(data.pending_invoices, 10) ?? 0,
        },
      };

      this.broadcast(event);

      for (const handler of this.revenueHandlers) {
        handler(event.data as RevenueUpdateEvent);
      }
    } catch {
      // Ignore parse errors
    }
  }

  private getPendingActions(meshDir: string): Array<{
    action_id: string;
    claw: string;
    action_type: string;
    priority: string;
  }> {
    const actions: Array<{
      action_id: string;
      claw: string;
      action_type: string;
      priority: string;
    }> = [];

    const warRoomInbox = join(meshDir, "inbox", "war_room");
    if (existsSync(warRoomInbox)) {
      try {
        for (const file of readdirSync(warRoomInbox)) {
          if (!file.endsWith(".json")) continue;
          try {
            const msg = JSON.parse(readFileSync(join(warRoomInbox, file), "utf-8"));
            actions.push({
              action_id: msg.message_id ?? file,
              claw: msg.sender_role ?? "unknown",
              action_type: msg.action_type ?? msg.message_type ?? "unknown",
              priority: msg.priority ?? "REVIEW",
            });
          } catch {
            // Ignore parse errors
          }
        }
      } catch {
        // Ignore read errors
      }
    }

    return actions;
  }

  private getClawStatuses(): Record<string, { status: string; tool_count: number }> {
    const home = homedir();
    const baseDir = join(home, ".openclaw/milimo");
    const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];
    const statuses: Record<string, { status: string; tool_count: number }> = {};

    for (const role of clawRoles) {
      let status: "active" | "idle" | "processing" | "error" = "idle";
      let toolCount = 0;

      const registryPath = join(baseDir, "tools", this.squadId, role, "registry.json");
      try {
        if (existsSync(registryPath)) {
          const data = JSON.parse(readFileSync(registryPath, "utf-8"));
          toolCount = Object.keys(data.tools ?? {}).length;
          status = toolCount > 0 ? "active" : "idle";
          this.clawStatusCache.set(role, status);
        }
      } catch {
        status = "error";
      }

      statuses[role] = { status, tool_count: toolCount };
    }

    return statuses;
  }

  public getConnectedClients(): number {
    return this.clients.size;
  }

  public isRunning(): boolean {
    return this.running;
  }
}

export function createRealtimeBridge(options: RealtimeBridgeOptions): RealtimeBridge {
  return new RealtimeBridge(options);
}
