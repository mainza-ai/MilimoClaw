"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.callPythonBridge = callPythonBridge;
exports.callPythonBridgeSafe = callPythonBridgeSafe;
exports.callPython = callPython;
exports.callPythonSafe = callPythonSafe;
exports.callPythonModule = callPythonModule;
exports.callPythonFile = callPythonFile;
exports.callPythonWithInput = callPythonWithInput;
/**
 * Python Bridge Helper
 *
 * Provides safe execution of Python commands using spawnSync with array arguments
 * to prevent shell injection vulnerabilities.
 *
 * Includes bridge_cli.py interface for structured JSON communication.
 */
const node_child_process_1 = require("node:child_process");
const node_path_1 = require("node:path");
const BRIDGE_CLI_PATH = "orchestrator/bridge_cli.py";
function callPythonBridge(command, args, options) {
    const rawPath = (0, node_path_1.join)(options.blueprintDir, BRIDGE_CLI_PATH);
    const bridgePath = options.resolvePath ? options.resolvePath(rawPath) : rawPath;
    const argsJson = JSON.stringify(args);
    const result = (0, node_child_process_1.spawnSync)("python3", [bridgePath, "--command", command, "--args", argsJson], {
        cwd: options.blueprintDir,
        encoding: "utf-8",
        timeout: options.timeout ?? 30000,
        env: { ...process.env, PYTHONPATH: options.blueprintDir },
    });
    if (result.error) {
        throw result.error;
    }
    if (result.status !== 0) {
        throw new Error(`Bridge CLI failed with status ${result.status}: ${result.stderr}`);
    }
    const response = JSON.parse(result.stdout);
    if (!response.success) {
        throw new Error(response.error ?? "Unknown bridge error");
    }
    return response.data;
}
function callPythonBridgeSafe(command, args, options) {
    try {
        const data = callPythonBridge(command, args, options);
        return { success: true, data };
    }
    catch (error) {
        return { success: false, error: error.message };
    }
}
/**
 * @deprecated Use `callPythonBridge()` instead. This function accepts raw code
 * strings which is an injection surface. All new callers should use the
 * structured `--command` / `--args` interface via `callPythonBridge()`.
 */
function callPython(blueprintDir, code, options) {
    const safeCode = `import sys; sys.path.insert(0, ${JSON.stringify(blueprintDir)}); ${code}`;
    const result = (0, node_child_process_1.spawnSync)("python3", ["-c", safeCode], {
        cwd: options?.cwd ?? blueprintDir,
        encoding: "utf-8",
        timeout: options?.timeout ?? 30000,
        env: options?.env ?? process.env,
    });
    if (result.error) {
        throw result.error;
    }
    if (result.status !== 0) {
        throw new Error(`Python command failed with status ${result.status}: ${result.stderr}`);
    }
    return result.stdout.trim();
}
function callPythonSafe(code, options) {
    const result = (0, node_child_process_1.spawnSync)("python3", ["-c", code], {
        cwd: options?.cwd,
        encoding: "utf-8",
        timeout: options?.timeout ?? 30000,
        env: options?.env ?? process.env,
    });
    return {
        success: result.status === 0 && !result.error,
        stdout: result.stdout ?? "",
        stderr: result.stderr ?? "",
        status: result.status,
        error: result.error ?? undefined,
    };
}
function callPythonModule(moduleName, args, options) {
    const allArgs = ["-m", moduleName, ...args];
    const result = (0, node_child_process_1.spawnSync)("python3", allArgs, {
        cwd: options?.cwd,
        encoding: "utf-8",
        timeout: options?.timeout ?? 60000,
        env: options?.env ?? process.env,
    });
    return {
        success: result.status === 0 && !result.error,
        stdout: result.stdout ?? "",
        stderr: result.stderr ?? "",
        status: result.status,
        error: result.error ?? undefined,
    };
}
function callPythonFile(scriptPath, args, options) {
    const result = (0, node_child_process_1.spawnSync)("python3", [scriptPath, ...args], {
        cwd: options?.cwd,
        encoding: "utf-8",
        timeout: options?.timeout ?? 60000,
        env: options?.env ?? process.env,
    });
    return {
        success: result.status === 0 && !result.error,
        stdout: result.stdout ?? "",
        stderr: result.stderr ?? "",
        status: result.status,
        error: result.error ?? undefined,
    };
}
function callPythonWithInput(code, input, options) {
    const result = (0, node_child_process_1.spawnSync)("python3", ["-c", code], {
        cwd: options?.cwd,
        encoding: "utf-8",
        timeout: options?.timeout ?? 30000,
        env: options?.env ?? process.env,
        input: input,
    });
    return {
        success: result.status === 0 && !result.error,
        stdout: result.stdout ?? "",
        stderr: result.stderr ?? "",
        status: result.status,
        error: result.error ?? undefined,
    };
}
//# sourceMappingURL=python-bridge.js.map