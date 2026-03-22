#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — Documentation Maintainer

Maintains project documentation autonomously.

Changelog: updated on every merged PR (AUTO — no approval)
API docs: updated on PRs touching API routes (REVIEW)
Weekly devlog: generated Friday 17:00, sent to Content Claw
All documentation inference logs data_type.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .approval_handler import BuildApprovalHandler
    from .build_init import BuildFilesystemInit, BuildOperationalLog
    from .pr_manager import PRRecord
    from .signal_dispatcher import BuildSignalDispatcher

logger = logging.getLogger("milimo.build")


class DocMaintainer:
    """
    Maintains project documentation autonomously.

    Changelog: updated on every merged PR (AUTO — no approval)
    API docs: updated on PRs touching API routes (REVIEW)
    Weekly devlog: generated Friday 17:00, sent to Content Claw
    All documentation inference logs data_type.
    """

    def __init__(
        self,
        fs: BuildFilesystemInit,
        inference_client: Any,
        dispatcher: BuildSignalDispatcher,
        approval_handler: BuildApprovalHandler,
        operational_log: BuildOperationalLog,
    ):
        self._fs = fs
        self._inference = inference_client
        self._dispatcher = dispatcher
        self._approval = approval_handler
        self._log = operational_log

    def update_changelog(self, merged_pr: PRRecord) -> None:
        prompt = f"""Generate a changelog entry for this merged PR.

PR Title: {merged_pr.title}
PR Description: {merged_pr.description}

Output a single-line changelog entry in the format:
- [category] Brief description (#pr_number)

Category should be one of: fix, feat, refactor, docs, test, chore
"""

        try:
            entry = self._inference.complete(
                prompt=prompt,
                data_type="changelog_generation",
                max_tokens=100,
            ).strip()
        except Exception as e:
            logger.warning("Changelog generation failed: %s", e)
            entry = f"- fix: {merged_pr.title} (#{merged_pr.github_pr_number})"

        if not entry.startswith("-"):
            entry = f"- {entry}"

        changelog_path = self._fs.get_changelog_path()
        if changelog_path.exists():
            content = changelog_path.read_text()
        else:
            content = "# Changelog\n\nAll notable changes documented here.\n"

        date_header = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        lines = content.split("\n")

        insert_index = 2
        for i, line in enumerate(lines):
            if line.startswith("## ") and date_header in line:
                insert_index = i + 1
                break
            elif line.startswith("## "):
                insert_index = i

        if f"## {date_header}" not in content:
            new_section = f"\n## {date_header}\n\n{entry}\n"
            lines.insert(insert_index, new_section)
        else:
            for i, line in enumerate(lines):
                if f"## {date_header}" in line:
                    lines.insert(i + 2, entry)
                    break

        changelog_path.write_text("\n".join(lines))

        self._approval.log_auto(
            "changelog_updated",
            merged_pr.pr_id,
            {"entry": entry[:50]},
        )

        self._log.append(self._create_log_entry(
            "changelog_updated",
            merged_pr.pr_id,
            "success",
            {"entry": entry[:50]},
        ))

    def update_api_docs(self, merged_pr: PRRecord) -> None:
        files_changed = []
        if isinstance(merged_pr.files_changed, list):
            files_changed = merged_pr.files_changed

        if not self._detect_api_routes_changed(files_changed):
            logger.debug("No API routes changed, skipping API docs update")
            return

        prompt = f"""Generate API documentation for the changes in this PR.

PR Title: {merged_pr.title}
PR Description: {merged_pr.description}

Output documentation in Markdown format:
- Endpoint path
- HTTP method
- Request parameters
- Response format
"""

        try:
            docs = self._inference.complete(
                prompt=prompt,
                data_type="api_documentation_generation",
                max_tokens=1000,
            )
        except Exception as e:
            logger.warning("API docs generation failed: %s", e)
            docs = f"## {merged_pr.title}\n\nSee PR #{merged_pr.github_pr_number} for details."

        docs_filename = f"api-{merged_pr.pr_id}.md"
        docs_path = self._fs.get_api_docs_dir() / docs_filename
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(docs)

        self._approval.queue_security_pr_review(
            vuln_id=f"api-docs-{merged_pr.pr_id}",
            package="documentation",
            severity="info",
            fix_description=f"API documentation update for {merged_pr.title}",
        )

        self._log.append(self._create_log_entry(
            "api_docs_updated",
            merged_pr.pr_id,
            "review_queued",
            {"docs_file": docs_filename},
        ))

    def generate_weekly_devlog(self) -> str:
        week_of = datetime.now(timezone.utc).strftime("%Y-W%W")
        devlog_filename = f"week-{week_of}.md"
        devlog_path = self._fs.get_devlog_dir() / devlog_filename
        devlog_path.parent.mkdir(parents=True, exist_ok=True)

        summary = self._dispatcher.get_accumulated_shipping_summary()

        prompt = f"""Generate a weekly development log for a build-in-public audience.

Week of: {week_of}

Activity summary:
- PRs merged: {summary.get('prs_merged', 0)}
- Issues resolved: {summary.get('issues_resolved', 0)}
- Features shipped: {', '.join(summary.get('features_shipped', [])) or 'None'}
- Notable changes: {', '.join(summary.get('notable_changes', [])[:5]) or 'None'}

Write a friendly, engaging devlog entry that:
1. Summarizes the week's progress
2. Highlights key achievements
3. Mentions any interesting technical challenges
4. Thanks the community

Output in Markdown format, suitable for a blog post.
"""

        try:
            devlog_content = self._inference.complete(
                prompt=prompt,
                data_type="devlog_draft_generation",
                max_tokens=1500,
            )
        except Exception as e:
            logger.warning("Devlog generation failed: %s", e)
            devlog_content = f"""# Weekly Devlog — {week_of}

## Summary

This week we shipped {summary.get('prs_merged', 0)} PRs and resolved {summary.get('issues_resolved', 0)} issues.

## What's New

{chr(10).join(f'- {c}' for c in summary.get('notable_changes', [])[:5]) or '- Various improvements'}

---

*Generated by Build Claw*
"""

        devlog_path.write_text(devlog_content)

        self._dispatcher.send_shipping_summary(
            week_of=week_of,
            prs_merged=summary.get('prs_merged', 0),
            issues_resolved=summary.get('issues_resolved', 0),
            features_shipped=summary.get('features_shipped', []),
            notable_changes=summary.get('notable_changes', []),
        )

        self._log.append(self._create_log_entry(
            "devlog_generated",
            week_of,
            "success",
            {"pr_count": summary.get('prs_merged', 0)},
        ))

        return devlog_content

    def _detect_api_routes_changed(self, files_changed: list[str]) -> bool:
        api_indicators = [
            "api/",
            "routes/",
            "handlers/",
            "endpoints/",
            "router",
            "endpoint",
            "route",
        ]

        for file_path in files_changed:
            file_lower = file_path.lower()
            for indicator in api_indicators:
                if indicator in file_lower:
                    return True

        return False

    def _create_log_entry(
        self,
        action_type: str,
        entity_id: str,
        outcome: str,
        details: dict[str, Any],
    ):
        from .build_init import BuildLogEntry

        return BuildLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action_type=action_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
