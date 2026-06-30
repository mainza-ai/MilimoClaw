// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

import type { BridgeCommandOptions, PythonBridgeOptions } from "./python-bridge";

const RPC_PORT = 19999;
// const RPC_BASE_URL = `http://127.0.0.1:${RPC_PORT}/rpc`;

interface RpcError {
  message: string;
  code?: number;
}

interface RpcResponse<T> {
  result?: T;
  error?: RpcError;
  id: number;
}

let _clientInstance: RpcBridgeClient | null = null;

export class RpcBridgeClient {
  private baseUrl: string;

  constructor(port: number = RPC_PORT) {
    this.baseUrl = `http://127.0.0.1:${port}/rpc`;
  }

  async call<T = unknown>(method: string, params: object = {}): Promise<T> {
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

    const json = (await res.json()) as RpcResponse<T>;

    if (json.error) {
      throw new Error(`RPC error: ${json.error.message}`);
    }

    return json.result as T;
  }

  async ping(): Promise<boolean> {
    try {
      await this.call("ping", {});
      return true;
    } catch {
      return false;
    }
  }

  async bridge<T = unknown>(
    command: string,
    args: Record<string, unknown>,
    _options?: BridgeCommandOptions,
  ): Promise<T> {
    return this.call<T>("bridge", { command, args });
  }

  async bridgeSafe<T = unknown>(
    command: string,
    args: Record<string, unknown>,
    options?: BridgeCommandOptions,
  ): Promise<{ success: boolean; data?: T; error?: string }> {
    try {
      const data = await this.bridge<T>(command, args, options);
      return { success: true, data };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  async pythonEval<T = unknown>(code: string, _options?: PythonBridgeOptions): Promise<T> {
    return this.call<T>("python_eval", { code });
  }

  async pythonEvalSafe(
    code: string,
    options?: PythonBridgeOptions,
  ): Promise<{ success: boolean; stdout?: string; error?: string }> {
    try {
      const result = await this.pythonEval<{ stdout: string }>(code, options);
      return { success: true, stdout: result.stdout };
    } catch (err) {
      return { success: false, error: (err as Error).message };
    }
  }

  async pythonModule<T = unknown>(
    moduleName: string,
    args: string[],
    _options?: PythonBridgeOptions,
  ): Promise<T> {
    return this.call<T>("python_module", { moduleName, args });
  }

  async pythonFile<T = unknown>(
    scriptPath: string,
    args: string[],
    _options?: PythonBridgeOptions,
  ): Promise<T> {
    return this.call<T>("python_file", { scriptPath, args });
  }
}

export function getRpcClient(): RpcBridgeClient {
  if (!_clientInstance) {
    _clientInstance = new RpcBridgeClient();
  }
  return _clientInstance;
}
