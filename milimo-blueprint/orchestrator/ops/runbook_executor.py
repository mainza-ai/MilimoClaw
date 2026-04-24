"""
Ops Claw — Runbook Executor

Automated remediation procedures for common incidents.
Matches incident analysis results to predefined runbooks and
executes remediation steps.

Usage:
    executor = RunbookExecutor(operational_log, dispatcher)
    result = executor.execute_runbook("restart_service", context)
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .ops_init import OpsOperationalLog, OpsLogEntry

logger = logging.getLogger("milimo.ops.runbook_executor")


@dataclass
class RunbookResult:
    """Result of a runbook execution."""

    runbook_name: str
    success: bool
    steps_executed: int = 0
    steps_failed: int = 0
    output: str = ""
    executed_at: str = ""
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not self.executed_at:
            self.executed_at = datetime.now(timezone.utc).isoformat()


class RunbookExecutor:
    """
    Automated remediation executor for the Ops Claw.

    Executes predefined runbooks based on incident analysis results.
    Each runbook is a sequence of steps that can include shell commands,
    service restarts, cache clearing, and notifications.
    """

    def __init__(
        self,
        operational_log: OpsOperationalLog,
        dispatcher: Any | None = None,
    ) -> None:
        self._log = operational_log
        self._dispatcher = dispatcher
        self._execution_history: list[RunbookResult] = []

        # Predefined runbooks
        self._runbooks: dict[str, dict[str, Any]] = {
            "restart_service": {
                "name": "Restart Service",
                "description": "Restart a failing sandbox",
                "steps": [
                    {"action": "log", "message": "Initiating sandbox restart"},
                    {
                        "action": "shell",
                        "command": "nemoclaw list 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "nemoclaw $(nemoclaw list 2>/dev/null | head -1 | awk '{print $1}') rebuild 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "wait", "seconds": 10},
                    {
                        "action": "shell",
                        "command": "nemoclaw list 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "log", "message": "Sandbox restart complete"},
                ],
            },
            "clear_cache": {
                "name": "Clear Cache",
                "description": "Clear application caches and temporary files",
                "steps": [
                    {"action": "log", "message": "Initiating cache clear"},
                    {
                        "action": "shell",
                        "command": "du -sh /tmp 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "find /tmp -type f -mtime +1 -delete 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "df -h / 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "log", "message": "Cache clear complete"},
                ],
            },
            "scale_up": {
                "name": "Scale Up",
                "description": "Scale up sandbox capacity",
                "steps": [
                    {"action": "log", "message": "Initiating scale up"},
                    {
                        "action": "shell",
                        "command": "nemoclaw list 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "nemoclaw build-claw rebuild 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "wait", "seconds": 15},
                    {
                        "action": "shell",
                        "command": "nemoclaw list 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "log", "message": "Scale up complete"},
                ],
            },
            "rollback": {
                "name": "Rollback Deployment",
                "description": "Rollback to the previous deployment",
                "steps": [
                    {"action": "log", "message": "Initiating rollback"},
                    {
                        "action": "shell",
                        "command": "git log --oneline -5 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "log",
                        "message": "Rollback requires manual confirmation — queued for review",
                    },
                ],
            },
            "investigate": {
                "name": "Investigate",
                "description": "Gather diagnostic information for investigation",
                "steps": [
                    {"action": "log", "message": "Starting investigation"},
                    {"action": "shell", "command": "uptime", "capture": True},
                    {
                        "action": "shell",
                        "command": "free -m 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "df -h 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "nemoclaw list 2>/dev/null || true",
                        "capture": True,
                    },
                    {
                        "action": "shell",
                        "command": "tail -100 /var/log/syslog 2>/dev/null || true",
                        "capture": True,
                    },
                    {"action": "log", "message": "Investigation data collected"},
                ],
            },
            "notify_team": {
                "name": "Notify Team",
                "description": "Send notification to the team",
                "steps": [
                    {"action": "log", "message": "Team notification queued for review"},
                ],
            },
        }

    def execute_runbook(
        self,
        runbook_name: str,
        context: dict[str, Any] | None = None,
    ) -> RunbookResult:
        """
        Execute a runbook by name.

        Args:
            runbook_name: Name of the runbook to execute.
            context: Optional context dict with alert info.

        Returns:
            RunbookResult with execution details.
        """
        runbook = self._runbooks.get(runbook_name)
        if not runbook:
            logger.warning("Unknown runbook: %s", runbook_name)
            result = RunbookResult(
                runbook_name=runbook_name,
                success=False,
                output=f"Unknown runbook: {runbook_name}",
            )
            self._execution_history.append(result)
            return result

        logger.info("Executing runbook: %s — %s", runbook_name, runbook["description"])

        start_time = time.monotonic()
        steps_executed = 0
        steps_failed = 0
        output_parts: list[str] = []

        for step in runbook["steps"]:
            action = step.get("action", "")
            try:
                if action == "shell":
                    cmd_output = self._run_shell_command(
                        step.get("command", ""), step.get("capture", False)
                    )
                    output_parts.append(f"[{action}] {cmd_output}")
                elif action == "wait":
                    time.sleep(step.get("seconds", 1))
                    output_parts.append(f"[{action}] waited {step.get('seconds', 1)}s")
                elif action == "log":
                    msg = step.get("message", "")
                    output_parts.append(f"[{action}] {msg}")
                    logger.info("Runbook step: %s", msg)
                elif action == "notify":
                    output_parts.append(f"[{action}] notification queued")
                else:
                    output_parts.append(f"[{action}] unknown action")

                steps_executed += 1

            except Exception as e:
                steps_failed += 1
                output_parts.append(f"[{action}] ERROR: {e}")
                logger.error("Runbook step failed: %s — %s", action, e)

        duration = time.monotonic() - start_time
        success = steps_failed == 0
        output = "\n".join(output_parts)

        result = RunbookResult(
            runbook_name=runbook_name,
            success=success,
            steps_executed=steps_executed,
            steps_failed=steps_failed,
            output=output,
            duration_seconds=round(duration, 2),
        )

        self._execution_history.append(result)

        self._log.append(
            OpsLogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                action_type="runbook_executed",
                entity_id=runbook_name,
                outcome="success" if success else "partial",
                details={
                    "steps_executed": steps_executed,
                    "steps_failed": steps_failed,
                    "duration_seconds": result.duration_seconds,
                    "context": context,
                },
            )
        )

        logger.info(
            "Runbook %s complete: %d steps, %d failed, %.1fs",
            runbook_name,
            steps_executed,
            steps_failed,
            duration,
        )

        return result

    def get_available_runbooks(self) -> list[dict[str, Any]]:
        """Return list of available runbooks."""
        return [
            {
                "name": name,
                "description": rb["description"],
                "steps_count": len(rb["steps"]),
            }
            for name, rb in self._runbooks.items()
        ]

    def get_execution_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent execution results."""
        return [
            {
                "runbook_name": r.runbook_name,
                "success": r.success,
                "steps_executed": r.steps_executed,
                "steps_failed": r.steps_failed,
                "duration_seconds": r.duration_seconds,
                "executed_at": r.executed_at,
            }
            for r in self._execution_history[-limit:]
        ]

    def register_runbook(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
    ) -> None:
        """Register a custom runbook."""
        self._runbooks[name] = {
            "name": name,
            "description": description,
            "steps": steps,
        }
        logger.info("Registered custom runbook: %s", name)

    @staticmethod
    def _run_shell_command(command: str, capture: bool = False) -> str:
        """Execute a shell command and return output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if capture:
                output = result.stdout.strip() or result.stderr.strip()
                return output[:1000]  # Truncate long output
            return f"exit_code={result.returncode}"
        except subprocess.TimeoutExpired:
            return "ERROR: Command timed out after 30s"
        except Exception as e:
            return f"ERROR: {e}"

    def handle_incident_with_remediation(
        self, alert: dict[str, Any], analysis: Any
    ) -> RunbookResult:
        """
        Analyze an incident and automatically execute the matched runbook.

        This is the main entry point for the webhook server to call.

        Args:
            alert: The alert dict from the webhook.
            analysis: IncidentAnalysis result from IncidentAnalyzer.

        Returns:
            RunbookResult from the executed runbook.
        """
        runbook_name = (
            analysis.runbook_match
            if hasattr(analysis, "runbook_match")
            else "investigate"
        )

        # Auto-execute only for non-destructive runbooks
        auto_execute_runbooks = {"restart_service", "clear_cache", "investigate"}

        if runbook_name in auto_execute_runbooks:
            logger.info(
                "Auto-executing runbook %s for alert %s (severity: %s)",
                runbook_name,
                alert.get("alert_id"),
                alert.get("severity"),
            )
            return self.execute_runbook(runbook_name, context=alert)
        else:
            logger.info(
                "Runbook %s requires manual approval for alert %s — queuing for review",
                runbook_name,
                alert.get("alert_id"),
            )
            # Queue for War Room review
            if self._dispatcher and hasattr(self._dispatcher, "_operational_log"):
                self._dispatcher._operational_log.append(
                    OpsLogEntry(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        action_type="runbook_queued_for_review",
                        entity_id=alert.get("alert_id", "unknown"),
                        outcome="success",
                        details={
                            "runbook": runbook_name,
                            "severity": alert.get("severity"),
                            "alert_source": alert.get("source"),
                        },
                    )
                )
            return RunbookResult(
                runbook_name=runbook_name,
                success=False,
                output=f"Runbook {runbook_name} queued for manual approval",
            )
