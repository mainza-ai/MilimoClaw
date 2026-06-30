interface AssistantConfig {
    name: string;
    emoji: string;
}
export declare function getAssistantConfig(): AssistantConfig | null;
export declare function assistantSetup(): Promise<void>;
export declare function assistantVerify(): Promise<void>;
export declare function assistantStart(): void;
export {};
//# sourceMappingURL=assistant.d.ts.map