// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Blueprint validation tests for Milimo Claw role blueprints.
 *
 * Verifies:
 * - All 4 role blueprints load valid YAML
 * - Required fields exist on every blueprint
 * - Filesystem mounts don't overlap between roles
 * - Finance Claw has no cloud inference
 * - Every role has a matching sandbox policy
 * - Policies follow OpenShell schema with network_policies section
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const fs = require("fs");
const yaml = require("yaml");

const BLUEPRINT_DIR = path.join(__dirname, "..", "milimo-blueprint");
const ROLES_DIR = path.join(BLUEPRINT_DIR, "roles");
const POLICIES_DIR = path.join(BLUEPRINT_DIR, "policies");

const EXPECTED_ROLES = ["content", "ops", "analytics", "finance"];
const REQUIRED_BLUEPRINT_FIELDS = [
  "role",
  "display_name",
  "description",
  "filesystem_mount",
  "egress_policy",
  "inference_routing",
  "inter_claw_policy",
  "approval_thresholds",
];

function loadBlueprint(role) {
  const file = path.join(ROLES_DIR, `${role}-claw.yaml`);
  return yaml.parse(fs.readFileSync(file, "utf-8"));
}

function loadPolicy(role) {
  const file = path.join(POLICIES_DIR, `${role}-sandbox.yaml`);
  return yaml.parse(fs.readFileSync(file, "utf-8"));
}

// --------------------------------------------------------------------------
// Blueprint YAML loading & schema
// --------------------------------------------------------------------------

describe("Milimo role blueprints", () => {
  it("all 4 role blueprint files exist", () => {
    for (const role of EXPECTED_ROLES) {
      const file = path.join(ROLES_DIR, `${role}-claw.yaml`);
      assert.ok(fs.existsSync(file), `${role}-claw.yaml not found`);
    }
  });

  it("all blueprints parse as valid YAML", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      assert.ok(bp, `${role} blueprint parsed as null/undefined`);
      assert.equal(typeof bp, "object", `${role} blueprint should be an object`);
    }
  });

  it("every blueprint has all required fields", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      for (const field of REQUIRED_BLUEPRINT_FIELDS) {
        assert.ok(
          bp[field] !== undefined,
          `${role} blueprint missing required field: ${field}`,
        );
      }
    }
  });

  it("role field matches filename", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      assert.equal(bp.role, role, `${role} blueprint has role="${bp.role}"`);
    }
  });

  it("every blueprint has a schema_version", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      assert.ok(bp.schema_version, `${role} missing schema_version`);
    }
  });
});

// --------------------------------------------------------------------------
// Filesystem isolation
// --------------------------------------------------------------------------

describe("Filesystem mount isolation", () => {
  it("each role has a unique primary mount", () => {
    const mounts = new Set();
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      const mount = bp.filesystem_mount.primary;
      assert.ok(
        !mounts.has(mount),
        `Duplicate mount "${mount}" — roles must not share primary mounts`,
      );
      mounts.add(mount);
    }
  });

  it("all mounts are under /sandbox/", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      const mount = bp.filesystem_mount.primary;
      assert.ok(
        mount.startsWith("/sandbox/"),
        `${role} mount "${mount}" is not under /sandbox/`,
      );
    }
  });

  it("no role can access another role's primary mount (no cross-mount overlap)", () => {
    const mounts = {};
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      mounts[role] = bp.filesystem_mount.primary;
    }

    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      const crossMounts = bp.filesystem_mount.cross_mounts || [];
      for (const cross of crossMounts) {
        // Cross-mount must not be another role's PRIMARY mount
        for (const [otherRole, otherMount] of Object.entries(mounts)) {
          if (otherRole !== role) {
            assert.notEqual(
              cross.path,
              otherMount,
              `${role} cross-mounts ${otherRole}'s primary mount "${otherMount}"`,
            );
          }
        }
      }
    }
  });
});

// --------------------------------------------------------------------------
// Inference routing
// --------------------------------------------------------------------------

describe("Inference routing", () => {
  it("every blueprint has a default_backend", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      assert.ok(
        bp.inference_routing.default_backend,
        `${role} missing default_backend in inference_routing`,
      );
    }
  });

  it("Finance Claw has cloud_allowed: false", () => {
    const bp = loadBlueprint("finance");
    assert.equal(
      bp.inference_routing.cloud_allowed,
      false,
      "Finance Claw MUST have cloud_allowed: false",
    );
  });

  it("Finance Claw only routes to local-nim", () => {
    const bp = loadBlueprint("finance");
    for (const rule of bp.inference_routing.rules) {
      assert.equal(
        rule.backend,
        "local-nim",
        `Finance rule "${rule.data_type}" uses backend "${rule.backend}" — must be local-nim`,
      );
    }
  });

  it("non-Finance claws have at least one cloud route", () => {
    for (const role of ["content", "ops", "analytics"]) {
      const bp = loadBlueprint(role);
      const hasCloud = bp.inference_routing.rules.some((r) => r.backend === "cloud");
      assert.ok(hasCloud, `${role} has no cloud inference route`);
    }
  });
});

