"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.RpcBridgeClient = void 0;
exports.getRpcClient = getRpcClient;
const RPC_PORT = 19999;
const RPC_BASE_URL = `http://127.0.0.1:${RPC_PORT}/rpc`;
let _clientInstance = null;
class RpcBridgeClient {
    baseUrl;
    constructor(port = RPC_PORT) {
        this.baseUrl = `http://127.0.0.1:${port}/rpc`;
    }
    async call(method, params = {}) {
        const body = JSON.stringify({
            jsonrpc: "2.0",
            method,
            params,
            id: Date.now(),
        });
        const res = await fetch(this.baseUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body,
            signal: AbortSignal.timeout(120_000),
        });
        if (!res.ok) {
            throw new Error(`RPC server error: ${res.status} ${res.statusText}`);
        }
        const json = (await res.json());
        if (json.error) {
            throw new Error(`RPC error: ${json.error.message}`);
        }
        return json.result;
    }
    async ping() {
        try {
            await this.call("ping", {});
            return true;
        }
        catch {
            return false;
        }
    }
    async bridge(command, args, _options) {
        return this.call("bridge", { command, args });
    }
    async bridgeSafe(command, args, options) {
        try {
            const data = await this.bridge(command, args, options);
            return { success: true, data };
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    }
    async pythonEval(code, _options) {
        return this.call("python_eval", { code });
    }
    async pythonEvalSafe(code, options) {
        try {
            const result = await this.pythonEval(code, options);
            return { success: true, stdout: result.stdout };
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    }
    async pythonModule(moduleName, args, _options) {
        return this.call("python_module", { moduleName, args });
    }
    async pythonFile(scriptPath, args, _options) {
        return this.call("python_file", { scriptPath, args });
    }
}
exports.RpcBridgeClient = RpcBridgeClient;
function getRpcClient() {
    if (!_clientInstance) {
        _clientInstance = new RpcBridgeClient();
    }
    return _clientInstance;
}
//# sourceMappingURL=rpc-bridge.js.map