// SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * Legacy config path export for backwards compatibility.
 */

import { join } from "node:path";

export const CONFIG_DIR = join(process.env.HOME ?? "/tmp", ".openclaw/milimo");

export function configPath(): string {
  return join(CONFIG_DIR, "config.json");
}
