// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import { getRpcClient, RpcBridgeClient } from "./rpc-bridge";

export interface PythonBridgeResult {
  success: boolean;
  stdout: string;
  stderr: string;
  status: number | null;
  error?: Error;
}

export interface PythonBridgeOptions {
  cwd?: string;
  timeout?: number;
  env?: NodeJS.ProcessEnv;
}

export interface BridgeResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface BridgeCommandOptions {
  blueprintDir: string;
  timeout?: number;
  resolvePath?: (input: string) => string;
}

// const BRIDGE_CLI_PATH = "orchestrator/bridge_cli.py";

function rpc(): RpcBridgeClient {
  return getRpcClient();
}

export async function callPythonBridge<T = unknown>(
  command: string,
  args: Record<string, unknown>,
  options: BridgeCommandOptions,
): Promise<T> {
  return rpc().bridge<T>(command, { ...args, blueprintDir: options.blueprintDir }, options);
}

export async function callPythonBridgeSafe<T = unknown>(
  command: string,
  args: Record<string, unknown>,
  options: BridgeCommandOptions,
): Promise<BridgeResponse<T>> {
  return rpc().bridgeSafe<T>(command, args, options);
}

export async function callPython(
  blueprintDir: string,
  code: string,
  _options?: PythonBridgeOptions,
): Promise<string> {
  const result = await rpc().pythonEval<{ stdout: string }>(code, {
    ..._options,
    cwd: blueprintDir,
  });
  return result.stdout;
}

export async function callPythonSafe(
  code: string,
  options?: PythonBridgeOptions,
): Promise<PythonBridgeResult> {
  try {
    const result = await rpc().pythonEval<{ stdout: string }>(code, options);
    return {
      success: true,
      stdout: result.stdout,
      stderr: "",
      status: 0,
    };
  } catch (err) {
    return {
      success: false,
      stdout: "",
      stderr: (err as Error).message,
      status: 1,
      error: err as Error,
    };
  }
}

export async function callPythonModule(
  moduleName: string,
  args: string[],
  options?: PythonBridgeOptions,
): Promise<PythonBridgeResult> {
  try {
    const result = await rpc().pythonModule<{ stdout: string; stderr: string }>(
      moduleName,
      args,
      options,
    );
    return {
      success: true,
      stdout: result.stdout,
      stderr: result.stderr,
      status: 0,
    };
  } catch (err) {
    return {
      success: false,
      stdout: "",
      stderr: (err as Error).message,
      status: 1,
      error: err as Error,
    };
  }
}

export async function callPythonFile(
  scriptPath: string,
  args: string[],
  options?: PythonBridgeOptions,
): Promise<PythonBridgeResult> {
  try {
    const result = await rpc().pythonFile<{ stdout: string; stderr: string }>(
      scriptPath,
      args,
      options,
    );
    return {
      success: true,
      stdout: result.stdout,
      stderr: result.stderr,
      status: 0,
    };
  } catch (err) {
    return {
      success: false,
      stdout: "",
      stderr: (err as Error).message,
      status: 1,
      error: err as Error,
    };
  }
}

export async function callPythonWithInput(
  code: string,
  input: string,
  options?: PythonBridgeOptions,
): Promise<PythonBridgeResult> {
  try {
    const result = await rpc().pythonEval<{ stdout: string }>(
      `import sys; sys.stdin = __import__('io').StringIO(${JSON.stringify(input)}); ${code}`,
      options,
    );
    return {
      success: true,
      stdout: result.stdout,
      stderr: "",
      status: 0,
    };
  } catch (err) {
    return {
      success: false,
      stdout: "",
      stderr: (err as Error).message,
      status: 1,
      error: err as Error,
    };
  }
}
