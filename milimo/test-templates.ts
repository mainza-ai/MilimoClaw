import { cliInit } from './src/commands/init.js';
import { cliBlueprintList } from './src/commands/blueprint.js';
import * as path from 'path';

const pluginConfig = {
  blueprintDir: path.resolve(__dirname, '../milimo-blueprint'),
  squadName: 'test-squad',
  clawRole: 'content',
  debugMode: true,
  pluginDir: path.resolve(__dirname, '..'),
  meshSecret: 'test-secret'
};

const logger = {
  info: console.log,
  warn: console.warn,
  error: console.error,
  debug: console.debug,
  success: console.log,
};

async function run() {
  console.log('--- BLUEPRINT LIST TEST ---');
  await cliBlueprintList({ json: false, logger, pluginConfig: pluginConfig as any });

  console.log('\n--- INIT TEMPLATE TEST ---');
  try {
    const fs = await import('fs');
    if (fs.existsSync('/tmp/.milimo/state.json')) {
      fs.unlinkSync('/tmp/.milimo/state.json');
    }
  } catch(err) {}

  process.env.HOME = '/tmp'; // isolate state
  await cliInit({ squad: 'my-agency', role: 'content', template: 'content-agency', solo: false, logger, pluginConfig: pluginConfig as any });
}

run().catch(console.error);
