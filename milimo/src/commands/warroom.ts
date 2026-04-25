// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { startWarRoom } from "../warroom/warroom-tui.js";
import { ApprovalEngine } from "../warroom/approval.js";
import type { MilimoConfig, PluginLogger } from "../index.js";
import { loadOnboardConfig } from "../onboard/config.js";

export function cliWarRoom(opts: {
  operator: string;
  logger: PluginLogger;
  pluginConfig: MilimoConfig;
  list?: boolean;
}): void {
  const onboardConfig = loadOnboardConfig();
  const squadName = onboardConfig?.squadName ?? opts.pluginConfig.squadName;

  if (!squadName) {
    opts.logger.error(
      'Error: "squadName" not configured. Please run `openclaw milimo onboard` first.',
    );
    process.exit(1);
  }

  // Non-interactive list mode for scripting/Lucy
  if (opts.list) {
    listWarRoomMessages(
      squadName,
      opts.operator,
      onboardConfig?.warRoomMode === "full" ? "pro" : "free",
    );
    return;
  }

  startWarRoom(squadName, opts.operator, onboardConfig?.warRoomMode === "full" ? "pro" : "free");
}

function listWarRoomMessages(squadId: string, operatorId: string, tier: "free" | "pro") {
  const engine = new ApprovalEngine(squadId, tier);
  const messages = engine.getPendingMessages();

  if (messages.length === 0) {
    console.log("War Room inbox is empty.");
    return;
  }

  console.log(`\nWar Room — ${messages.length} pending message(s):\n`);
  for (const msg of messages) {
    const evalResult = engine.evaluateAction(msg);
    console.log(`  [${evalResult.mode}] ${msg.sender_role} → ${msg.recipient_role}`);
    console.log(`    Type: ${msg.message_type}`);
    console.log(`    Time: ${msg.timestamp}`);
    console.log(`    ID:   ${msg.message_id}`);
    if (msg.payload && Object.keys(msg.payload).length > 0) {
      console.log(
        `    Payload: ${JSON.stringify(msg.payload, null, 4)
          .split("\n")
          .map((l) => "      " + l)
          .join("\n")}`,
      );
    }
    console.log("");
  }
}
