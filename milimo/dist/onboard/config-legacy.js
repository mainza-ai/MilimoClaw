"use strict";
// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.CONFIG_DIR = void 0;
exports.configPath = configPath;
/**
 * Legacy config path export for backwards compatibility.
 */
const node_path_1 = require("node:path");
exports.CONFIG_DIR = (0, node_path_1.join)(process.env.HOME ?? "/tmp", ".milimo");
function configPath() {
    return (0, node_path_1.join)(exports.CONFIG_DIR, "config.json");
}
//# sourceMappingURL=config-legacy.js.map