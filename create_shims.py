#!/usr/bin/env python3
"""Create shim files for all modules in orchestrator subdirectories."""

import os

SHIM_TEMPLATE = '''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {module_name}.

DEPRECATED: Import from milimo_core.{package} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{package}.{module_name} is deprecated; use milimo_core.{package} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{package} import *  # noqa: F403,F401
'''

ORCHESTRATOR_DIR = "/Users/mck/Desktop/MilimoClaw/milimo-blueprint/orchestrator"

# Map of directory -> milimo_core package
PACKAGE_MAP = {
    "analytics": "analytics",
    "build": "build",
    "content": "content",
    "finance": "finance",
    "ops": "ops",
    "assistant": "assistant",
    "evolution": "evolution",
    "protocols": "protocols",
    "stubs": "stubs",
    "templates": "templates",
}

def create_shims():
    for dir_name, package_name in PACKAGE_MAP.items():
        dir_path = os.path.join(ORCHESTRATOR_DIR, dir_name)
        if not os.path.isdir(dir_path):
            continue

        for filename in os.listdir(dir_path):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                shim_content = SHIM_TEMPLATE.format(
                    module_name=module_name,
                    package=package_name
                )
                file_path = os.path.join(dir_path, filename)
                with open(file_path, "w") as f:
                    f.write(shim_content)
                print(f"Created shim: {file_path}")

if __name__ == "__main__":
    create_shims()
