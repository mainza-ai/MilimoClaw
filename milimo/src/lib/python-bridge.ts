// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Python Bridge Helper
 *
 * Provides safe execution of Python commands using spawnSync with array arguments
 * to prevent shell injection vulnerabilities.
 *
 * Includes bridge_cli.py interface for structured JSON communication.
 */

import { spawnSync } from "node:child_process";
import { join } from "node:path";

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
  /**
   * Optional path resolver for SSRF-safe path resolution.
   * When provided, all constructed paths are resolved through this
   * function before use. Pass `api.resolvePath` from the OpenClaw
   * plugin API to prevent symlink-based path traversal attacks.
   */
  resolvePath?: (input: string) => string;
}

const BRIDGE_CLI_PATH = "orchestrator/bridge_cli.py";

export function callPythonBridge<T = unknown>(
  command: string,
  args: Record<string, unknown>,
  options: BridgeCommandOptions,
): T {
  const rawPath = join(options.blueprintDir, BRIDGE_CLI_PATH);
  const bridgePath = options.resolvePath ? options.resolvePath(rawPath) : rawPath;
  const argsJson = JSON.stringify(args);

  const result = spawnSync("python3", [bridgePath, "--command", command, "--args", argsJson], {
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

  const response: BridgeResponse<T> = JSON.parse(result.stdout);

  if (!response.success) {
    throw new Error(response.error ?? "Unknown bridge error");
  }

  return response.data as T;
}

export function callPythonBridgeSafe<T = unknown>(
  command: string,
  args: Record<string, unknown>,
  options: BridgeCommandOptions,
): BridgeResponse<T> {
  try {
    const data = callPythonBridge<T>(command, args, options);
    return { success: true, data };
  } catch (error) {
    return { success: false, error: (error as Error).message };
  }
}

/**
 * @deprecated Use `callPythonBridge()` instead. This function accepts raw code
 * strings which is an injection surface. All new callers should use the
 * structured `--command` / `--args` interface via `callPythonBridge()`.
 */
export function callPython(
  blueprintDir: string,
  code: string,
  options?: PythonBridgeOptions,
): string {
  const safeCode = `import sys; sys.path.insert(0, ${JSON.stringify(blueprintDir)}); ${code}`;
  const result = spawnSync("python3", ["-c", safeCode], {
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

export function callPythonSafe(code: string, options?: PythonBridgeOptions): PythonBridgeResult {
  const result = spawnSync("python3", ["-c", code], {
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

export function callPythonModule(
  moduleName: string,
  args: string[],
  options?: PythonBridgeOptions,
): PythonBridgeResult {
  const allArgs = ["-m", moduleName, ...args];

  const result = spawnSync("python3", allArgs, {
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

export function callPythonFile(
  scriptPath: string,
  args: string[],
  options?: PythonBridgeOptions,
): PythonBridgeResult {
  const result = spawnSync("python3", [scriptPath, ...args], {
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

export function callPythonWithInput(
  code: string,
  input: string,
  options?: PythonBridgeOptions,
): PythonBridgeResult {
  const result = spawnSync("python3", ["-c", code], {
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
