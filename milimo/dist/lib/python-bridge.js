"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.callPythonBridge = callPythonBridge;
exports.callPythonBridgeSafe = callPythonBridgeSafe;
exports.callPython = callPython;
exports.callPythonSafe = callPythonSafe;
exports.callPythonModule = callPythonModule;
exports.callPythonFile = callPythonFile;
exports.callPythonWithInput = callPythonWithInput;
const rpc_bridge_1 = require("./rpc-bridge");
const BRIDGE_CLI_PATH = "orchestrator/bridge_cli.py";
function rpc() {
    return (0, rpc_bridge_1.getRpcClient)();
}
async function callPythonBridge(command, args, options) {
    return rpc().bridge(command, { ...args, blueprintDir: options.blueprintDir }, options);
}
async function callPythonBridgeSafe(command, args, options) {
    return rpc().bridgeSafe(command, args, options);
}
async function callPython(blueprintDir, code, _options) {
    const result = await rpc().pythonEval(code, {
        ..._options,
        cwd: blueprintDir,
    });
    return result.stdout;
}
async function callPythonSafe(code, options) {
    try {
        const result = await rpc().pythonEval(code, options);
        return {
            success: true,
            stdout: result.stdout,
            stderr: "",
            status: 0,
        };
    }
    catch (err) {
        return {
            success: false,
            stdout: "",
            stderr: err.message,
            status: 1,
            error: err,
        };
    }
}
async function callPythonModule(moduleName, args, options) {
    try {
        const result = await rpc().pythonModule(moduleName, args, options);
        return {
            success: true,
            stdout: result.stdout,
            stderr: result.stderr,
            status: 0,
        };
    }
    catch (err) {
        return {
            success: false,
            stdout: "",
            stderr: err.message,
            status: 1,
            error: err,
        };
    }
}
async function callPythonFile(scriptPath, args, options) {
    try {
        const result = await rpc().pythonFile(scriptPath, args, options);
        return {
            success: true,
            stdout: result.stdout,
            stderr: result.stderr,
            status: 0,
        };
    }
    catch (err) {
        return {
            success: false,
            stdout: "",
            stderr: err.message,
            status: 1,
            error: err,
        };
    }
}
async function callPythonWithInput(code, input, options) {
    try {
        const result = await rpc().pythonEval(`import sys; sys.stdin = __import__('io').StringIO(${JSON.stringify(input)}); ${code}`, options);
        return {
            success: true,
            stdout: result.stdout,
            stderr: "",
            status: 0,
        };
    }
    catch (err) {
        return {
            success: false,
            stdout: "",
            stderr: err.message,
            status: 1,
            error: err,
        };
    }
}
//# sourceMappingURL=python-bridge.js.map