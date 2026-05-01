"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.RealtimeBridge = void 0;
exports.createRealtimeBridge = createRealtimeBridge;
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
const node_http_1 = require("node:http");
const ws_1 = require("ws");
const node_crypto_1 = require("node:crypto");
const node_path_1 = require("node:path");
const node_fs_1 = require("node:fs");
const node_os_1 = require("node:os");
const DEFAULT_PORT = 9876;
class RealtimeBridge {
    port;
    squadId;
    blueprintDir;
    server = null;
    wss = null;
    clients = new Set();
    actionHandlers = [];
    statusHandlers = [];
    evolutionHandlers = [];
    revenueHandlers = [];
    fileWatchers = [];
    clawStatusCache = new Map();
    running = false;
    constructor(options) {
        this.port = options.port ?? DEFAULT_PORT;
        this.squadId = options.squadId;
        this.blueprintDir = options.blueprintDir ?? process.cwd();
    }
    start() {
        if (this.running)
            return;
        this.server = (0, node_http_1.createServer)();
        this.wss = new ws_1.WebSocketServer({ server: this.server });
        this.wss.on("connection", (ws) => {
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
    stop() {
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
    onAction(handler) {
        this.actionHandlers.push(handler);
    }
    onHealthUpdate(handler) {
        this.statusHandlers.push(handler);
    }
    onEvolutionEvent(handler) {
        this.evolutionHandlers.push(handler);
    }
    onRevenueUpdate(handler) {
        this.revenueHandlers.push(handler);
    }
    broadcast(event) {
        const message = JSON.stringify(event);
        for (const client of this.clients) {
            if (client.readyState === ws_1.WebSocket.OPEN) {
                client.send(message);
            }
        }
    }
    sendInitialState(ws) {
        const home = (0, node_os_1.homedir)();
        const meshDir = (0, node_path_1.join)(home, ".openclaw/milimo", "mesh");
        const initialState = {
            type: "initial_state",
            timestamp: new Date().toISOString(),
            data: {
                squad_id: this.squadId,
                pending_actions: this.getPendingActions(meshDir),
                claw_status: this.getClawStatuses(),
            },
        };
        if (ws.readyState === ws_1.WebSocket.OPEN) {
            ws.send(JSON.stringify(initialState));
        }
    }
    setupFileWatchers() {
        const home = (0, node_os_1.homedir)();
        const baseDir = (0, node_path_1.join)(home, ".openclaw/milimo");
        const watchPaths = [
            (0, node_path_1.join)(baseDir, "mesh", "inbox", "war_room"),
            (0, node_path_1.join)(baseDir, "queue", "pending"),
            (0, node_path_1.join)(baseDir, "logs"),
            (0, node_path_1.join)(baseDir, "tools", this.squadId),
            (0, node_path_1.join)(baseDir, "finance", "revenue"),
        ];
        for (const watchPath of watchPaths) {
            if ((0, node_fs_1.existsSync)(watchPath)) {
                try {
                    const watcher = (0, node_fs_1.watch)(watchPath, (eventType, filename) => {
                        if (eventType === "rename" && filename) {
                            this.handleFileChange(watchPath, filename);
                        }
                    });
                    this.fileWatchers.push(watcher);
                }
                catch {
                    // Ignore watch errors
                }
            }
        }
        const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];
        for (const role of clawRoles) {
            const registryPath = (0, node_path_1.join)(baseDir, "tools", this.squadId, role, "registry.json");
            if ((0, node_fs_1.existsSync)(registryPath)) {
                try {
                    const watcher = (0, node_fs_1.watch)(registryPath, () => {
                        this.checkClawStatusChange(role);
                    });
                    this.fileWatchers.push(watcher);
                }
                catch {
                    // Ignore watch errors
                }
            }
        }
    }
    handleFileChange(watchPath, filename) {
        if (!filename.endsWith(".json"))
            return;
        const filePath = (0, node_path_1.join)(watchPath, filename);
        if (watchPath.includes("inbox") || watchPath.includes("pending")) {
            this.checkForNewAction(filePath);
        }
        else if (watchPath.includes("revenue")) {
            this.checkForRevenueUpdate();
        }
    }
    checkForNewAction(filePath) {
        try {
            if (!(0, node_fs_1.existsSync)(filePath))
                return;
            const content = (0, node_fs_1.readFileSync)(filePath, "utf-8");
            const msg = JSON.parse(content);
            const event = {
                type: "action_queued",
                timestamp: new Date().toISOString(),
                data: {
                    action_id: msg.message_id ?? (0, node_crypto_1.randomUUID)(),
                    claw: msg.sender_role ?? "unknown",
                    action_type: msg.action_type ?? msg.message_type ?? "unknown",
                    priority: msg.priority ?? "REVIEW",
                    message_type: msg.message_type ?? "unknown",
                    payload: msg.payload ?? {},
                },
            };
            this.broadcast(event);
            for (const handler of this.actionHandlers) {
                handler(event.data);
            }
        }
        catch {
            // Ignore parse errors
        }
    }
    checkClawStatusChange(role) {
        const home = (0, node_os_1.homedir)();
        const baseDir = (0, node_path_1.join)(home, ".openclaw/milimo");
        const registryPath = (0, node_path_1.join)(baseDir, "tools", this.squadId, role, "registry.json");
        let newStatus = "idle";
        let toolCount = 0;
        try {
            if ((0, node_fs_1.existsSync)(registryPath)) {
                const content = (0, node_fs_1.readFileSync)(registryPath, "utf-8");
                const data = JSON.parse(content);
                toolCount = Object.keys(data.tools ?? {}).length;
                newStatus = toolCount > 0 ? "active" : "idle";
            }
        }
        catch {
            newStatus = "error";
        }
        const pendingDir = (0, node_path_1.join)(baseDir, "queue", "pending");
        if ((0, node_fs_1.existsSync)(pendingDir)) {
            try {
                for (const file of (0, node_fs_1.readdirSync)(pendingDir)) {
                    if (!file.endsWith(".json"))
                        continue;
                    try {
                        const msg = JSON.parse((0, node_fs_1.readFileSync)((0, node_path_1.join)(pendingDir, file), "utf-8"));
                        if (msg.sender_role === role && msg.priority === "HOLD") {
                            newStatus = "processing";
                            break;
                        }
                    }
                    catch {
                        // Ignore parse errors
                    }
                }
            }
            catch {
                // Ignore read errors
            }
        }
        const previousStatus = this.clawStatusCache.get(role);
        this.clawStatusCache.set(role, newStatus);
        if (previousStatus && previousStatus !== newStatus) {
            const event = {
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
                handler(event.data);
            }
        }
    }
    checkForRevenueUpdate() {
        const home = (0, node_os_1.homedir)();
        const summaryPath = (0, node_path_1.join)(home, ".openclaw/milimo", "finance", "revenue", "weekly_summary.json");
        try {
            if (!(0, node_fs_1.existsSync)(summaryPath))
                return;
            const content = (0, node_fs_1.readFileSync)(summaryPath, "utf-8");
            const data = JSON.parse(content);
            const currentWeek = data.current_week ?? {};
            const event = {
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
                handler(event.data);
            }
        }
        catch {
            // Ignore parse errors
        }
    }
    getPendingActions(meshDir) {
        const actions = [];
        const warRoomInbox = (0, node_path_1.join)(meshDir, "inbox", "war_room");
        if ((0, node_fs_1.existsSync)(warRoomInbox)) {
            try {
                for (const file of (0, node_fs_1.readdirSync)(warRoomInbox)) {
                    if (!file.endsWith(".json"))
                        continue;
                    try {
                        const msg = JSON.parse((0, node_fs_1.readFileSync)((0, node_path_1.join)(warRoomInbox, file), "utf-8"));
                        actions.push({
                            action_id: msg.message_id ?? file,
                            claw: msg.sender_role ?? "unknown",
                            action_type: msg.action_type ?? msg.message_type ?? "unknown",
                            priority: msg.priority ?? "REVIEW",
                        });
                    }
                    catch {
                        // Ignore parse errors
                    }
                }
            }
            catch {
                // Ignore read errors
            }
        }
        return actions;
    }
    getClawStatuses() {
        const home = (0, node_os_1.homedir)();
        const baseDir = (0, node_path_1.join)(home, ".openclaw/milimo");
        const clawRoles = ["content", "ops", "analytics", "finance", "build", "assistant"];
        const statuses = {};
        for (const role of clawRoles) {
            let status = "idle";
            let toolCount = 0;
            const registryPath = (0, node_path_1.join)(baseDir, "tools", this.squadId, role, "registry.json");
            try {
                if ((0, node_fs_1.existsSync)(registryPath)) {
                    const data = JSON.parse((0, node_fs_1.readFileSync)(registryPath, "utf-8"));
                    toolCount = Object.keys(data.tools ?? {}).length;
                    status = toolCount > 0 ? "active" : "idle";
                    this.clawStatusCache.set(role, status);
                }
            }
            catch {
                status = "error";
            }
            statuses[role] = { status, tool_count: toolCount };
        }
        return statuses;
    }
    getConnectedClients() {
        return this.clients.size;
    }
    isRunning() {
        return this.running;
    }
}
exports.RealtimeBridge = RealtimeBridge;
function createRealtimeBridge(options) {
    return new RealtimeBridge(options);
}
//# sourceMappingURL=realtime-bridge.js.map