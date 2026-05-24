# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Tests for T1.1, T1.3, T2.5, T2.6 — MilimoClaw status and evolution query improvements.

Covers:
  T1.1: _query_evolution_status uses claw_base(role)/sandbox/tools/registry.json
  T1.3: handle_milimo_status aggregates launcher + health + evolution + pending
  T2.5: handle_claw_status includes metadata (interpretation, diagnostic_note)
  T2.6: handle_launcher_status includes diagnostic_notes for stale/unknown states
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SANDBOX_ROOT = Path(tempfile.mkdtemp())


def _make_heartbeat(role: str, seconds_ago: float = 10, pid: int = 12345) -> dict:
    ts = (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()
    return {"timestamp": ts, "pid": pid, "uptime_seconds": 3600}


class TestT1QueryEvolutionStatus(unittest.TestCase):
    """T1.1: _query_evolution_status reads claw_base/sandbox/tools/registry.json."""

    def setUp(self):
        self.tmp = SANDBOX_ROOT / "t1"
        if self.tmp.exists():
            import shutil

            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.tmp / "state" / "evolution"
        self.state_dir.mkdir(parents=True)
        self.summary = self.state_dir / "summary.json"

    def _mock_claw_base(self, role):
        return self.tmp / "claws" / role

    def _write_summary(self, data: dict) -> None:
        self.summary.write_text(json.dumps(data))

    def _write_registry(self, role: str, tools: dict) -> None:
        claw_dir = self.tmp / "claws" / role
        registry = claw_dir / "sandbox" / "tools"
        registry.mkdir(parents=True)
        (registry / "registry.json").write_text(json.dumps({"tools": tools}))

    def test_never_run_when_no_summary(self):
        """When summary.json doesn't exist, status must be 'never_run'."""
        self._write_summary({})
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "content")
            self.assertEqual(result["status"], "never_run")
            self.assertFalse(result["evolution_ever_run"])

    def test_success_when_last_stage_is_deploy(self):
        """When last_stage is 'deploy', status must be 'success'."""
        self._write_summary(
            {
                "by_role": {
                    "content": {
                        "last_run": "2026-04-28T10:00:00Z",
                        "last_stage": "deploy",
                        "tools_deployed": 3,
                    }
                }
            }
        )
        self._write_registry("content", {"tool1": {}, "tool2": {}})
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "content")
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["evolution_ever_run"])
            self.assertEqual(result["tools_deployed"], 3)
            self.assertEqual(result["tool_count"], 2)

    def test_error_when_last_stage_is_error(self):
        """When last_stage is 'error', status must be 'error'."""
        self._write_summary(
            {
                "by_role": {
                    "ops": {
                        "last_run": "2026-04-28T10:00:00Z",
                        "last_stage": "error",
                        "last_skipped_reason": None,
                    }
                }
            }
        )
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "ops")
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["last_stage_reached"], "error")

    def test_incomplete_when_last_stage_is_build(self):
        """When last_stage is 'build' (not deploy/error), status must be 'incomplete'."""
        self._write_summary(
            {
                "by_role": {
                    "analytics": {
                        "last_run": "2026-04-28T10:00:00Z",
                        "last_stage": "build",
                    }
                }
            }
        )
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "analytics")
            self.assertEqual(result["status"], "incomplete")

    def test_registry_path_uses_claw_base_sandbox_tools(self):
        """Registry path must be: claw_base(role)/sandbox/tools/registry.json."""
        self._write_summary({"by_role": {}})
        self._write_registry("finance", {"tool_a": {}, "tool_b": {}, "tool_c": {}})
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "finance")
            self.assertEqual(result["tool_count"], 3)

    def test_diagnostic_note_when_never_run(self):
        """diagnostic_note must explain that evolution has never run."""
        self._write_summary({})
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "content")
            self.assertIn("never run", result["diagnostic_note"].lower())

    def test_diagnostic_note_shows_last_stage(self):
        """diagnostic_note must include last_stage and last_run when available."""
        self._write_summary(
            {
                "by_role": {
                    "content": {
                        "last_run": "2026-04-28T10:00:00Z",
                        "last_stage": "deploy",
                    }
                }
            }
        )
        with self._patch_sandbox_paths():
            from orchestrator.bridge_cli import _query_evolution_status

            result = _query_evolution_status("test-squad", "content")
            self.assertIn("deploy", result["diagnostic_note"])
            self.assertIn("2026-04-28", result["diagnostic_note"])

    def _patch_sandbox_paths(self):
        root = self.tmp

        def fake_mesh_dir():
            return root / "mesh"

        def fake_health_dir(squad_id="default"):
            return root / "health"

        def fake_claw_base(role):
            return root / "claws" / role

        def fake_state_dir():
            return root / "state"

        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(
            patch.multiple(
                "orchestrator.milimo_paths",
                mesh_dir=fake_mesh_dir,
                health_dir=fake_health_dir,
                claw_base=fake_claw_base,
                state_dir=fake_state_dir,
            )
        )
        stack.enter_context(
            patch.multiple(
                "orchestrator.bridge_cli",
                milimo_mesh_dir=fake_mesh_dir,
                health_dir=fake_health_dir,
                claw_base=fake_claw_base,
                state_dir=fake_state_dir,
            )
        )
        return stack


