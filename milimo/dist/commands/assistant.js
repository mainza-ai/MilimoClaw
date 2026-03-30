"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.getAssistantConfig = getAssistantConfig;
exports.assistantSetup = assistantSetup;
exports.assistantVerify = assistantVerify;
exports.assistantStart = assistantStart;
/**
 * `milimo assistant` — Squad assistant management commands.
 *
 * setup   — Renders and installs the assistant system prompt
 * verify  — Checks assistant is correctly configured
 * start   — Starts the assistant in NemoClaw terminal
 */
const node_child_process_1 = require("node:child_process");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const node_os_1 = require("node:os");
function getAssistantConfig() {
    const configPath = (0, node_path_1.join)((0, node_os_1.homedir)(), ".milimo", "config.json");
    try {
        const config = JSON.parse((0, node_fs_1.readFileSync)(configPath, "utf-8"));
        const assistant = config?.assistant;
        if (assistant?.name) {
            return { name: assistant.name, emoji: assistant.emoji || "🦀" };
        }
        return null;
    }
    catch {
        return null;
    }
}
async function assistantSetup() {
    console.log("Setting up squad assistant...\n");
    const result = (0, node_child_process_1.spawn)("python3", ["milimo-blueprint/orchestrator/assistant_setup.py"], {
        stdio: "inherit",
    });
    return new Promise((resolve, reject) => {
        result.on("close", (code) => {
            if (code === 0)
                resolve();
            else
                reject(new Error(`Assistant setup failed with exit code ${code}`));
        });
    });
}
async function assistantVerify() {
    const result = (0, node_child_process_1.spawn)("python3", ["milimo-blueprint/orchestrator/assistant_setup.py", "--verify"], {
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
            }
            else {
                console.error("\nAssistant setup incomplete. Run: openclaw milimo assistant setup");
                reject(new Error("Assistant setup verification failed"));
            }
        });
    });
}
async function assistantStart() {
    const agentConfig = ".openclaw/agents/main/config.yaml";
    if (!(0, node_fs_1.existsSync)(agentConfig)) {
        console.error("Assistant not set up. Run: openclaw milimo assistant setup");
        process.exit(1);
    }
    const assistant = getAssistantConfig();
    const name = assistant?.name ?? "your assistant";
    const emoji = assistant?.emoji ?? "🦀";
    console.log(`Starting ${name}... ${emoji}\n`);
    // Launch the interactive TUI instead of a single, required-message turn
    const result = (0, node_child_process_1.spawn)("openclaw", ["tui", "--session", "main"], { stdio: "inherit" });
    return new Promise((resolve, reject) => {
        result.on("close", (code) => {
            if (code === 0)
                resolve();
            else
                reject(new Error(`${name} exited with code ${code}`));
        });
    });
}
//# sourceMappingURL=assistant.js.map
