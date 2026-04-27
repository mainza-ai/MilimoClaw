// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const originalHome = process.env.HOME;

beforeEach(() => {
  process.env.HOME = "/home/test";
  vi.resetModules();
});

afterEach(() => {
  process.env.HOME = originalHome;
  vi.restoreAllMocks();
});

vi.mock("node:fs", () => ({
  existsSync: vi.fn(),
  mkdirSync: vi.fn(),
  readFileSync: vi.fn(),
  writeFileSync: vi.fn(),
  unlinkSync: vi.fn(),
  rmSync: vi.fn(),
}));

vi.mock("node:path", () => ({
  join: vi.fn((...args: string[]) => args.join("/")),
}));

vi.mock("../lib/config-encryption.js", () => ({
  encryptConfig: vi.fn((config: Record<string, unknown>) => config),
  decryptConfig: vi.fn((config: Record<string, unknown>) => config),
  isEncrypted: vi.fn(() => false),
}));

describe("ConfigManager", () => {
  let mockedFs: any;
  let ConfigManager: any;
  let _MilimoConfig: any;
  let _loadOnboardConfig: any;
  let _saveOnboardConfig: any;
  let clearCache: any;

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
    assistant: {
      name: "Nova",
      creature: "a claw",
      vibe: "sharp and unhurried",
      emoji: "🦀",
    },
    activeClaws: ["content", "ops", "analytics", "finance", "build"],
  };

  beforeEach(async () => {
    process.env.HOME = "/home/test";
    vi.clearAllMocks();

    const fsModule = await import("node:fs");
    mockedFs = fsModule as any;

    const configModule = await import("../onboard/config");
    ConfigManager = configModule.ConfigManager;
    _MilimoConfig = configModule.MilimoConfig;
    _loadOnboardConfig = configModule.loadOnboardConfig;
    _saveOnboardConfig = configModule.saveOnboardConfig;
    clearCache = configModule.clearCache;
    clearCache();
  });

  describe("load()", () => {
    it("returns null when no config file exists", () => {
      mockedFs.existsSync.mockReturnValue(false);

      const result = ConfigManager.load();

      expect(result).toBeNull();
    });

    it("loads valid config from file", () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(mockConfig));

      const result = ConfigManager.load();

      expect(result).not.toBeNull();
      expect(result?.squadName).toBe("test-squad");
      expect(result?.clawRole).toBe("build");
    });

    it("returns null for malformed JSON", () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue("not valid json");

      const result = ConfigManager.load();

      expect(result).toBeNull();
    });

    it("handles missing optional fields with defaults", () => {
      const partialConfig = { squadName: "partial", clawRole: "content" };
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(JSON.stringify(partialConfig));

      const result = ConfigManager.load();

      expect(result).not.toBeNull();
      expect(result?.squadName).toBe("partial");
      expect(result?.solo).toBe(true);
      expect(result?.warRoomMode).toBe("full");
    });
  });

  describe("save()", () => {
    it("writes config to file with correct permissions", () => {
      mockedFs.existsSync.mockReturnValue(true);

      ConfigManager.save(mockConfig);

      expect(mockedFs.writeFileSync).toHaveBeenCalledWith(
        expect.any(String),
        JSON.stringify(mockConfig, null, 2),
        { mode: 0o600 },
      );
    });

    it("creates config directory if it does not exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      ConfigManager.save(mockConfig);

      expect(mockedFs.mkdirSync).toHaveBeenCalled();
    });
  });

  describe("migrate()", () => {
    it("returns false when no legacy files exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      const result = ConfigManager.migrate();

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

      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync
        .mockReturnValueOnce(JSON.stringify(legacyState))
        .mockReturnValueOnce("");

      const result = ConfigManager.migrate();

      expect(result.migrated).toBe(true);
      expect(result.hadLegacyState).toBe(true);
      expect(mockedFs.unlinkSync).toHaveBeenCalled();
    });

    it("removes state.json after successful migration", () => {
      mockedFs.existsSync.mockReturnValue(true);
      mockedFs.readFileSync.mockReturnValue(
        JSON.stringify({ squadName: "test", clawRole: "build" }),
      );

      ConfigManager.migrate();

      expect(mockedFs.unlinkSync).toHaveBeenCalledWith(expect.stringContaining("state.json"));
    });
  });

  describe("clear()", () => {
    it("removes config file if it exists", () => {
      mockedFs.existsSync.mockReturnValue(true);

      ConfigManager.clear();

      expect(mockedFs.unlinkSync).toHaveBeenCalled();
    });

    it("does not throw if files do not exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      expect(() => ConfigManager.clear()).not.toThrow();
    });
  });

  describe("getConfigDir()", () => {
    it("returns config directory path", () => {
      const result = ConfigManager.getConfigDir();

      expect(result).toContain(".openclaw-data/milimo");
    });
  });

  describe("ensureDirectories()", () => {
    it("creates all required subdirectories", () => {
      mockedFs.existsSync.mockReturnValue(false);

      ConfigManager.ensureDirectories();

      expect(mockedFs.mkdirSync).toHaveBeenCalled();
    });
  });

  describe("hasLegacyState()", () => {
    it("returns true when state.json exists", () => {
      mockedFs.existsSync.mockReturnValue(true);

      const result = ConfigManager.hasLegacyState();

      expect(result).toBe(true);
    });

    it("returns false when state.json does not exist", () => {
      mockedFs.existsSync.mockReturnValue(false);

      const result = ConfigManager.hasLegacyState();

      expect(result).toBe(false);
    });
  });
});

describe("loadOnboardConfig (legacy export)", () => {
  let mockedFs: any;
  let loadOnboardConfig: any;
  let clearCache: any;

  beforeEach(async () => {
    process.env.HOME = "/home/test";
    vi.clearAllMocks();

    const fsModule = await import("node:fs");
    mockedFs = fsModule as any;

    const configModule = await import("../onboard/config");
    loadOnboardConfig = configModule.loadOnboardConfig;
    clearCache = configModule.clearCache;
    clearCache();
  });

  it("delegates to ConfigManager.load", () => {
    mockedFs.existsSync.mockReturnValue(false);

    const result = loadOnboardConfig();

    expect(result).toBeNull();
  });
});

describe("saveOnboardConfig (legacy export)", () => {
  let mockedFs: any;
  let saveOnboardConfig: any;

  beforeEach(async () => {
    process.env.HOME = "/home/test";
    vi.clearAllMocks();

    const fsModule = await import("node:fs");
    mockedFs = fsModule as any;

    const configModule = await import("../onboard/config");
    saveOnboardConfig = configModule.saveOnboardConfig;
  });

  it("delegates to ConfigManager.save", () => {
    mockedFs.existsSync.mockReturnValue(true);

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
      assistant: {
        name: "Nova",
        creature: "a claw",
        vibe: "sharp and unhurried",
        emoji: "🦀",
      },
      activeClaws: ["content", "ops", "analytics", "finance", "build"],
    });

    expect(mockedFs.writeFileSync).toHaveBeenCalled();
  });
});
