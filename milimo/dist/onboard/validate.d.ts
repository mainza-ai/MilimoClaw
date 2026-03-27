export interface TemplateValidationResult {
    valid: boolean;
    errors: string[];
    config?: Record<string, unknown>;
}
export interface TemplateInfo {
    name: string;
    displayName: string;
    category: string;
    description: string;
    squadSize: number;
    clawsActive: string[];
}
export declare function validateTemplateFile(templatePath: string): TemplateValidationResult;
export declare function getTemplateInfo(templatePath: string): TemplateInfo | null;
export declare function validateSquadName(name: string): {
    valid: boolean;
    error?: string;
};
export declare function validateOperatorName(name: string): {
    valid: boolean;
    error?: string;
};
export declare function generateMeshSecret(): string;
//# sourceMappingURL=validate.d.ts.map