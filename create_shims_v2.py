#!/usr/bin/env python3
"""Create proper shim files for all modules in orchestrator subdirectories."""

import os

ORCHESTRATOR_DIR = "/Users/mck/Desktop/MilimoClaw/milimo-blueprint/orchestrator"
MILIMO_CORE_DIR = "/Users/mck/Desktop/MilimoClaw/milimo-core/src/milimo_core"

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

def get_public_names(module_path):
    import ast
    with open(module_path, 'r') as f:
        content = f.read()
    tree = ast.parse(content)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not node.name.startswith('_'):
            names.append(node.name)
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith('_'):
                    names.append(target.id)
    return list(set(names))

def create_shim_file(shim_path, pkg, mod_name):
    original_path = os.path.join(MILIMO_CORE_DIR, pkg, f"{mod_name}.py")

    if os.path.exists(original_path):
        public_names = get_public_names(original_path)
        filtered = [n for n in public_names if n not in ('Any', 'Path', 'Dict', 'List', 'Optional', 'Union', 'Literal', 'ClassVar', 'Final', 'Protocol', 'TypeVar', 'Generic', 'Callable', 'Awaitable', 'Coroutine', 'AsyncIterable', 'AsyncIterator', 'Iterator', 'Iterable', 'Sequence', 'Mapping', 'Set', 'FrozenSet', 'Tuple', 'Type', 'Collection', 'Container', 'Reversible', 'SupportsInt', 'SupportsFloat', 'SupportsComplex', 'SupportsBytes', 'SupportsIndex', 'SupportsAbs', 'SupportsRound', 'SupportsLen', 'SupportsGetItem', 'SupportsSetItem', 'SupportsDelItem', 'SupportsIter', 'SupportsContains', 'SupportsKeys', 'SupportsValues', 'SupportsItems', 'SupportsReversed', 'SupportsLengthHint', 'NoReturn', 'Never', 'Final', 'final', 'override', 'deprecated', 'deprecate', 'runtime_checkable', 'dataclass', 'field', 'fields', 'Field', 'InitVar', 'KW_ONLY', 'property', 'cached_property', 'abstractmethod', 'abstractproperty', 'abstractclassmethod', 'abstractstaticmethod', 'classmethod', 'staticmethod')]
        if filtered:
            imports = ', '.join(sorted(filtered))
            shim_content = f'''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {mod_name}.

DEPRECATED: Import from milimo_core.{pkg}.{mod_name} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{pkg}.{mod_name} is deprecated; use milimo_core.{pkg}.{mod_name} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{pkg}.{mod_name} import {imports}
'''
        else:
            shim_content = f'''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {mod_name}.

DEPRECATED: Import from milimo_core.{pkg}.{mod_name} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{pkg}.{mod_name} is deprecated; use milimo_core.{pkg}.{mod_name} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{pkg}.{mod_name} import *  # noqa: F403,F401
'''
    else:
        shim_content = f'''# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Backward-compatibility shim for {mod_name}.

DEPRECATED: Import from milimo_core.{pkg} directly.
"""

import warnings

warnings.warn(
    "orchestrator.{pkg}.{mod_name} is deprecated; use milimo_core.{pkg} instead",
    DeprecationWarning,
    stacklevel=2,
)

from milimo_core.{pkg} import *  # noqa: F403,F401
'''

    with open(shim_path, 'w') as f:
        f.write(shim_content)

def create_shims():
    for dir_name, pkg in PACKAGE_MAP.items():
        dir_path = os.path.join(ORCHESTRATOR_DIR, dir_name)
        if not os.path.isdir(dir_path):
            continue
        for filename in os.listdir(dir_path):
            if filename.endswith(".py") and filename != "__init__.py":
                mod_name = filename[:-3]
                shim_path = os.path.join(dir_path, filename)
                create_shim_file(shim_path, pkg, mod_name)
                print(f"Created shim: {shim_path}")

if __name__ == "__main__":
    create_shims()
