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
}
export declare function callPythonBridge<T = unknown>(command: string, args: Record<string, unknown>, options: BridgeCommandOptions): T;
export declare function callPythonBridgeSafe<T = unknown>(command: string, args: Record<string, unknown>, options: BridgeCommandOptions): BridgeResponse<T>;
export declare function callPython(blueprintDir: string, code: string, options?: PythonBridgeOptions): string;
export declare function callPythonSafe(code: string, options?: PythonBridgeOptions): PythonBridgeResult;
export declare function callPythonModule(moduleName: string, args: string[], options?: PythonBridgeOptions): PythonBridgeResult;
export declare function callPythonFile(scriptPath: string, args: string[], options?: PythonBridgeOptions): PythonBridgeResult;
export declare function callPythonWithInput(code: string, input: string, options?: PythonBridgeOptions): PythonBridgeResult;
//# sourceMappingURL=python-bridge.d.ts.map