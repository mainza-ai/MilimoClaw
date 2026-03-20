"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.EvolutionManager = void 0;
const fs_1 = require("fs");
const path_1 = require("path");
const os_1 = require("os");
const python_bridge_js_1 = require("../lib/python-bridge.js");
class EvolutionManager {
    squadId;
    toolsDir;
    blueprintDir;
    constructor(squadId, blueprintDir) {
        this.squadId = squadId;
        const home = process.env.HOME || process.env.USERPROFILE || (0, os_1.homedir)() || '/tmp';
        this.toolsDir = (0, path_1.join)(home, '.milimo', 'tools', squadId);
        this.blueprintDir = blueprintDir || process.env.MILIMO_BLUEPRINT_DIR || '/opt/milimo-blueprint';
    }
    showEvolutionLog() {
        console.log('\n--- SQUAD EVOLUTION LOG ---');
        try {
            const roles = (0, fs_1.readdirSync)(this.toolsDir);
            for (const role of roles) {
                if (role.startsWith('.'))
                    continue;
                const regPath = (0, path_1.join)(this.toolsDir, role, 'registry.json');
                try {
                    const content = (0, fs_1.readFileSync)(regPath, 'utf8');
                    const registry = JSON.parse(content);
                    const tools = registry.tools || {};
                    console.log(`\n[${role.toUpperCase()} CLAW]`);
                    if (Object.keys(tools).length === 0) {
                        console.log(' No evolved tools yet.');
                        continue;
                    }
                    for (const [name, tool] of Object.entries(tools)) {
                        const statusMark = tool.status === 'deployed' ? '🟢' : '🔴';
                        const trigger = tool.proposal?.trigger_pattern?.trigger_description || 'Unknown trigger';
                        console.log(` ${statusMark} ${name} v${tool.version || '1.0.0'} | ${statusMark === '🟢' ? 'ACTIVE' : 'DISABLED'}`);
                        console.log(` Trigger: ${trigger}`);
                        console.log(` Impact: +${tool.performance_delta?.toFixed(1) || '?'}% uplift`);
                    }
                }
                catch {
                    // ignore missing registry or unreadable file for this role
                }
            }
        }
        catch {
            console.log('No evolution data found. Claws are still gathering observations.');
        }
        console.log('\n---------------------------\n');
    }
    toggleTool(role, toolName, enable) {
        if (!role || !toolName) {
            console.log('Usage: enable-tool/disable-tool <role> <tool_name>');
            return;
        }
        const regPath = (0, path_1.join)(this.toolsDir, role, 'registry.json');
        try {
            const content = (0, fs_1.readFileSync)(regPath, 'utf8');
            const registry = JSON.parse(content);
            if (!registry.tools || !registry.tools[toolName]) {
                console.log(`Tool '${toolName}' not found for role '${role}'.`);
                return;
            }
            registry.tools[toolName].status = enable ? 'deployed' : 'disabled';
            (0, fs_1.writeFileSync)(regPath, JSON.stringify(registry, null, 2));
            console.log(`Tool '${toolName}' has been ${enable ? 'ENABLED' : 'DISABLED'}.`);
        }
        catch (e) {
            console.log(`Failed to toggle tool: ${e}`);
        }
    }
    showCrossClawFlows() {
        console.log('\n--- CROSS-CLAW EVOLUTION FLOWS ---');
        console.log('Visualizing signal routing between claws based on mesh configurations.');
        console.log('');
        const flowState = this.getMeshFlowState();
        if (!flowState || flowState.signals.length === 0) {
            console.log(' Signal data unavailable.');
            console.log('');
            console.log(' [Analytics Claw] ===(Retention Signals)===> [Content Claw]');
            console.log(' [Finance Claw] ===(Risk Annotations)===> [Ops Claw]');
            console.log(' [Ops Claw] ===(Engagement Flags)===> [Content Claw]');
            console.log('');
            console.log(' (Showing default flow diagram - connect to mesh for live data)');
        }
        else {
            console.log(` Signal count this week: ${flowState.signal_count_this_week}`);
            console.log('');
            for (const signal of flowState.signals) {
                const lastTx = signal.last_transmission ? ` (${signal.last_transmission})` : '';
                console.log(` [${signal.source_claw.toUpperCase()} Claw] ===(${signal.signal_type})===> [${signal.destination_claw.toUpperCase()} Claw]${lastTx}`);
            }
            if (flowState.last_transmission) {
                console.log('');
                console.log(` Last mesh transmission: ${flowState.last_transmission}`);
            }
        }
        console.log('');
        console.log('Signals are ingested during the OBSERVE stage to trigger new tool proposals.');
        console.log('----------------------------------\n');
    }
    getMeshFlowState() {
        try {
            const response = (0, python_bridge_js_1.callPythonBridgeSafe)('mesh_flow_state', { squad: this.squadId }, { blueprintDir: this.blueprintDir });
            if (response.success && response.data) {
                return response.data;
            }
            return null;
        }
        catch {
            return null;
        }
    }
    getMeshFlowData() {
        return this.getMeshFlowState();
    }
}
exports.EvolutionManager = EvolutionManager;
//# sourceMappingURL=evolution.js.map