class TestT2LauncherStatusDiagnostics(unittest.TestCase):
    """T2.6: handle_launcher_status includes diagnostic_note for stale/unknown claws."""

    def setUp(self):
        self.tmp = SANDBOX_ROOT / "t2"
        if self.tmp.exists():
            import shutil

            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.mesh_dir = self.tmp / "mesh"
        self.mesh_dir.mkdir(parents=True)
        self.heartbeats_dir = self.mesh_dir / "heartbeats"
        self.heartbeats_dir.mkdir()
        (self.mesh_dir / "launcher.pid").write_text("99999\n")

    def _write_heartbeat(self, role: str, data: dict) -> None:
        (self.heartbeats_dir / f"{role}.json").write_text(json.dumps(data))

    def _patch_paths(self):
        root = self.tmp

        def fake_mesh_dir():
            return root / "mesh"

        def fake_kill(pid, sig):
            if pid in (88888, 99999):
                return
            raise ProcessLookupError()

        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch("os.kill", fake_kill))
        stack.enter_context(patch("orchestrator.milimo_paths.mesh_dir", fake_mesh_dir))
        stack.enter_context(
            patch("orchestrator.bridge_cli.milimo_mesh_dir", fake_mesh_dir)
        )
        return stack

    def test_stale_heartbeat_gets_diagnostic_note(self):
        """Claw with heartbeat >90s old must have 'stale' status + diagnostic_note."""
        self._write_heartbeat("content", _make_heartbeat("content", seconds_ago=120))
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_launcher_status

            result = handle_launcher_status({})
            claw = result["claws"]["content"]
            self.assertEqual(claw["status"], "stale")
            self.assertIn("diagnostic_note", claw)
            self.assertIn("unresponsive", claw["diagnostic_note"].lower())

    def test_no_timestamp_gets_diagnostic_note(self):
        """Claw with heartbeat but no timestamp must have 'unknown' + diagnostic_note."""
        self._write_heartbeat("ops", {"pid": 12345, "uptime_seconds": 100})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_launcher_status

            result = handle_launcher_status({})
            claw = result["claws"]["ops"]
            self.assertEqual(claw["status"], "unknown")
            self.assertIn("diagnostic_note", claw)
            self.assertIn("corrupt", claw["diagnostic_note"].lower())

    def test_parsing_error_gets_diagnostic_note(self):
        """Claw whose heartbeat file fails to parse must have 'unknown' + diagnostic_note."""
        (self.heartbeats_dir / "analytics.json").write_text("not valid json{")
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_launcher_status

            result = handle_launcher_status({})
            claw = result["claws"]["analytics"]
            self.assertEqual(claw["status"], "unknown")
            self.assertIn("diagnostic_note", claw)

    def test_running_heartbeat_has_no_diagnostic_note(self):
        """Fresh heartbeat should NOT have diagnostic_note."""
        self._write_heartbeat("finance", _make_heartbeat("finance", seconds_ago=10))
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_launcher_status

            result = handle_launcher_status({})
            claw = result["claws"]["finance"]
            self.assertEqual(claw["status"], "running")
            self.assertNotIn("diagnostic_note", claw)


