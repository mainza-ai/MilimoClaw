import type { BridgeCommandOptions, PythonBridgeOptions } from "./python-bridge";
export declare class RpcBridgeClient {
    private baseUrl;
    constructor(port?: number);
    call<T = unknown>(method: string, params?: object): Promise<T>;
    ping(): Promise<boolean>;
    bridge<T = unknown>(command: string, args: Record<string, unknown>, _options?: BridgeCommandOptions): Promise<T>;
    bridgeSafe<T = unknown>(command: string, args: Record<string, unknown>, options?: BridgeCommandOptions): Promise<{
        success: boolean;
        data?: T;
        error?: string;
    }>;
    pythonEval<T = unknown>(code: string, _options?: PythonBridgeOptions): Promise<T>;
    pythonEvalSafe(code: string, options?: PythonBridgeOptions): Promise<{
        success: boolean;
        stdout?: string;
        error?: string;
    }>;
    pythonModule<T = unknown>(moduleName: string, args: string[], _options?: PythonBridgeOptions): Promise<T>;
    pythonFile<T = unknown>(scriptPath: string, args: string[], _options?: PythonBridgeOptions): Promise<T>;
}
export declare function getRpcClient(): RpcBridgeClient;
//# sourceMappingURL=rpc-bridge.d.ts.map