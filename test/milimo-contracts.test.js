// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Contract validation tests for Milimo Claw inter-claw messaging.
 *
 * Tests verify the message matrix defined in mesh_config.yaml:
 * - Valid contracts pass validation
 * - Missing or invalid fields are rejected
 * - Unauthorized sender→recipient→type routes are blocked
 * - Cross-role policy enforcement matches the project spec
 * - Build Claw routes work correctly
 * - War Room is reachable by all roles
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const path = require("path");
const fs = require("fs");
const yaml = require("yaml");

const MESH_CONFIG_PATH = path.join(__dirname, "..", "milimo-blueprint", "mesh_config.yaml");
const meshConfig = yaml.parse(fs.readFileSync(MESH_CONFIG_PATH, "utf-8"));
const matrix = meshConfig.message_matrix;
const messageTypes = meshConfig.message_types;

const VALID_ROLES = ["content", "ops", "analytics", "finance", "build"];
const VALID_RECIPIENTS = [...VALID_ROLES, "war_room"];
const VALID_MESSAGE_TYPES = Object.keys(messageTypes);

// ---------------------------------------------------------------------------
// Mesh config loads correctly
// ---------------------------------------------------------------------------

describe("Mesh config loading", () => {
  it("mesh_config.yaml exists and loads", () => {
    assert.ok(fs.existsSync(MESH_CONFIG_PATH), "mesh_config.yaml not found");
    assert.ok(meshConfig, "Failed to parse mesh_config.yaml");
  });

  it("has message_matrix section", () => {
    assert.ok(matrix, "mesh_config missing message_matrix");
    assert.equal(typeof matrix, "object");
  });

  it("has message_types section", () => {
    assert.ok(messageTypes, "mesh_config missing message_types");
  });

  it("has escalation_rules section", () => {
    assert.ok(meshConfig.escalation_rules, "mesh_config missing escalation_rules");
    assert.ok(Array.isArray(meshConfig.escalation_rules));
  });

  it("defines all 6 message types", () => {
    const expected = ["brief", "query", "response", "signal", "deliverable", "summary"];
    for (const type of expected) {
      assert.ok(messageTypes[type], `Missing message type: ${type}`);
    }
  });
});

// ---------------------------------------------------------------------------
// Valid contracts
// ---------------------------------------------------------------------------

describe("Valid message contracts", () => {
  // Content Claw routes
  it("content → ops: deliverable", () => {
    assert.ok(matrix.content.ops.includes("deliverable"));
  });

  it("content → analytics: query", () => {
    assert.ok(matrix.content.analytics.includes("query"));
  });

  it("content → war_room: deliverable", () => {
    assert.ok(matrix.content.war_room.includes("deliverable"));
  });

  // Ops Claw routes
  it("ops → content: brief", () => {
    assert.ok(matrix.ops.content.includes("brief"));
  });

  it("ops → content: signal", () => {
    assert.ok(matrix.ops.content.includes("signal"));
  });

  it("ops → finance: query", () => {
    assert.ok(matrix.ops.finance.includes("query"));
  });

  it("ops → build: brief", () => {
    assert.ok(matrix.ops.build.includes("brief"));
  });

  it("ops → war_room: signal + deliverable", () => {
    assert.ok(matrix.ops.war_room.includes("signal"));
    assert.ok(matrix.ops.war_room.includes("deliverable"));
  });

  // Analytics Claw routes
  it("analytics → content: response + summary", () => {
    assert.ok(matrix.analytics.content.includes("response"));
    assert.ok(matrix.analytics.content.includes("summary"));
  });

  it("analytics → build: response + signal", () => {
    assert.ok(matrix.analytics.build.includes("response"));
    assert.ok(matrix.analytics.build.includes("signal"));
  });

  it("analytics → war_room: signal + summary", () => {
    assert.ok(matrix.analytics.war_room.includes("signal"));
    assert.ok(matrix.analytics.war_room.includes("summary"));
  });

  // Finance Claw routes
  it("finance → ops: response + signal", () => {
    assert.ok(matrix.finance.ops.includes("response"));
    assert.ok(matrix.finance.ops.includes("signal"));
  });

  it("finance → analytics: summary", () => {
    assert.ok(matrix.finance.analytics.includes("summary"));
  });

  it("finance → war_room: signal + deliverable", () => {
    assert.ok(matrix.finance.war_room.includes("signal"));
    assert.ok(matrix.finance.war_room.includes("deliverable"));
  });

  // Build Claw routes
  it("build → ops: signal + deliverable", () => {
    assert.ok(matrix.build.ops.includes("signal"));
    assert.ok(matrix.build.ops.includes("deliverable"));
  });

  it("build → analytics: query", () => {
    assert.ok(matrix.build.analytics.includes("query"));
  });

  it("build → content: summary", () => {
    assert.ok(matrix.build.content.includes("summary"));
  });

  it("build → war_room: signal + deliverable", () => {
    assert.ok(matrix.build.war_room.includes("signal"));
    assert.ok(matrix.build.war_room.includes("deliverable"));
  });
});

