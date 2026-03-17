import { WarRoomTUI } from '../warroom/warroom.js';
import { MilimoConfig, PluginLogger } from '../index.js'; 

export async function cliWarRoom(opts: { operator: string, logger: PluginLogger, pluginConfig: MilimoConfig }) {
    if (!opts.pluginConfig.squadName) {
      opts.logger.error('Error: "squadName" not configured in openclaw.plugin.json. Please run `milimo init` first.');
      process.exit(1);
    }
    
    const tui = new WarRoomTUI(opts.pluginConfig.squadName, opts.operator);
    tui.start();
}
