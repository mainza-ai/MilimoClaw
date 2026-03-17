import { readdirSync, readFileSync, writeFileSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

export class EvolutionManager {
  private toolsDir: string;
  
  constructor(private squadId: string) {
    const home = process.env.HOME || process.env.USERPROFILE || homedir() || '/tmp';
    this.toolsDir = join(home, '.milimo', 'tools', squadId);
  }

  public showEvolutionLog() {
    console.log('\n--- SQUAD EVOLUTION LOG ---');
    try {
      const roles = readdirSync(this.toolsDir);
      for (const role of roles) {
        // Skip hidden files or non-directories if any, though usually clean
        if (role.startsWith('.')) continue;

        const regPath = join(this.toolsDir, role, 'registry.json');
        try {
          const content = readFileSync(regPath, 'utf8');
          const registry = JSON.parse(content);
          const tools = registry.tools || {};
          
          console.log(`\n[${role.toUpperCase()} CLAW]`);
          if (Object.keys(tools).length === 0) {
            console.log('  No evolved tools yet.');
            continue;
          }
          
          for (const [name, tool] of Object.entries<any>(tools)) {
            const statusMark = tool.status === 'deployed' ? '🟢' : '🔴';
            const trigger = tool.proposal?.trigger_pattern?.trigger_description || 'Unknown trigger';
            console.log(`  ${statusMark} ${name} v${tool.version || '1.0.0'} | ${statusMark === '🟢' ? 'ACTIVE' : 'DISABLED'}`);
            console.log(`     Trigger: ${trigger}`);
            console.log(`     Impact:  +${tool.performance_delta?.toFixed(1) || '?'}% uplift`);
          }
        } catch (e) {
          // ignore missing registry or unreadable file for this role
        }
      }
    } catch (e) {
      console.log('No evolution data found. Claws are still gathering observations.');
    }
    console.log('\n---------------------------\n');
  }

  public toggleTool(role: string, toolName: string, enable: boolean) {
    if (!role || !toolName) {
      console.log('Usage: enable-tool/disable-tool <role> <tool_name>');
      return;
    }

    const regPath = join(this.toolsDir, role, 'registry.json');
    try {
      const content = readFileSync(regPath, 'utf8');
      const registry = JSON.parse(content);
      
      if (!registry.tools || !registry.tools[toolName]) {
        console.log(`Tool '${toolName}' not found for role '${role}'.`);
        return;
      }
      
      registry.tools[toolName].status = enable ? 'deployed' : 'disabled';
      writeFileSync(regPath, JSON.stringify(registry, null, 2));
      console.log(`Tool '${toolName}' has been ${enable ? 'ENABLED' : 'DISABLED'}.`);
    } catch (e) {
      console.log(`Failed to toggle tool: ${e}`);
    }
  }

  public showCrossClawFlows() {
    console.log('\n--- CROSS-CLAW EVOLUTION FLOWS ---');
    console.log('Visualizing signal routing between claws based on mesh configurations.');
    console.log('');
    console.log('  [Analytics Claw] ===(Retention Signals)===> [Content Claw]');
    console.log('  [Finance Claw]   ===(Risk Annotations)===>  [Ops Claw]');
    console.log('  [Ops Claw]       ===(Engagement Flags)===>  [Content Claw]');
    console.log('');
    console.log('Signals are ingested during the OBSERVE stage to trigger new tool proposals.');
    console.log('----------------------------------\n');
  }
}
