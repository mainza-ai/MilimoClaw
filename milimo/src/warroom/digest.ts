// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Digest Scheduler
 *
 * Schedules morning brief (07:00) and evening wrap (20:00) digests.
 * Uses setTimeout with recalculated delay — no cron, no new deps.
 */

import { callPythonBridgeSafe, type BridgeCommandOptions } from "../lib/python-bridge";

export interface DigestBrief {
  type: "morning" | "evening";
  overnight_actions?: number;
  queue_summary?: {
    hold: number;
    review: number;
    auto: number;
  };
  pending_actions?: Array<{
    id: string;
    claw: string;
    type: string;
    priority: string;
  }>;
  today_completed?: number;
  auto_executed?: number;
  remaining_pending?: number;
  evolution_updates?: Array<{
    claw: string;
    tool: string;
    timestamp: string;
  }>;
  alerts?: Array<{
    level: string;
    message: string;
  }>;
  generated_at: string;
}

export interface DigestConfig {
  morning_time: { hour: number; minute: number };
  evening_time: { hour: number; minute: number };
  squad_id: string;
}

export interface DigestScheduleOptions {
  config: DigestConfig;
  blueprintDir: string;
  onUpdate?: (brief: DigestBrief) => void;
  onError?: (error: Error) => void;
}

export class DigestScheduler {
  private config: DigestConfig;
  private bridgeOptions: BridgeCommandOptions;
  private morningTimer: NodeJS.Timeout | null = null;
  private eveningTimer: NodeJS.Timeout | null = null;
  private onUpdate?: (brief: DigestBrief) => void;
  private onError?: (error: Error) => void;
  private running: boolean = false;

  constructor(options: DigestScheduleOptions) {
    this.config = options.config;
    this.bridgeOptions = { blueprintDir: options.blueprintDir };
    this.onUpdate = options.onUpdate;
    this.onError = options.onError;
  }

  public start(): void {
    if (this.running) {
      return;
    }
    this.running = true;

    this.scheduleMorning();
    this.scheduleEvening();
  }

  public stop(): void {
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

  private scheduleMorning(): void {
    if (!this.running) return;

    const delay = this.calculateDelay(this.config.morning_time);
    this.morningTimer = setTimeout(() => {
      void this.getMorningBrief();
      this.scheduleMorning();
    }, delay);
  }

  private scheduleEvening(): void {
    if (!this.running) return;

    const delay = this.calculateDelay(this.config.evening_time);
    this.eveningTimer = setTimeout(() => {
      void this.getEveningWrap();
      this.scheduleEvening();
    }, delay);
  }

  private calculateDelay(target: { hour: number; minute: number }): number {
    const now = new Date();
    const targetTime = new Date(
      now.getFullYear(),
      now.getMonth(),
      now.getDate(),
      target.hour,
      target.minute,
      0,
      0,
    );

    if (targetTime.getTime() <= now.getTime()) {
      targetTime.setDate(targetTime.getDate() + 1);
    }

    return targetTime.getTime() - now.getTime();
  }

  public async getMorningBrief(): Promise<DigestBrief | null> {
    const response = await callPythonBridgeSafe<{ [key: string]: unknown }>(
      "morning_brief",
      { squad_id: this.config.squad_id },
      this.bridgeOptions,
    );

    if (!response.success || !response.data) {
      const error = new Error(response.error ?? "Morning brief failed");
      this.onError?.(error);
      return null;
    }

    const data = response.data;
    const brief: DigestBrief = {
      type: "morning",
      overnight_actions: typeof data.overnight_actions === "number" ? data.overnight_actions : 0,
      queue_summary: data.queue_summary as DigestBrief["queue_summary"],
      pending_actions: data.pending_actions as DigestBrief["pending_actions"],
      generated_at: new Date().toISOString(),
    };

    const now = new Date();
    if (now.getDay() === 0 && Array.isArray(data.evolution_updates)) {
      brief.evolution_updates = data.evolution_updates as DigestBrief["evolution_updates"];
    }

    this.onUpdate?.(brief);
    return brief;
  }

  public async getEveningWrap(): Promise<DigestBrief | null> {
    const response = await callPythonBridgeSafe<{ [key: string]: unknown }>(
      "evening_wrap",
      { squad_id: this.config.squad_id },
      this.bridgeOptions,
    );

    if (!response.success || !response.data) {
      const error = new Error(response.error ?? "Evening wrap failed");
      this.onError?.(error);
      return null;
    }

    const data = response.data;
    const brief: DigestBrief = {
      type: "evening",
      today_completed: typeof data.today_completed === "number" ? data.today_completed : 0,
      auto_executed: typeof data.auto_executed === "number" ? data.auto_executed : 0,
      remaining_pending: typeof data.remaining_pending === "number" ? data.remaining_pending : 0,
      generated_at: new Date().toISOString(),
    };

    this.onUpdate?.(brief);
    return brief;
  }

  public renderBrief(brief: DigestBrief): string[] {
    const lines: string[] = [];

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
          const emoji = priorityEmoji[action.priority as keyof typeof priorityEmoji] ?? "⚪";
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
    } else {
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

  public getNextMorningTime(): Date | null {
    if (!this.running || !this.morningTimer) return null;
    const delay = this.calculateDelay(this.config.morning_time);
    return new Date(Date.now() + delay);
  }

  public getNextEveningTime(): Date | null {
    if (!this.running || !this.eveningTimer) return null;
    const delay = this.calculateDelay(this.config.evening_time);
    return new Date(Date.now() + delay);
  }

  public isRunning(): boolean {
    return this.running;
  }
}