// --------------------------------------------------------------------------
// Inter-claw policy
// --------------------------------------------------------------------------

describe("Inter-claw policy", () => {
  it("every blueprint has inbound and outbound sections", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      assert.ok(bp.inter_claw_policy.inbound, `${role} missing inbound inter_claw_policy`);
      assert.ok(bp.inter_claw_policy.outbound, `${role} missing outbound inter_claw_policy`);
    }
  });

  it("all referenced roles are valid", () => {
    const validTargets = [...EXPECTED_ROLES, "build", "war_room"];
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      for (const entry of bp.inter_claw_policy.inbound) {
        assert.ok(
          validTargets.includes(entry.from),
          `${role} inbound references unknown role "${entry.from}"`,
        );
      }
      for (const entry of bp.inter_claw_policy.outbound) {
        assert.ok(
          validTargets.includes(entry.to),
          `${role} outbound references unknown role "${entry.to}"`,
        );
      }
    }
  });
});

// --------------------------------------------------------------------------
// Sandbox policies
// --------------------------------------------------------------------------

describe("Milimo sandbox policies", () => {
  it("all 4 role policy files exist", () => {
    for (const role of EXPECTED_ROLES) {
      const file = path.join(POLICIES_DIR, `${role}-sandbox.yaml`);
      assert.ok(fs.existsSync(file), `${role}-sandbox.yaml not found`);
    }
  });

  it("all policies parse as valid YAML", () => {
    for (const role of EXPECTED_ROLES) {
      const policy = loadPolicy(role);
      assert.ok(policy, `${role} policy parsed as null`);
    }
  });

  it("every policy has network_policies section", () => {
    for (const role of EXPECTED_ROLES) {
      const policy = loadPolicy(role);
      assert.ok(
        policy.network_policies,
        `${role} policy missing network_policies`,
      );
    }
  });

  it("every policy has filesystem_policy section", () => {
    for (const role of EXPECTED_ROLES) {
      const policy = loadPolicy(role);
      assert.ok(
        policy.filesystem_policy,
        `${role} policy missing filesystem_policy`,
      );
    }
  });

  it("finance policy has NO cloud inference endpoint", () => {
    const policy = loadPolicy("finance");
    const policyNames = Object.keys(policy.network_policies);
    assert.ok(
      !policyNames.includes("nvidia"),
      "Finance sandbox MUST NOT have nvidia cloud inference endpoint",
    );
    // Verify no endpoint points to NVIDIA cloud
    for (const [name, np] of Object.entries(policy.network_policies)) {
      if (np.endpoints) {
        for (const ep of np.endpoints) {
          assert.notEqual(
            ep.host,
            "integrate.api.nvidia.com",
            `Finance policy "${name}" has cloud inference endpoint`,
          );
        }
      }
    }
  });

  it("non-finance policies have nvidia inference endpoint", () => {
    for (const role of ["content", "ops", "analytics"]) {
      const policy = loadPolicy(role);
      assert.ok(
        policy.network_policies.nvidia,
        `${role} policy missing nvidia inference endpoint`,
      );
    }
  });

  it("policy read_write dirs match blueprint primary mount", () => {
    for (const role of EXPECTED_ROLES) {
      const bp = loadBlueprint(role);
      const policy = loadPolicy(role);
      const mount = bp.filesystem_mount.primary;
      assert.ok(
        policy.filesystem_policy.read_write.includes(mount),
        `${role} policy read_write doesn't include primary mount "${mount}"`,
      );
    }
  });

  it("no policy has rules at NetworkPolicyRuleDef level (must be inside endpoints)", () => {
    for (const role of EXPECTED_ROLES) {
      const file = path.join(POLICIES_DIR, `${role}-sandbox.yaml`);
      const content = fs.readFileSync(file, "utf-8");
      const lines = content.split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (/^\s{4}rules:/.test(lines[i])) {
          assert.fail(
            `${role} policy line ${i + 1}: rules at policy level (should be inside endpoint)`,
          );
        }
      }
    }
  });
});

// --------------------------------------------------------------------------
// Schema
// --------------------------------------------------------------------------

describe("Claw schema", () => {
  it("claw-schema.yaml exists and loads", () => {
    const file = path.join(BLUEPRINT_DIR, "claw-schema.yaml");
    assert.ok(fs.existsSync(file), "claw-schema.yaml not found");
    const schema = yaml.parse(fs.readFileSync(file, "utf-8"));
    assert.ok(schema.required_fields, "schema missing required_fields");
    assert.ok(schema.valid_roles, "schema missing valid_roles");
  });

  it("schema valid_roles matches expected roles plus build", () => {
    const file = path.join(BLUEPRINT_DIR, "claw-schema.yaml");
    const schema = yaml.parse(fs.readFileSync(file, "utf-8"));
    const expected = ["content", "ops", "analytics", "finance", "build"];
    assert.deepEqual(schema.valid_roles, expected);
  });
});
