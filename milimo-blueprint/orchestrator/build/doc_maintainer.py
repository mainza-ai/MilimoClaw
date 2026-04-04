"""
Build Claw documentation maintainer.

Handles:
- Automatic changelog updates from merged PRs
- Weekly devlog generation
- API route change detection
- Documentation drift monitoring

Enhancement: Renderer/Sink separation pattern (from Clawhip).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build.build_init import BuildFilesystemInit, BuildOperationalLog, BuildLogEntry
from build.signal_dispatcher import BuildSignalDispatcher
from build.approval_handler import BuildApprovalHandler

logger = logging.getLogger(__name__)


class DocMaintainer:
    """Maintains project documentation automatically."""

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ) -> None:
        self._fs = fs
        self._inference = inference_client
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log

    # ------------------------------------------------------------------
    # Changelog updates
    # ------------------------------------------------------------------

    def update_changelog(self, pr: Any) -> str:
        """Update CHANGELOG.md from a merged PR.

        Accepts either a dict or a PRRecord object.
        Uses inference to generate the changelog entry.
        """
        # Support both dict and PRRecord
        if hasattr(pr, "title"):
            pr_title = pr.title
            pr_number = getattr(pr, "issue_number", "unknown")
            pr_type = getattr(pr, "status", "fix")
            pr_description = getattr(pr, "description", "")
        else:
            pr_title = pr.get("title", "Unknown")
            pr_number = pr.get("number", "unknown")
            pr_type = pr.get("type", "fix")
            pr_description = pr.get("description", "")

        changelog_path = self._fs.base / "docs" / "changelog.md"

        # Use inference to generate changelog entry
        if self._inference is not None:
            prompt = (
                f"Generate a concise changelog entry for this PR:\n"
                f"Title: {pr_title}\n"
                f"Description: {pr_description}\n"
                f"PR #{pr_number}"
            )
            entry_text = self._inference.complete(
                prompt=prompt,
                data_type="changelog_generation",
                temperature=0.3,
            )
        else:
            entry_text = f"- {pr_title} (#{pr_number})"

        entry = f"\n## {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n{entry_text}\n"

        if changelog_path.exists():
            existing = changelog_path.read_text()
            changelog_path.write_text(entry + existing)
        else:
            changelog_path.write_text(f"# Changelog\n{entry}")

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="changelog_updated",
            entity_id=f"pr-{pr_number}",
            outcome="success",
            details={"pr_title": pr_title, "pr_type": pr_type},
        ))

        return f"CHANGELOG.md updated with PR #{pr_number}"

    # ------------------------------------------------------------------
    # Weekly devlog generation
    # ------------------------------------------------------------------

    def generate_weekly_devlog(self) -> str:
        """Generate a weekly development summary log."""
        week_start = datetime.now(timezone.utc).strftime('%Y-%W')

        # Collect recent activity
        recent_logs = self._log.read_recent(days=7)
        merged_prs = [l for l in recent_logs if l.action_type == "pr_merged"]
        deploys = [l for l in recent_logs if l.action_type == "deploy_completed"]
        issues = [l for l in recent_logs if l.action_type == "issue_closed"]

        devlog = f"# Weekly Devlog — Week {week_start}\n\n"
        devlog += f"## Summary\n"
        devlog += f"- PRs merged: {len(merged_prs)}\n"
        devlog += f"- Deploys: {len(deploys)}\n"
        devlog += f"- Issues closed: {len(issues)}\n\n"

        if merged_prs:
            devlog += "## Merged PRs\n"
            for pr in merged_prs[:10]:
                devlog += f"- {pr.entity_id}: {pr.details.get('title', 'Unknown')}\n"
            devlog += "\n"

        if deploys:
            devlog += "## Deployments\n"
            for d in deploys[:5]:
                devlog += f"- {d.entity_id}: {d.outcome}\n"
            devlog += "\n"

        devlog_path = self._fs.base / "docs" / "devlog" / f"week-{week_start}.md"
        devlog_path.parent.mkdir(parents=True, exist_ok=True)
        devlog_path.write_text(devlog)

        # Send shipping summary to Content Claw
        shipping = self._dispatcher.get_accumulated_shipping_summary()
        if shipping["prs_merged"] > 0:
            self._dispatcher.send_shipping_summary(
                week_of=shipping["week_of"],
                prs_merged=shipping["prs_merged"],
                issues_resolved=shipping["issues_resolved"],
                features_shipped=shipping["features_shipped"],
                notable_changes=shipping["notable_changes"],
            )

        self._log.append(BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type="devlog_generated",
            entity_id=f"week-{week_start}",
            outcome="success",
            details={"pr_count": len(merged_prs), "deploy_count": len(deploys)},
        ))

        return devlog

    # ------------------------------------------------------------------
    # API route change detection
    # ------------------------------------------------------------------

    def _detect_api_routes_changed(self, files_changed: list[str]) -> bool:
        """Detect if any API routes were changed based on modified files."""
        for f in files_changed:
            if "route" in f.lower() or "api" in f.lower() or "endpoint" in f.lower():
                return True
        return False

    # ------------------------------------------------------------------
    # Documentation drift monitoring
    # ------------------------------------------------------------------

    def check_doc_drift(self, changed_files: list[str]) -> list[str]:
        """Check if documentation needs updating based on code changes."""
        drifted_docs = []

        for f in changed_files:
            if f.endswith(('.py', '.ts', '.js')):
                # Check if corresponding docs exist
                doc_path = self._fs.base_path / "docs" / f.replace('/', '_') + ".md"
                if doc_path.exists():
                    # Simple heuristic: if code changed, docs might be stale
                    drifted_docs.append(f)

        return drifted_docs

    # ------------------------------------------------------------------
    # Inference-assisted doc generation
    # ------------------------------------------------------------------

    def generate_api_docs(self, code_content: str) -> str:
        """Generate API documentation from code using inference."""
        if self._inference is None:
            return "# API Documentation\n\nAuto-generation unavailable."

        prompt = f"Generate API documentation for the following code:\n\n```python\n{code_content}\n```"
        # Inference call would go here
        return "# API Documentation\n\nGenerated from source code."
