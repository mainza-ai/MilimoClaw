"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cliWarRoom = cliWarRoom;
const warroom_tui_js_1 = require("../warroom/warroom-tui.js");
const config_js_1 = require("../onboard/config.js");
async function cliWarRoom(opts) {
    const onboardConfig = (0, config_js_1.loadOnboardConfig)();
    const squadName = onboardConfig?.squadName ?? opts.pluginConfig.squadName;
    if (!squadName) {
        opts.logger.error('Error: "squadName" not configured. Please run `openclaw milimo onboard` first.');
        process.exit(1);
    }
    (0, warroom_tui_js_1.startWarRoom)(squadName, opts.operator, onboardConfig?.warRoomMode === "full" ? "pro" : "free");
}
//# sourceMappingURL=warroom.js.map