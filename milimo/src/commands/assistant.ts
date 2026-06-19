// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * `milimo assistant` — Squad assistant management commands.
 *
 * setup   — Renders and installs the assistant system prompt
 * verify  — Checks assistant is correctly configured
 * start   — Starts the assistant in NemoClaw terminal
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { homedir } from "node:os";
import { getRpcClient } from "../lib/rpc-bridge";

interface AssistantConfig {
  name: string;
  emoji: string;
}

function resolveAssistantScript(): string {
  const home = homedir();
  const candidates = [
    join(home, ".openclaw/milimo", "blueprints", "0.1.0", "orchestrator", "assistant_setup.py"),
    join(home, ".openclaw/milimo", "milimo-blueprint", "orchestrator", "assistant_setup.py"),
    join(process.cwd(), "milimo-blueprint", "orchestrator", "assistant_setup.py"),
    "/opt/milimo-blueprint/orchestrator/assistant_setup.py",
  ];
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  return candidates[0];
}

export function getAssistantConfig(): AssistantConfig | null {
  const configPath = join(homedir(), ".openclaw/milimo", "config.json");
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

  const scriptPath = resolveAssistantScript();
  const blueprintDir = dirname(dirname(scriptPath));
  const rpc = getRpcClient();
  await rpc.call("assistant_setup", { blueprintDir });
}

export async function assistantVerify(): Promise<void> {
  const scriptPath = resolveAssistantScript();
  const blueprintDir = dirname(dirname(scriptPath));
  const rpc = getRpcClient();
  try {
    await rpc.call("assistant_verify", { scriptPath, blueprintDir });
    const assistant = getAssistantConfig();
    const name = assistant?.name ?? "your assistant";
    console.log(`\n${name} setup is complete.`);
    console.log("Start with: openclaw milimo assistant start");
  } catch {
    console.error("\nAssistant setup incomplete. Run: openclaw milimo assistant setup");
    throw new Error("Assistant setup verification failed");
  }
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

  console.log(`${emoji} Starting ${name}...\n`);
  console.log("Run the following command to start the interactive TUI:\n");
  console.log("  openclaw tui --session main\n");
}