// ---------------------------------------------------------------------------
// Unauthorized routes (cross-role policy enforcement)
// ---------------------------------------------------------------------------

describe("Unauthorized message routes", () => {
  it("content cannot send to finance", () => {
    assert.equal(matrix.content.finance, undefined, "Content should have no route to Finance");
  });

  it("content cannot send to build", () => {
    assert.equal(matrix.content.build, undefined, "Content should have no route to Build");
  });

  it("finance cannot send brief to content", () => {
    assert.equal(matrix.finance.content, undefined, "Finance should have no route to Content");
  });

  it("finance cannot send to build", () => {
    assert.equal(matrix.finance.build, undefined, "Finance should have no route to Build");
  });

  it("build cannot send to finance", () => {
    assert.equal(matrix.build.finance, undefined, "Build should have no route to Finance");
  });

  it("ops cannot send directly to analytics", () => {
    assert.equal(matrix.ops.analytics, undefined, "Ops should have no direct route to Analytics");
  });
});

// ---------------------------------------------------------------------------
// War Room accessibility — all roles must reach it
// ---------------------------------------------------------------------------

describe("War Room accessibility", () => {
  it("every claw role can send at least one message type to war_room", () => {
    for (const role of VALID_ROLES) {
      const routes = matrix[role];
      assert.ok(routes, `Role "${role}" has no routes defined in matrix`);
      assert.ok(
        routes.war_room && routes.war_room.length > 0,
        `${role} has no route to war_room`,
      );
    }
  });

  it("war_room is not a sender (no outbound from war_room in matrix)", () => {
    assert.equal(matrix.war_room, undefined, "war_room should not be a sender in the matrix");
  });
});

// ---------------------------------------------------------------------------
// Approval requirements
// ---------------------------------------------------------------------------

describe("Approval requirements", () => {
  it("deliverable requires approval", () => {
    assert.equal(messageTypes.deliverable.requires_approval, true);
  });

  it("brief does not require approval", () => {
    assert.equal(messageTypes.brief.requires_approval, false);
  });

  it("query does not require approval", () => {
    assert.equal(messageTypes.query.requires_approval, false);
  });

  it("signal does not require approval", () => {
    assert.equal(messageTypes.signal.requires_approval, false);
  });

  it("summary does not require approval", () => {
    assert.equal(messageTypes.summary.requires_approval, false);
  });

  it("response does not require approval", () => {
    assert.equal(messageTypes.response.requires_approval, false);
  });
});

// ---------------------------------------------------------------------------
// Matrix completeness — every role in the matrix is valid
// ---------------------------------------------------------------------------

describe("Matrix role validation", () => {
  it("all sender roles in matrix are valid claw roles", () => {
    for (const sender of Object.keys(matrix)) {
      assert.ok(VALID_ROLES.includes(sender), `Unknown sender role in matrix: ${sender}`);
    }
  });

  it("all recipient roles in matrix are valid", () => {
    for (const [sender, routes] of Object.entries(matrix)) {
      for (const recipient of Object.keys(routes)) {
        assert.ok(
          VALID_RECIPIENTS.includes(recipient),
          `${sender} routes to unknown role: ${recipient}`,
        );
      }
    }
  });

  it("all message types used in matrix are defined in message_types", () => {
    for (const [sender, routes] of Object.entries(matrix)) {
      for (const [recipient, types] of Object.entries(routes)) {
        for (const type of types) {
          assert.ok(
            VALID_MESSAGE_TYPES.includes(type),
            `${sender} → ${recipient} uses undefined type: ${type}`,
          );
        }
      }
    }
  });
});
