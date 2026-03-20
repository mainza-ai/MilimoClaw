"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Jest tests for ConfigManager
 */
const node_fs_1 = require("node:fs");
const config_js_1 = require("../onboard/config.js");
jest.mock("node:fs", () => ({
    existsSync: jest.fn(),
    mkdirSync: jest.fn(),
    readFileSync: jest.fn(),
    writeFileSync: jest.fn(),
    unlinkSync: jest.fn(),
    rmSync: jest.fn(),
}));
jest.mock("node:path", () => ({
    join: jest.fn((...args) => args.join("/")),
}));
const mockedFs = jest.mocked({
    existsSync: node_fs_1.existsSync,
    mkdirSync: node_fs_1.mkdirSync,
    readFileSync: node_fs_1.readFileSync,
    writeFileSync: node_fs_1.writeFileSync,
    unlinkSync: node_fs_1.unlinkSync,
    rmSync: node_fs_1.rmSync,
});
describe("ConfigManager", () => {
    const mockConfig = {
        squadName: "test-squad",
        clawRole: "build",
        template: "solo-founder",
        solo: true,
        meshMembers: ["build"],
        meshSecret: null,
        operatorName: "TestOperator",
        warRoomMode: "full",
        onboardedAt: "2026-03-20T00:00:00.000Z",
        initializedAt: "2026-03-20T00:00:00.000Z",
        blueprintVersion: "0.1.0",
    };
    beforeEach(() => {
        jest.clearAllMocks();
        config_js_1.ConfigManager._clearCache?.();
    });
    describe("load()", () => {
        it("returns null when no config file exists", () => {
            mockedFs.existsSync.mockReturnValue(false);
            const result = config_js_1.ConfigManager.load();
            expect(result).toBeNull();
        });
        it("loads valid config from file", () => {
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockConfig));
            const result = config_js_1.ConfigManager.load();
            expect(result).not.toBeNull();
            expect(result?.squadName).toBe("test-squad");
            expect(result?.clawRole).toBe("build");
        });
        it("returns null for malformed JSON", () => {
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue("not valid json");
            const result = config_js_1.ConfigManager.load();
            expect(result).toBeNull();
        });
        it("caches config after first load", () => {
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockConfig));
            config_js_1.ConfigManager.load();
            config_js_1.ConfigManager.load();
            expect(mockedFs.readFileSync).toHaveBeenCalledTimes(1);
        });
        it("handles missing optional fields with defaults", () => {
            const partialConfig = { squadName: "partial", clawRole: "content" };
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue(JSON.stringify(partialConfig));
            const result = config_js_1.ConfigManager.load();
            expect(result).not.toBeNull();
            expect(result?.squadName).toBe("partial");
            expect(result?.solo).toBe(true);
            expect(result?.warRoomMode).toBe("full");
        });
    });
    describe("save()", () => {
        it("writes config to file with correct permissions", () => {
            mockedFs.existsSync.mockReturnValue(true);
            config_js_1.ConfigManager.save(mockConfig);
            expect(mockedFs.writeFileSync).toHaveBeenCalledWith(expect.any(String), JSON.stringify(mockConfig, null, 2), { mode: 0o600 });
        });
        it("creates config directory if it does not exist", () => {
            mockedFs.existsSync.mockReturnValue(false);
            config_js_1.ConfigManager.save(mockConfig);
            expect(mockedFs.mkdirSync).toHaveBeenCalled();
        });
        it("updates cache after save", () => {
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue(JSON.stringify({ ...mockConfig, squadName: "old" }));
            config_js_1.ConfigManager.save(mockConfig);
            const result = config_js_1.ConfigManager.load();
            expect(result?.squadName).toBe("test-squad");
        });
    });
    describe("migrate()", () => {
        it("returns false when no legacy files exist", () => {
            mockedFs.existsSync.mockReturnValue(false);
            const result = config_js_1.ConfigManager.migrate();
            expect(result.migrated).toBe(false);
            expect(result.hadLegacyState).toBe(false);
        });
        it("migrates legacy state.json to config.json", () => {
            const legacyState = {
                squadName: "legacy-squad",
                clawRole: "ops",
                template: "content-agency",
                solo: false,
                meshMembers: ["content", "ops"],
                initializedAt: "2026-03-19T00:00:00.000Z",
                blueprintVersion: "0.0.5",
            };
            mockedFs.existsSync
                .mockReturnValueOnce(true)
                .mockReturnValueOnce(false)
                .mockReturnValueOnce(true);
            mockedFs.readFileSync
                .mockReturnValueOnce(JSON.stringify(legacyState))
                .mockReturnValueOnce("");
            const result = config_js_1.ConfigManager.migrate();
            expect(result.migrated).toBe(true);
            expect(result.hadLegacyState).toBe(true);
            expect(mockedFs.unlinkSync).toHaveBeenCalled();
        });
        it("merges legacy state with existing config", () => {
            const legacyState = {
                squadName: "legacy-squad",
                clawRole: "analytics",
                template: "tech-consultancy",
                solo: false,
                meshMembers: ["build", "ops"],
                initializedAt: "2026-03-18T00:00:00.000Z",
                blueprintVersion: "0.0.3",
            };
            const existingConfig = {
                squadName: "new-squad",
                clawRole: "build",
                operatorName: "TestUser",
                meshSecret: "secret123",
            };
            mockedFs.existsSync
                .mockReturnValueOnce(true)
                .mockReturnValueOnce(true)
                .mockReturnValueOnce(true);
            mockedFs.readFileSync
                .mockReturnValueOnce(JSON.stringify(legacyState))
                .mockReturnValueOnce(JSON.stringify(existingConfig));
            const result = config_js_1.ConfigManager.migrate();
            expect(result.migrated).toBe(true);
        });
        it("removes state.json after successful migration", () => {
            mockedFs.existsSync.mockReturnValue(true);
            mockedFs.readFileSync.mockReturnValue(JSON.stringify({ squadName: "test", clawRole: "build" }));
            config_js_1.ConfigManager.migrate();
            expect(mockedFs.unlinkSync).toHaveBeenCalledWith(expect.stringContaining("state.json"));
        });
    });
    describe("clear()", () => {
        it("removes config file if it exists", () => {
            mockedFs.existsSync.mockReturnValue(true);
            config_js_1.ConfigManager.clear();
            expect(mockedFs.unlinkSync).toHaveBeenCalled();
        });
        it("removes legacy state.json if it exists", () => {
            mockedFs.existsSync.mockReturnValue(true);
            config_js_1.ConfigManager.clear();
            expect(mockedFs.unlinkSync).toHaveBeenCalledTimes(2);
        });
        it("does not throw if files do not exist", () => {
            mockedFs.existsSync.mockReturnValue(false);
            expect(() => config_js_1.ConfigManager.clear()).not.toThrow();
        });
    });
    describe("getConfigDir()", () => {
        it("returns config directory path", () => {
            const result = config_js_1.ConfigManager.getConfigDir();
            expect(result).toContain(".milimo");
        });
    });
    describe("ensureDirectories()", () => {
        it("creates all required subdirectories", () => {
            mockedFs.existsSync.mockReturnValue(false);
            config_js_1.ConfigManager.ensureDirectories();
            expect(mockedFs.mkdirSync).toHaveBeenCalledTimes(9);
        });
        it("does not recreate existing directories", () => {
            mockedFs.existsSync.mockReturnValue(true);
            config_js_1.ConfigManager.ensureDirectories();
            expect(mockedFs.mkdirSync).toHaveBeenCalledTimes(1);
        });
    });
    describe("hasLegacyState()", () => {
        it("returns true when state.json exists", () => {
            mockedFs.existsSync.mockReturnValue(true);
            const result = config_js_1.ConfigManager.hasLegacyState();
            expect(result).toBe(true);
        });
        it("returns false when state.json does not exist", () => {
            mockedFs.existsSync.mockReturnValue(false);
            const result = config_js_1.ConfigManager.hasLegacyState();
            expect(result).toBe(false);
        });
    });
});
describe("loadOnboardConfig (legacy export)", () => {
    it("delegates to ConfigManager.load", () => {
        const { loadOnboardConfig } = jest.requireActual("../onboard/config.js");
        mockedFs.existsSync.mockReturnValue(false);
        const result = loadOnboardConfig();
        expect(result).toBeNull();
    });
});
describe("saveOnboardConfig (legacy export)", () => {
    it("delegates to ConfigManager.save", () => {
        mockedFs.existsSync.mockReturnValue(true);
        const { saveOnboardConfig } = jest.requireActual("../onboard/config.js");
        saveOnboardConfig({
            squadName: "test",
            clawRole: "build",
            template: "solo",
            solo: true,
            meshMembers: [],
            meshSecret: null,
            operatorName: "op",
            warRoomMode: "full",
            onboardedAt: null,
            initializedAt: new Date().toISOString(),
            blueprintVersion: "0.1.0",
        });
        expect(mockedFs.writeFileSync).toHaveBeenCalled();
    });
});
//# sourceMappingURL=config.test.js.map