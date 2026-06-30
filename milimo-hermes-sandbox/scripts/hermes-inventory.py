#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# hermes-inventory.py — In-sandbox claw file inventory
#
# Lists all claw-generated files with metadata (size, mtime, type).
# Designed to be invoked from the host via:
#   nemohermes milimo-hermes exec -- python3 /opt/hermes/scripts/hermes-inventory.py
#
# Output: JSON array with entries:
#   { "role": "build", "path": "prs/drafted/pr-42.json", "size": 1234,
#     "mtime": "2026-06-30T12:00:00", "type": "json" }
#
# Flags:
#   --role build      Filter to one claw
#   --pattern *.json  Filter by glob pattern
#   --since 2026-06-01  Only files modified after date

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Try to import from milimo-core; fall back to hardcoded paths for standalone use
try:
    from milimo_core.milimo_paths import CLAWS_DIR
except ImportError:
    # Fallback: try Hermes-native path then OpenClaw
    for p in [
        Path("/sandbox/.hermes/claws"),
        Path("/sandbox/.openclaw/milimo/claws"),
        Path("/sandbox/.openclaw-data/milimo/claws"),
    ]:
        if p.is_dir():
            CLAWS_DIR = p
            break
    else:
        CLAWS_DIR = Path("/sandbox/.hermes/claws")


CLAW_ROLES = ["content", "ops", "analytics", "finance", "build", "assistant"]


def build_inventory(
    claws_dir: Path,
    role_filter: str = "",
    pattern: str = "",
    since: float = 0.0,
) -> List[Dict[str, Any]]:
    inventory: List[Dict[str, Any]] = []
    roles = [role_filter] if role_filter else CLAW_ROLES

    for role in roles:
        role_dir = claws_dir / role
        if not role_dir.is_dir():
            continue

        for fpath in role_dir.rglob("*"):
            if not fpath.is_file():
                continue
            if pattern and not fpath.match(pattern):
                continue

            stat = fpath.stat()
            mtime = stat.st_mtime
            if since > 0.0 and mtime < since:
                continue

            rel = fpath.relative_to(claws_dir)
            inventory.append(
                {
                    "role": role,
                    "path": str(rel),
                    "size": stat.st_size,
                    "mtime": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                    "type": fpath.suffix.lstrip(".") or "unknown",
                }
            )

    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List claw-generated files with metadata"
    )
    parser.add_argument(
        "--role",
        choices=CLAW_ROLES,
        default="",
        help="Filter to a single claw role",
    )
    parser.add_argument(
        "--pattern",
        default="",
        help="Glob pattern filter (e.g. '*.json')",
    )
    parser.add_argument(
        "--since",
        default="",
        help="Only files modified after this date (ISO 8601, e.g. 2026-06-01)",
    )

    args = parser.parse_args()

    since_ts: float = 0.0
    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since)
            since_ts = since_dt.timestamp()
        except ValueError:
            print(f"Invalid date format: {args.since}. Use ISO 8601 (e.g. 2026-06-01).")
            exit(1)

    inventory = build_inventory(
        claws_dir=CLAWS_DIR,
        role_filter=args.role,
        pattern=args.pattern,
        since=since_ts,
    )

    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
