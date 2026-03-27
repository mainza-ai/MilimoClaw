import { startWarRoom } from "../warroom/warroom-tui.js";
import type { MilimoConfig, PluginLogger } from "../index.js";
import { loadOnboardConfig } from "../onboard/config.js";

export async function cliWarRoom(opts: { operator: string; logger: PluginLogger; pluginConfig: MilimoConfig }) {
	const onboardConfig = loadOnboardConfig();
	const squadName = onboardConfig?.squadName ?? opts.pluginConfig.squadName;

	if (!squadName) {
		opts.logger.error('Error: "squadName" not configured. Please run `openclaw milimo onboard` first.');
		process.exit(1);
	}

	startWarRoom(squadName, opts.operator, onboardConfig?.warRoomMode === "full" ? "pro" : "free");
}
