#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
CI-runnable script to prevent code drift between core packages and sandbox mirrors.
"""

import sys
from pathlib import Path


def diff_files(p1: Path, p2: Path) -> bool:
    if not p1.exists() or not p2.exists():
        print(f"Error: One of the files does not exist: {p1} or {p2}")
        return False

    c1 = p1.read_bytes()
    c2 = p2.read_bytes()

    if c1 != c2:
        print(f"Drift detected between:\n  {p1}\n  {p2}")
        return False
    return True


def main():
    root = Path(__file__).parent.parent
    core_src = root / "milimo-core/src/milimo_core"
    sandbox_core_src = root / "milimo-hermes-sandbox/milimo-core/src/milimo_core"

    bp_src = root / "milimo-blueprint/orchestrator"
    sandbox_bp_src = root / "milimo-hermes-sandbox/milimo-blueprint/orchestrator"

    drift_found = False

    # Check core
    for p in core_src.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        rel = p.relative_to(core_src)
        p_sandbox = sandbox_core_src / rel
        if not p_sandbox.exists():
            print(f"File missing in sandbox copy: {p_sandbox}")
            drift_found = True
            continue
        if not diff_files(p, p_sandbox):
            drift_found = True

    # Check sandbox files missing in core
    for p in sandbox_core_src.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        rel = p.relative_to(sandbox_core_src)
        p_core = core_src / rel
        if not p_core.exists():
            print(f"File missing in core copy: {p_core}")
            drift_found = True

    # Check blueprint orchestrator
    for p in bp_src.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        rel = p.relative_to(bp_src)
        p_sandbox = sandbox_bp_src / rel
        if not p_sandbox.exists():
            print(f"File missing in sandbox blueprint copy: {p_sandbox}")
            drift_found = True
            continue
        if not diff_files(p, p_sandbox):
            drift_found = True

    # Check sandbox bp files missing in bp
    for p in sandbox_bp_src.rglob("*.py"):
        if "__pycache__" in str(p):
            continue
        rel = p.relative_to(sandbox_bp_src)
        p_core = bp_src / rel
        if not p_core.exists():
            print(f"File missing in blueprint copy: {p_core}")
            drift_found = True

    if drift_found:
        print("\nValidation failed: Code drift detected between core and sandbox mirrors!")
        sys.exit(1)
    else:
        print("Success: Core and sandbox mirrors are in perfect sync.")
        sys.exit(0)


if __name__ == "__main__":
    main()
