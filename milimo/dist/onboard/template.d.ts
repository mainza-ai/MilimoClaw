import type { ClawRole } from "../index.js";
export interface TemplateDiscovery {
    id: string;
    name: string;
    displayName: string;
    description: string;
    category: string;
    path: string;
    squadSize: number;
    clawsActive: ClawRole[];
    solo: boolean;
}
export interface RoleBlueprint {
    role: ClawRole;
    description: string;
    path: string;
}
export declare function getRoleDescription(role: ClawRole): string;
export declare function discoverTemplates(blueprintDir: string): TemplateDiscovery[];
export declare function loadTemplateMetadata(templatePath: string): TemplateDiscovery | null;
export declare function discoverRoleBlueprints(blueprintDir: string): RoleBlueprint[];
export declare function getTemplateCategories(templates: TemplateDiscovery[]): string[];
export declare function filterTemplatesByCategory(templates: TemplateDiscovery[], category: string): TemplateDiscovery[];
export declare function getBuiltInTemplates(): TemplateDiscovery[];
export declare function resolveTemplatePath(templateId: string, blueprintDir: string): string | null;
//# sourceMappingURL=template.d.ts.map