// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `milimo assistant` — Squad assistant management commands.
 *
 * setup   — Renders and installs the assistant system prompt
 * verify  — Checks assistant is correctly configured
 * start   — Starts the assistant in NemoClaw terminal
 */

import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

interface AssistantConfig {
  name: string;
  emoji: string;
}

export function getAssistantConfig(): AssistantConfig | null {
    const configPath = join(homedir(), ".milimo", "config.json");
    try {
        const config = JSON.parse(readFileSync(configPath, "utf-8"));
        const assistant = config?.assistant;
        if (assistant?.name) {
            return { name: assistant.name, emoji: assistant.emoji || "🦀" };
        }
        return null;
    } catch {
        return null;
    }
}

export async function assistantSetup(): Promise<void> {
    console.log("Setting up squad assistant...\n");

    const result = spawn("python3", ["milimo-blueprint/orchestrator/assistant_setup.py"], {
        stdio: "inherit",
    });

    return new Promise((resolve, reject) => {
        result.on("close", (code) => {
            if (code === 0) resolve();
            else reject(new Error(`Assistant setup failed with exit code ${code}`));
        });
    });
}

export async function assistantVerify(): Promise<void> {
    const result = spawn("python3", ["milimo-blueprint/orchestrator/assistant_setup.py", "--verify"], {
        stdio: "inherit",
    });

    return new Promise((resolve, reject) => {
        result.on("close", (code) => {
            const assistant = getAssistantConfig();
            if (code === 0) {
                const name = assistant?.name ?? "your assistant";
                console.log(`\n${name} setup is complete.`);
                console.log("Start with: openclaw milimo assistant start");
                resolve();
            } else {
                console.error("\nAssistant setup incomplete. Run: openclaw milimo assistant setup");
                reject(new Error("Assistant setup verification failed"));
            }
        });
    });
}

export async function assistantStart(): Promise<void> {
    const agentConfig = ".openclaw/agents/main/config.yaml";
    if (!existsSync(agentConfig)) {
        console.error("Assistant not set up. Run: openclaw milimo assistant setup");
        process.exit(1);
    }

    const assistant = getAssistantConfig();
    const name = assistant?.name ?? "your assistant";
    const emoji = assistant?.emoji ?? "🦀";

    console.log(`Starting ${name}... ${emoji}\n`);

    // Launch the interactive TUI instead of a single, required-message turn
    const result = spawn("openclaw", ["tui", "--session", "main"], { stdio: "inherit" });

    return new Promise((resolve, reject) => {
        result.on("close", (code) => {
            if (code === 0) resolve();
            else reject(new Error(`${name} exited with code ${code}`));
        });
    });
}
