"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.DigestScheduler = void 0;
/**
 * Digest Scheduler
 *
 * Schedules morning brief (07:00) and evening wrap (20:00) digests.
 * Uses setTimeout with recalculated delay — no cron, no new deps.
 */
const python_bridge_1 = require("../lib/python-bridge");
class DigestScheduler {
    config;
    bridgeOptions;
    morningTimer = null;
    eveningTimer = null;
    onUpdate;
    onError;
    running = false;
    constructor(options) {
        this.config = options.config;
        this.bridgeOptions = { blueprintDir: options.blueprintDir };
        this.onUpdate = options.onUpdate;
        this.onError = options.onError;
    }
    start() {
        if (this.running) {
            return;
        }
        this.running = true;
        this.scheduleMorning();
        this.scheduleEvening();
    }
    stop() {
        this.running = false;
        if (this.morningTimer) {
            clearTimeout(this.morningTimer);
            this.morningTimer = null;
        }
        if (this.eveningTimer) {
            clearTimeout(this.eveningTimer);
            this.eveningTimer = null;
        }
    }
    scheduleMorning() {
        if (!this.running)
            return;
        const delay = this.calculateDelay(this.config.morning_time);
        this.morningTimer = setTimeout(() => {
            this.getMorningBrief();
            this.scheduleMorning();
        }, delay);
    }
    scheduleEvening() {
        if (!this.running)
            return;
        const delay = this.calculateDelay(this.config.evening_time);
        this.eveningTimer = setTimeout(() => {
            this.getEveningWrap();
            this.scheduleEvening();
        }, delay);
    }
    calculateDelay(target) {
        const now = new Date();
        const targetTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), target.hour, target.minute, 0, 0);
        if (targetTime.getTime() <= now.getTime()) {
            targetTime.setDate(targetTime.getDate() + 1);
        }
        return targetTime.getTime() - now.getTime();
    }
    async getMorningBrief() {
        const response = (0, python_bridge_1.callPythonBridgeSafe)("morning_brief", { squad_id: this.config.squad_id }, this.bridgeOptions);
        if (!response.success || !response.data) {
            const error = new Error(response.error ?? "Morning brief failed");
            this.onError?.(error);
            return null;
        }
        const data = response.data;
        const brief = {
            type: "morning",
            overnight_actions: typeof data.overnight_actions === "number" ? data.overnight_actions : 0,
            queue_summary: data.queue_summary,
            pending_actions: data.pending_actions,
            generated_at: new Date().toISOString(),
        };
        const now = new Date();
        if (now.getDay() === 0 && Array.isArray(data.evolution_updates)) {
            brief.evolution_updates = data.evolution_updates;
        }
        this.onUpdate?.(brief);
        return brief;
    }
    async getEveningWrap() {
        const response = (0, python_bridge_1.callPythonBridgeSafe)("evening_wrap", { squad_id: this.config.squad_id }, this.bridgeOptions);
        if (!response.success || !response.data) {
            const error = new Error(response.error ?? "Evening wrap failed");
            this.onError?.(error);
            return null;
        }
        const data = response.data;
        const brief = {
            type: "evening",
            today_completed: typeof data.today_completed === "number" ? data.today_completed : 0,
            auto_executed: typeof data.auto_executed === "number" ? data.auto_executed : 0,
            remaining_pending: typeof data.remaining_pending === "number" ? data.remaining_pending : 0,
            generated_at: new Date().toISOString(),
        };
        this.onUpdate?.(brief);
        return brief;
    }
    renderBrief(brief) {
        const lines = [];
        const header = brief.type === "morning" ? "☀️ MORNING BRIEF" : "🌙 EVENING WRAP";
        const date = new Date(brief.generated_at).toLocaleDateString();
        lines.push("");
        lines.push(`{bold}${header} — ${date}{/bold}`);
        lines.push("");
        if (brief.type === "morning") {
            if (brief.overnight_actions !== undefined && brief.overnight_actions > 0) {
                lines.push(`✅ Auto-executed overnight: ${brief.overnight_actions}`);
                lines.push("");
            }
            if (brief.queue_summary) {
                lines.push("{bold}Queue Status:{/bold}");
                lines.push(` 🔴 HOLD: ${brief.queue_summary.hold}`);
                lines.push(` 🟡 REVIEW: ${brief.queue_summary.review}`);
                lines.push(` 🟢 AUTO: ${brief.queue_summary.auto}`);
                lines.push("");
            }
            if (brief.pending_actions && brief.pending_actions.length > 0) {
                lines.push("{bold}Pending Actions:{/bold}");
                for (const action of brief.pending_actions.slice(0, 5)) {
                    const priorityEmoji = { HOLD: "🔴", REVIEW: "🟡", AUTO: "🟢" };
                    const emoji = priorityEmoji[action.priority] ?? "⚪";
                    lines.push(` ${emoji} [${action.id.slice(0, 8)}] ${action.claw}: ${action.type}`);
                }
                lines.push("");
            }
            if (brief.evolution_updates && brief.evolution_updates.length > 0) {
                lines.push("{bold}Weekly Evolution Updates:{/bold}");
                for (const update of brief.evolution_updates) {
                    lines.push(` • ${update.claw}: ${update.tool}`);
                }
                lines.push("");
            }
        }
        else {
            lines.push("{bold}Today's Summary:{/bold}");
            if (brief.today_completed !== undefined) {
                lines.push(` Total processed: ${brief.today_completed}`);
            }
            if (brief.auto_executed !== undefined) {
                lines.push(` Auto-executed: ${brief.auto_executed}`);
            }
            if (brief.remaining_pending !== undefined) {
                lines.push(` Remaining pending: ${brief.remaining_pending}`);
            }
            lines.push("");
            if (brief.remaining_pending && brief.remaining_pending > 0) {
                lines.push("{amber-fg}⚠️ Actions still pending for tomorrow{/amber-fg}");
                lines.push("");
            }
        }
        return lines;
    }
    getNextMorningTime() {
        if (!this.running || !this.morningTimer)
            return null;
        const delay = this.calculateDelay(this.config.morning_time);
        return new Date(Date.now() + delay);
    }
    getNextEveningTime() {
        if (!this.running || !this.eveningTimer)
            return null;
        const delay = this.calculateDelay(this.config.evening_time);
        return new Date(Date.now() + delay);
    }
    isRunning() {
        return this.running;
    }
}
exports.DigestScheduler = DigestScheduler;
//# sourceMappingURL=digest.js.map