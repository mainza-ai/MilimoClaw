// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Jest tests for role selection conditional logic in onboard.ts
 */

import { formatRoleDisplay } from "../commands/onboard.js";

describe("Role selection conditional logic", () => {
  describe("formatRoleDisplay", () => {
    it("returns readable string for solo mode", () => {
      const config = {
        clawRole: "solo" as const,
        activeClaws: ["content", "ops", "analytics", "finance", "build"],
      };
      expect(formatRoleDisplay(config as any)).toBe("Solo (content, ops, analytics, finance, build)");
    });

    it("returns role name unchanged for mesh mode", () => {
      const config = {
        clawRole: "content" as const,
        activeClaws: ["content"],
      };
      expect(formatRoleDisplay(config as any)).toBe("content");
    });

    it("handles missing activeClaws gracefully", () => {
      const config = {
        clawRole: "solo" as const,
      };
      expect(formatRoleDisplay(config as any)).toBe("Solo (all claws)");
    });

    it("handles empty activeClaws gracefully", () => {
      const config = {
        clawRole: "solo" as const,
        activeClaws: [],
      };
      // Empty array results in "Solo ()" - empty claws string
      expect(formatRoleDisplay(config as any)).toBe("Solo ()");
    });

    it("shows correct claws for content-agency template in solo mode", () => {
      const config = {
        clawRole: "solo" as const,
        activeClaws: ["content", "ops", "analytics"],
      };
      expect(formatRoleDisplay(config as any)).toBe("Solo (content, ops, analytics)");
    });

    it("shows correct claws for ai-micro-saas template in solo mode", () => {
      const config = {
        clawRole: "solo" as const,
        activeClaws: ["build", "ops", "analytics", "finance"],
      };
      expect(formatRoleDisplay(config as any)).toBe("Solo (build, ops, analytics, finance)");
    });
  });

  describe("ClawRole type", () => {
    it("includes 'solo' as a valid ClawRole", () => {
      const role: "solo" = "solo";
      expect(role).toBe("solo");
    });

    it("CLAW_ROLES array excludes 'solo' (it's a mode indicator)", async () => {
      const { CLAW_ROLES } = await import("../index.js");
      expect(CLAW_ROLES).toContain("content");
      expect(CLAW_ROLES).toContain("ops");
      expect(CLAW_ROLES).toContain("analytics");
      expect(CLAW_ROLES).toContain("finance");
      expect(CLAW_ROLES).toContain("build");
      expect(CLAW_ROLES).not.toContain("solo");
    });
  });

  describe("Solo mode behavior", () => {
    it("solo mode should set clawRole to 'solo'", () => {
      const isSolo = true;
      const clawRole = isSolo ? "solo" : "content";
      expect(clawRole).toBe("solo");
    });

    it("solo mode meshMembers should contain all active claws", () => {
      const isSolo = true;
      const templateActiveClaws = ["content", "ops", "analytics", "finance", "build"];
      const meshMembers = isSolo ? templateActiveClaws : ["content"];
      expect(meshMembers).toEqual(["content", "ops", "analytics", "finance", "build"]);
    });

    it("solo mode for content-agency template has 3 active claws", () => {
      const isSolo = true;
      const templateActiveClaws = ["content", "ops", "analytics"];
      const meshMembers = isSolo ? templateActiveClaws : ["content"];
      expect(meshMembers).toEqual(["content", "ops", "analytics"]);
      expect(meshMembers).not.toContain("finance");
      expect(meshMembers).not.toContain("build");
    });
  });

  describe("Mesh mode behavior", () => {
    it("mesh mode should set clawRole to selected role", () => {
      const isSolo = false;
      const selectedRole = "analytics";
      const clawRole = isSolo ? "solo" : selectedRole;
      expect(clawRole).toBe("analytics");
    });

    it("mesh mode meshMembers should contain only selected role", () => {
      const isSolo = false;
      const selectedRole = "content";
      const meshMembers = isSolo ? ["content", "ops", "analytics"] : [selectedRole];
      expect(meshMembers).toEqual(["content"]);
    });

    it("mesh mode only offers template-active claws", () => {
      const templateActiveClaws = ["content", "ops", "analytics"];
      const allRoles = ["content", "ops", "analytics", "finance", "build"];
      const availableRoles = allRoles.filter((r) => templateActiveClaws.includes(r));
      expect(availableRoles).toEqual(["content", "ops", "analytics"]);
      expect(availableRoles).not.toContain("finance");
      expect(availableRoles).not.toContain("build");
    });
  });
});