class TestT2ClawStatusMetadata(unittest.TestCase):
    """T2.5: handle_claw_status includes interpretation and diagnostic_note."""

    def setUp(self):
        self.tmp = SANDBOX_ROOT / "t2_5"
        if self.tmp.exists():
            import shutil

            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.health_dir = self.tmp / "health"
        self.health_dir.mkdir()
        self.mesh_dir = self.tmp / "mesh"
        self.mesh_dir.mkdir()
        self.inbox_dir = self.mesh_dir / "inbox" / "content"
        self.inbox_dir.mkdir(parents=True)
        self.state_dir = self.tmp / "state" / "evolution"
        self.state_dir.mkdir(parents=True)

    def _write_health(self, data: dict) -> None:
        (self.health_dir / "health.json").write_text(json.dumps({"claws": data}))

    def _write_summary(self, data: dict) -> None:
        (self.state_dir / "summary.json").write_text(json.dumps(data))

    def _patch_paths(self):
        root = self.tmp

        def fake_claw_base(role):
            return root / "claws" / role

        def fake_health_dir(squad_id="default"):
            return root / "health"

        def fake_mesh_dir():
            return root / "mesh"

        def fake_state_dir():
            return root / "state"

        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(
            patch.multiple(
                "orchestrator.milimo_paths",
                claw_base=fake_claw_base,
                health_dir=fake_health_dir,
                mesh_dir=fake_mesh_dir,
                state_dir=fake_state_dir,
            )
        )
        stack.enter_context(
            patch.multiple(
                "orchestrator.bridge_cli",
                claw_base=fake_claw_base,
                health_dir=fake_health_dir,
                milimo_mesh_dir=fake_mesh_dir,
                state_dir=fake_state_dir,
            )
        )
        return stack

    def test_zero_tools_gives_interpretation(self):
        """When tool_count is 0, tool_count_interpretation must explain why."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        (claw_dir / "sandbox" / "tools").mkdir(parents=True)
        (claw_dir / "sandbox" / "tools" / "registry.json").write_text(
            json.dumps({"tools": {}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("tool_count_interpretation", result)
            self.assertIn("0 tools", result["tool_count_interpretation"])

    def test_has_tools_gives_interpretation(self):
        """When tool_count > 0, tool_count_interpretation must describe the tools."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        reg_dir = claw_dir / "sandbox" / "tools"
        reg_dir.mkdir(parents=True)
        (reg_dir / "registry.json").write_text(
            json.dumps({"tools": {"tone_classifier": {}, "engagement_scorer": {}}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("tool_count_interpretation", result)
            self.assertEqual(result["tool_count"], 2)
            self.assertIn("2 tool(s)", result["tool_count_interpretation"])

    def test_no_health_data_interpretation(self):
        """When health status is 'no_health_data', health_interpretation must explain."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        (claw_dir / "sandbox" / "tools").mkdir(parents=True)
        (claw_dir / "sandbox" / "tools" / "registry.json").write_text(
            json.dumps({"tools": {}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("health_interpretation", result)
            self.assertIn("no health data", result["health_interpretation"].lower())

    def test_evolution_status_field_present(self):
        """Result must include evolution_status field."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        (claw_dir / "sandbox" / "tools").mkdir(parents=True)
        (claw_dir / "sandbox" / "tools" / "registry.json").write_text(
            json.dumps({"tools": {}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("evolution_status", result)
            self.assertEqual(result["evolution_status"], "never_run")

    def test_evolution_ever_run_field_present(self):
        """Result must include evolution_ever_run field."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        (claw_dir / "sandbox" / "tools").mkdir(parents=True)
        (claw_dir / "sandbox" / "tools" / "registry.json").write_text(
            json.dumps({"tools": {}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("evolution_ever_run", result)

    def test_diagnostic_note_from_evolution(self):
        """diagnostic_note must be present from evolution status."""
        self._write_health({})
        self._write_summary({})
        claw_dir = self.tmp / "claws" / "content"
        claw_dir.mkdir(parents=True)
        (claw_dir / "sandbox" / "tools").mkdir(parents=True)
        (claw_dir / "sandbox" / "tools" / "registry.json").write_text(
            json.dumps({"tools": {}})
        )
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_claw_status

            result = handle_claw_status({"role": "content"})
            self.assertIn("diagnostic_note", result)
            self.assertIn("never run", result["diagnostic_note"].lower())


class TestT1MilimoStatusAggregates(unittest.TestCase):
    """T1.3: handle_milimo_status aggregates launcher + health + evolution + pending."""

    def setUp(self):
        self.tmp = SANDBOX_ROOT / "t1_3"
        if self.tmp.exists():
            import shutil

            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.state_dir = self.tmp / "state" / "evolution"
        self.state_dir.mkdir(parents=True)
        self.health_dir = self.tmp / "health"
        self.health_dir.mkdir()
        self.mesh_dir = self.tmp / "mesh"
        self.mesh_dir.mkdir()
        self.inbox_dir = self.mesh_dir / "inbox"
        self.heartbeats_dir = self.mesh_dir / "heartbeats"
        self.heartbeats_dir.mkdir()
        (self.mesh_dir / "launcher.pid").write_text("88888\n")
        self._write_heartbeat("content", _make_heartbeat("content", seconds_ago=5))
        self._write_heartbeat("ops", _make_heartbeat("ops", seconds_ago=5))

    def _write_heartbeat(self, role: str, data: dict) -> None:
        (self.heartbeats_dir / f"{role}.json").write_text(json.dumps(data))

    def _write_health(self, data: dict) -> None:
        (self.health_dir / "health.json").write_text(json.dumps({"claws": data}))

    def _write_summary(self, data: dict) -> None:
        (self.state_dir / "summary.json").write_text(json.dumps(data))

    def _write_pending(self, role: str, count: int) -> None:
        inbox = self.inbox_dir / role
        inbox.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            (inbox / f"msg_{i}.json").write_text(
                json.dumps({"message_id": f"msg_{i}", "sender_role": "assistant"})
            )

    def _patch_paths(self):
        root = self.tmp

        def fake_mesh_dir():
            return root / "mesh"

        def fake_health_dir(squad_id="default"):
            return root / "health"

        def fake_claw_base(role):
            return root / "claws" / role

        def fake_state_dir():
            return root / "state"

        def fake_kill(pid, sig):
            if pid in (88888, 99999):
                return
            raise ProcessLookupError()

        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch("os.kill", fake_kill))
        stack.enter_context(
            patch.multiple(
                "orchestrator.milimo_paths",
                mesh_dir=fake_mesh_dir,
                health_dir=fake_health_dir,
                claw_base=fake_claw_base,
                state_dir=fake_state_dir,
            )
        )
        stack.enter_context(
            patch.multiple(
                "orchestrator.bridge_cli",
                milimo_mesh_dir=fake_mesh_dir,
                health_dir=fake_health_dir,
                claw_base=fake_claw_base,
                state_dir=fake_state_dir,
            )
        )
        return stack

    def test_returns_all_six_claws(self):
        """Result must include all 6 claw roles."""
        self._write_health({})
        self._write_summary({})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertEqual(
                set(result["claws"].keys()),
                {"content", "ops", "analytics", "finance", "build", "assistant"},
            )

    def test_evolution_never_run_diagnostic_note(self):
        """When no evolution has ever run, diagnostic_note must explain."""
        self._write_health({})
        self._write_summary({})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertFalse(result["evolution_ever_run"])
            self.assertIn("diagnostic_note", result)
            self.assertIn("never run", result["diagnostic_note"].lower())

    def test_evolution_ever_run_true_when_summary_exists(self):
        """evolution_ever_run must be True when summary.json has by_role data."""
        self._write_summary({"by_role": {"content": {"last_stage": "deploy"}}})
        self._write_health({})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertTrue(result["evolution_ever_run"])
            self.assertIsNone(result.get("diagnostic_note"))

    def test_pending_messages_counted(self):
        """pending_messages must reflect actual .json files in inbox."""
        self._write_health({})
        self._write_summary({})
        self._write_pending("content", 3)
        self._write_pending("ops", 1)
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertEqual(result["claws"]["content"]["pending_messages"], 3)
            self.assertEqual(result["claws"]["ops"]["pending_messages"], 1)
            self.assertEqual(result["claws"]["finance"]["pending_messages"], 0)

    def test_launcher_status_reflected(self):
        """Launcher running state must be propagated."""
        self._write_health({})
        self._write_summary({})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertTrue(result["launcher_running"])
            self.assertEqual(result["launcher_pid"], 88888)

    def test_evolution_status_per_claw(self):
        """Each claw must have evolution_status derived from summary."""
        self._write_summary(
            {
                "by_role": {
                    "content": {"last_stage": "deploy", "tools_deployed": 2},
                    "ops": {"last_stage": "error"},
                }
            }
        )
        self._write_health({})
        with self._patch_paths():
            from orchestrator.bridge_cli import handle_milimo_status

            result = handle_milimo_status({})
            self.assertEqual(result["claws"]["content"]["evolution_status"], "success")
            self.assertEqual(result["claws"]["ops"]["evolution_status"], "error")
            self.assertEqual(
                result["claws"]["finance"]["evolution_status"], "never_run"
            )


class TestT1MilimoStatusRegistered(unittest.TestCase):
    """Verify milimo_status is registered in COMMAND_HANDLERS."""

    def test_milimo_status_in_handlers(self):
        """milimo_status command must be registered in COMMAND_HANDLERS."""
        from orchestrator.bridge_cli import COMMAND_HANDLERS

        self.assertIn("milimo_status", COMMAND_HANDLERS)


if __name__ == "__main__":
    unittest.main()
