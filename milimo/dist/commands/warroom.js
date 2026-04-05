"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliWarRoom = cliWarRoom;
const warroom_tui_js_1 = require("../warroom/warroom-tui.js");
const approval_js_1 = require("../warroom/approval.js");
const config_js_1 = require("../onboard/config.js");
async function cliWarRoom(opts) {
    const onboardConfig = (0, config_js_1.loadOnboardConfig)();
    const squadName = onboardConfig?.squadName ?? opts.pluginConfig.squadName;
    if (!squadName) {
        opts.logger.error('Error: "squadName" not configured. Please run `openclaw milimo onboard` first.');
        process.exit(1);
    }
    // Non-interactive list mode for scripting/Lucy
    if (opts.list) {
        listWarRoomMessages(squadName, opts.operator, onboardConfig?.warRoomMode === "full" ? "pro" : "free");
        return;
    }
    (0, warroom_tui_js_1.startWarRoom)(squadName, opts.operator, onboardConfig?.warRoomMode === "full" ? "pro" : "free");
}
function listWarRoomMessages(squadId, operatorId, tier) {
    const engine = new approval_js_1.ApprovalEngine(squadId, tier);
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
            console.log(`    Payload: ${JSON.stringify(msg.payload, null, 4).split("\n").map(l => "      " + l).join("\n")}`);
        }
        console.log("");
    }
}
//# sourceMappingURL=warroom.js.map
