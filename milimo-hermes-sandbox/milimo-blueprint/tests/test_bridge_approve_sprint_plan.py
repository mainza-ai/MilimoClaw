# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for bridge_cli approve_sprint_plan subcommand."""

import json
from unittest.mock import patch
from orchestrator.bridge_cli import handle_command


def test_bridge_approve_sprint_plan(tmp_path):
    """Verify that handle_command('approve_sprint_plan') updates the sprint plan file."""
    # Build sandbox directory mock
    build_base = tmp_path / "claws/build"
    sprint_dir = build_base / "context/sprint"
    sprint_dir.mkdir(parents=True, exist_ok=True)

    # Write a dummy current-plan.json
    plan_data = {
        "plan_id": "plan_12345",
        "status": "pending_review",
        "issues": [{"issue_number": 42, "title": "Implement SA2-1"}]
    }
    plan_file = sprint_dir / "current-plan.json"
    plan_file.write_text(json.dumps(plan_data))

    # Create logs/ operational log directory to prevent file missing errors
    (build_base / "logs").mkdir(parents=True, exist_ok=True)
    (build_base / "logs/operational.log").touch()
    (build_base / "logs/pr-activity.log").touch()
    (build_base / "logs/deploy-activity.log").touch()

    # Patch claw_base to point to our mock build base inside the bridge_cli modules
    with patch("orchestrator.bridge_cli.claw_base", return_value=build_base), \
         patch("milimo_core.bridge_cli.claw_base", return_value=build_base):
        # Run command
        res = handle_command("approve_sprint_plan", {"plan_id": "plan_12345"}, str(tmp_path))

        # Verify response
        assert res["status"] == "approved"
        assert res["first_issue"]["issue_number"] == 42

        # Verify file content updated
        updated_data = json.loads(plan_file.read_text())
        assert updated_data["status"] == "approved"
        assert updated_data.get("approved_at") is not None
