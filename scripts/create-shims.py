#!/usr/bin/env python3
"""Create simple shim files using import *."""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ORCHESTRATOR_DIR = os.path.join(ROOT_DIR, "milimo-blueprint", "orchestrator")
MILIMO_CORE_DIR = os.path.join(ROOT_DIR, "milimo-core", "src", "milimo_core")

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

SHIM_TEMPLATE = '''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {module_name}.

DEPRECATED: Import from milimo_core.{package}.{module_name} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{package}.{module_name} is deprecated; use milimo_core.{package}.{module_name} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{package}.{module_name} import *  # noqa: F403,F401
'''

def create_shims():
    for dir_name, package_name in PACKAGE_MAP.items():
        dir_path = os.path.join(ORCHESTRATOR_DIR, dir_name)
        if not os.path.isdir(dir_path):
            continue
        for filename in os.listdir(dir_path):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                shim_path = os.path.join(dir_path, filename)

                # Check if source module exists in milimo_core
                source_path = os.path.join(MILIMO_CORE_DIR, package_name, f"{module_name}.py")
                if not os.path.exists(source_path):
                    # Fallback to package-level import
                    shim_content = f'''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {module_name}.

DEPRECATED: Import from milimo_core.{package_name} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{package_name}.{module_name} is deprecated; use milimo_core.{package_name} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{package_name} import *  # noqa: F403,F401
'''
                else:
                    shim_content = SHIM_TEMPLATE.format(
                        module_name=module_name,
                        package=package_name
                    )

                with open(shim_path, 'w') as f:
                    f.write(shim_content)
                print(f"Created shim: {shim_path}")

if __name__ == "__main__":
    create_shims()
