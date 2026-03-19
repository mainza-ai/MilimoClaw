// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Integration Test Harness
 *
 * Provides utilities for running integration tests between TypeScript CLI
 * and Python orchestrator components. Sets up test environments, manages
 * process lifecycle, and provides assertion helpers.
 */

const { spawn } = require("node:child_process");
const { promisify } = require("node:util");
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");

// ---------------------------------------------------------------------------
// Test Harness
// ---------------------------------------------------------------------------

class IntegrationTestHarness {
  constructor(config) {
    this.config = {
      blueprintDir: (config && config.blueprintDir) || path.resolve(__dirname, "../../milimo-blueprint"),
      pythonPath: (config && config.pythonPath) || "python3",
      timeout: (config && config.timeout) || 30000,
      tempDir: (config && config.tempDir) || "",
    };
    this.tempDir = null;
    this.processes = [];
  }

  /**
   * Setup test environment with temporary directories.
   */
  async setup() {
    this.tempDir = await fs.mkdtemp(
      path.join(os.tmpdir(), "milimo-integration-test-")
    );

    const dirs = [
      path.join(this.tempDir, ".milimo", "mesh", "inbox"),
      path.join(this.tempDir, ".milimo", "mesh", "outbox"),
      path.join(this.tempDir, ".milimo", "mesh", "delivered"),
      path.join(this.tempDir, ".milimo", "mesh", "rejected"),
      path.join(this.tempDir, ".milimo", "blueprints"),
      path.join(this.tempDir, ".milimo", "state"),
    ];

    for (const dir of dirs) {
      await fs.mkdir(dir, { recursive: true });
    }
  }

  /**
   * Tear down test environment and cleanup.
   */
  async teardown() {
    for (const proc of this.processes) {
      if (!proc.killed) {
        proc.kill("SIGTERM");
      }
    }
    this.processes = [];

    if (this.tempDir) {
      await fs.rm(this.tempDir, { recursive: true, force: true });
      this.tempDir = null;
    }
  }

  /**
   * Run a Python script and return the result.
   */
  async runPython(script, args) {
    const self = this;
    return new Promise((resolve, reject) => {
      const proc = spawn(self.config.pythonPath, [script, ...(args || [])], {
        cwd: self.config.blueprintDir,
        env: {
          ...process.env,
          HOME: self.tempDir || process.env.HOME,
          MILIMO_TEST_MODE: "true",
        },
        timeout: self.config.timeout,
      });

      self.processes.push(proc);

      let stdout = "";
      let stderr = "";

      proc.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      proc.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      proc.on("close", (code, signal) => {
        resolve({
          stdout,
          stderr,
          exitCode: code !== null ? code : 1,
          signal: signal,
        });
      });

      proc.on("error", (err) => {
        reject(err);
      });
    });
  }

  /**
   * Run a Python module and parse JSON output.
   */
  async runPythonJSON(module, code) {
    const script = `import json; from ${module} import *; print(json.dumps(${code}))`;
    const fullScript = `-c "${script}"`;

    const result = await this.runPython(fullScript);

    if (result.exitCode !== 0) {
      return {
        success: false,
        data: null,
        error: result.stderr || `Exit code: ${result.exitCode}`,
      };
    }

    try {
      return {
        success: true,
        data: JSON.parse(result.stdout.trim()),
      };
    } catch (e) {
      return {
        success: false,
        data: null,
        error: `JSON parse error: ${e.message}`,
      };
    }
  }

  /**
   * Write a message to the mesh inbox for testing.
   */
  async writeTestMessage(role, message) {
    if (!this.tempDir) {
      throw new Error("Harness not setup");
    }

    const inbox = path.join(this.tempDir, ".milimo", "mesh", "inbox", role);
    await fs.mkdir(inbox, { recursive: true });

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `${timestamp}_${message.message_id || Date.now()}.json`;
    const filepath = path.join(inbox, filename);

    await fs.writeFile(filepath, JSON.stringify(message, null, 2));

    return filepath;
  }

  /**
   * Read messages from a role's inbox.
   */
  async readInbox(role) {
    if (!this.tempDir) {
      throw new Error("Harness not setup");
    }

    const inbox = path.join(this.tempDir, ".milimo", "mesh", "inbox", role);

    try {
      const files = await fs.readdir(inbox);
      const messages = [];

      for (const file of files) {
        if (!file.endsWith(".json")) continue;
        const content = await fs.readFile(path.join(inbox, file), "utf-8");
        messages.push(JSON.parse(content));
      }

      return messages.sort((a, b) =>
        (a.timestamp).localeCompare(b.timestamp)
      );
    } catch {
      return [];
    }
  }

  /**
   * Write a blueprint state for testing.
   */
  async writeBlueprintState(squadId, role, state) {
    if (!this.tempDir) {
      throw new Error("Harness not setup");
    }

    const stateDir = path.join(
      this.tempDir,
      ".milimo",
      "blueprints",
      squadId,
      role
    );
    await fs.mkdir(stateDir, { recursive: true });

    await fs.writeFile(
      path.join(stateDir, "state.json"),
      JSON.stringify(state, null, 2)
    );
  }

  /**
   * Get the temp directory path.
   */
  getTempDir() {
    if (!this.tempDir) {
      throw new Error("Harness not setup");
    }
    return this.tempDir;
  }

  /**
   * Get the config.
   */
  getConfig() {
    return { ...this.config };
  }
}

// ---------------------------------------------------------------------------
// Test Utilities
// ---------------------------------------------------------------------------

/**
 * Create a test message with defaults.
 */
function createTestMessage(overrides) {
  return {
    message_id: `test-${Date.now()}`,
    sender_role: "content",
    recipient_role: "ops",
    message_type: "deliverable",
    payload: { test: true },
    squad_id: "test-squad",
    timestamp: new Date().toISOString(),
    ...(overrides || {}),
  };
}

/**
 * Assert that a value matches expected shape.
 */
function assertShape(value, shape) {
  if (typeof value !== "object" || value === null) {
    throw new Error(`Expected object, got ${typeof value}`);
  }

  for (const [key, type] of Object.entries(shape)) {
    const actual = value[key];
    const actualType = Array.isArray(actual) ? "array" : typeof actual;

    if (actualType !== type) {
      throw new Error(
        `Expected ${key} to be ${type}, got ${actualType}`
      );
    }
  }

  return true;
}

/**
 * Wait for a condition to be true.
 */
async function waitFor(condition, timeout, interval) {
  const actualTimeout = timeout || 5000;
  const actualInterval = interval || 100;
  const start = Date.now();

  while (Date.now() - start < actualTimeout) {
    if (await condition()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, actualInterval));
  }

  throw new Error(`Condition not met within ${actualTimeout}ms`);
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  IntegrationTestHarness,
  createTestMessage,
  assertShape,
  waitFor,
};
