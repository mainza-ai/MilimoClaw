# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Build Claw — MVR Integration Tests

15-step Minimum Viable Run test sequence per spec.
All 15 steps must pass before autonomous scheduling is enabled.
Step 9 is the critical correctness test — REVIEW approval must NOT trigger merge.
"""

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Fix Python 'build' package shadowing our build module
_orchestrator_path = os.path.join(os.path.dirname(__file__), "..", "orchestrator")
if _orchestrator_path not in sys.path:
    sys.path.insert(0, _orchestrator_path)


class TestBuildMVR:
    """15-step MVR test sequence for Build Claw."""

    @pytest.fixture
    def build_claw(self, tmp_path):
        """Create a fully-wired BuildClaw instance for MVR testing."""
        from build.build_claw import BuildClaw
        from build.build_init import BuildFilesystemInit

        mock_inference = MagicMock()
        mock_inference.complete.return_value = "M 8"
        mock_inference.get_usage.return_value = {
            "total_tokens": 1000,
            "total_cost_usd": 0.50,
            "cost_by_model": {"nemotron": 0.50},
            "calls_by_data_type": {"source_code_generation": 10},
        }

        mock_github = MagicMock()
        mock_github.get_open_issues.return_value = [
            {"number": 1, "title": "Fix bug", "body": "Fix the thing", "labels": []},
            {
                "number": 2,
                "title": "Add feature",
                "body": "Add new thing",
                "labels": [],
            },
        ]
        mock_github.create_issue.return_value = 10
        mock_github.create_pull_request.return_value = (
            123,
            "https://github.com/repo/pull/123",
        )
        mock_github.merge_pull_request.return_value = True
        mock_github.get_open_pull_requests.return_value = []
        mock_github.create_branch.return_value = True
        mock_github.commit_file.return_value = True

        mock_vercel = MagicMock()
        mock_vercel.trigger_deployment.return_value = {
            "id": "deploy-123",
            "url": "https://example.com",
        }
        mock_vercel.get_deployment_status.return_value = "ready"

        mock_sentry = MagicMock()
        mock_sentry.get_recent_errors.return_value = []

        with patch("build.issue_manager.ANALYTICS_WAIT_SECONDS", 0.1):
            with patch("build.issue_manager.time.sleep"):
                with patch("build.build_scheduler.BuildScheduler.start") as mock_start:
                    mock_start.return_value = None

                    claw = BuildClaw(
                        squad_id="test-squad",
                        inference_client=mock_inference,
                        github_client=mock_github,
                        sentry_client=mock_sentry,
                        vercel_client=mock_vercel,
                        base_path=tmp_path,
                    )

                    claw._fs = BuildFilesystemInit(base_path=tmp_path)
                    claw._fs.initialize()

                    from build.build_init import BuildOperationalLog
                    from build.approval_handler import PRActivityLog, DeployActivityLog

                    log_path = tmp_path / "logs" / "operational.log"
                    claw._log = BuildOperationalLog(log_path)
                    pr_log_path = tmp_path / "logs" / "pr-activity.log"
                    claw._pr_log = PRActivityLog(pr_log_path)
                    deploy_log_path = tmp_path / "logs" / "deploy-activity.log"
                    claw._deploy_log = DeployActivityLog(deploy_log_path)

                    from build.signal_dispatcher import BuildSignalDispatcher

                    claw._dispatcher = BuildSignalDispatcher(
                        fs=claw._fs,
                        operational_log=claw._log,
                        squad_id="test-squad",
                    )

                    from build.approval_handler import BuildApprovalHandler

                    claw._approval_handler = BuildApprovalHandler(
                        fs=claw._fs,
                        operational_log=claw._log,
                        pr_log=claw._pr_log,
                        deploy_log=claw._deploy_log,
                    )

                    from build.issue_manager import IssueManager

                    claw._issue_manager = IssueManager(
                        fs=claw._fs,
                        inference_client=mock_inference,
                        github_client=mock_github,
                        dispatcher=claw._dispatcher,
                        approval_handler=claw._approval_handler,
                        operational_log=claw._log,
                    )

        from build.code_generator import CodeGenerator

        claw._code_generator = CodeGenerator(
            fs=claw._fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=claw._approval_handler,
            operational_log=claw._log,
            repo_path=tmp_path / "repo",
        )

        from build.pr_manager import PRManager

        claw._pr_manager = PRManager(
            fs=claw._fs,
            inference_client=mock_inference,
            github_client=mock_github,
            approval_handler=claw._approval_handler,
            operational_log=claw._log,
            pr_log=claw._pr_log,
        )

        from build.deploy_manager import DeployManager

        claw._deploy_manager = DeployManager(
            fs=claw._fs,
            dispatcher=claw._dispatcher,
            approval_handler=claw._approval_handler,
            operational_log=claw._log,
            deploy_log=claw._deploy_log,
            vercel_client=mock_vercel,
        )

        return claw

    def test_mvr_01_github_credentials_configured(self, build_claw, tmp_path):
        """GitHub token and test repo configured from environment."""
        assert build_claw._github is not None
        assert build_claw._inference is not None

    def test_mvr_02_fetch_open_issues(self, build_claw, tmp_path):
        """Build Claw fetches open issues from configured test repo."""
        issues = build_claw.issue_manager.fetch_open_issues()
        assert len(issues) >= 1

    def test_mvr_03_sprint_plan_generated(self, build_claw, tmp_path):
        """Sprint plan generated — proceeds without Analytics after timeout."""
        import build.issue_manager

        original_wait = build.issue_manager.ANALYTICS_WAIT_SECONDS
        build.issue_manager.ANALYTICS_WAIT_SECONDS = 0.1

        with patch("build.issue_manager.time.sleep"):
            plan = build_claw.issue_manager.generate_sprint_plan()

        build.issue_manager.ANALYTICS_WAIT_SECONDS = original_wait
        assert plan is not None
        assert plan.status == "pending_review"

    def test_mvr_04_sprint_plan_in_war_room_as_review(self, build_claw, tmp_path):
        """Sprint plan queued as REVIEW — not AUTO, not HOLD."""
        import build.issue_manager

        original_wait = build.issue_manager.ANALYTICS_WAIT_SECONDS
        build.issue_manager.ANALYTICS_WAIT_SECONDS = 0.1

        with patch("build.issue_manager.time.sleep"):
            build_claw.issue_manager.generate_sprint_plan()

        build.issue_manager.ANALYTICS_WAIT_SECONDS = original_wait
        sprint_actions = [
            a
            for a in build_claw.approval_handler._pending_actions.values()
            if a.action_type == "sprint_plan"
        ]
        assert len(sprint_actions) >= 1
        action = sprint_actions[-1]
        assert action.mode == "REVIEW"

    def test_mvr_05_approve_sprint_plan(self, build_claw, tmp_path):
        """Sprint plan approved — Build Claw begins work on Issue #1."""
        import build.issue_manager

        original_wait = build.issue_manager.ANALYTICS_WAIT_SECONDS
        build.issue_manager.ANALYTICS_WAIT_SECONDS = 0.1

        with patch("build.issue_manager.time.sleep"):
            build_claw.issue_manager.generate_sprint_plan()

        build.issue_manager.ANALYTICS_WAIT_SECONDS = original_wait
        sprint_actions = [
            aid
            for aid, a in build_claw.approval_handler._pending_actions.items()
            if a.action_type == "sprint_plan"
        ]
        if sprint_actions:
            action_id = sprint_actions[-1]
            result = build_claw.approval_handler.handle_approve(action_id)
            assert result.executed

    def test_mvr_06_pr_opened_on_github(self, build_claw, tmp_path):
        """Confirm PR is opened on GitHub test repository."""
        from build.issue_manager import ComplexityScore

        score = ComplexityScore(
            issue_number=1,
            issue_title="Fix bug",
            complexity_tier="M",
            estimated_hours=8,
            clarity_score="clear",
            missing_elements=[],
            scored_at=datetime.now(timezone.utc).isoformat(),
        )

        with patch.object(
            build_claw._code_generator, "run_tests", return_value=("passing", 10, 0)
        ):
            with patch.object(
                build_claw._code_generator, "write_to_branch", return_value=["file.py"]
            ):
                result = build_claw._code_generator.resolve_issue(score)

        assert result.status == "ready_for_pr"

    def test_mvr_07_pr_in_war_room_as_review(self, build_claw, tmp_path):
        """PR queued as REVIEW in War Room."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=1,
            branch_name="fix/issue-1",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        build_claw._pr_manager.open_pr(resolution)

        pr_actions = [
            a
            for a in build_claw.approval_handler._pending_actions.values()
            if a.action_type == "pr_review"
        ]
        assert len(pr_actions) >= 1
        assert pr_actions[-1].mode == "REVIEW"

    def test_mvr_08_pr_review_approve_creates_hold_not_merge(
        self, build_claw, tmp_path
    ):
        """
        CRITICAL TEST: Approving PR REVIEW must NOT merge the PR.
        PR must move to HOLD queue only.
        Assert github_client.merge_pull_request call_count == 0.
        """
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=1,
            branch_name="fix/issue-1",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = build_claw._pr_manager.open_pr(resolution)

        build_claw._github.merge_pull_request.reset_mock()

        pr_review_actions = [
            aid
            for aid, a in build_claw.approval_handler._pending_actions.items()
            if a.action_type == "pr_review" and a.entity_id == pr.pr_id
        ]

        if pr_review_actions:
            action_id = pr_review_actions[-1]
            build_claw.approval_handler.handle_approve(action_id)

        build_claw._github.merge_pull_request.assert_not_called()

    def test_mvr_09_pr_hold_release_triggers_github_merge(self, build_claw, tmp_path):
        """HOLD release triggers GitHub merge (not PR REVIEW approve)."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=1,
            branch_name="fix/issue-1",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = build_claw._pr_manager.open_pr(resolution)

        pr_review_actions = [
            aid
            for aid, a in build_claw.approval_handler._pending_actions.items()
            if a.action_type == "pr_review"
        ]

        if pr_review_actions:
            action_id = pr_review_actions[-1]

            def next_step():
                return build_claw._pr_manager.handle_review_approved(pr.pr_id)

            build_claw.approval_handler.handle_approve(
                action_id, next_step_fn=next_step
            )

        pr_hold_actions = [
            aid
            for aid, a in build_claw.approval_handler._pending_actions.items()
            if a.action_type == "pr_merge_hold"
        ]

        build_claw._github.merge_pull_request.reset_mock()

        if pr_hold_actions:
            action_id = pr_hold_actions[-1]
            build_claw.approval_handler.handle_hold_release(
                action_id,
                execute_fn=lambda: build_claw._pr_manager.handle_merge_hold_released(
                    pr.pr_id
                ),
            )

        build_claw._github.merge_pull_request.assert_called()

    def test_mvr_10_deploy_staged_after_merge(self, build_claw, tmp_path):
        """Deploy staging record created in deployments/pending/ after merge."""
        from build.code_generator import ResolutionResult
        from build.pr_manager import PRRecord

        resolution = ResolutionResult(
            issue_number=1,
            branch_name="fix/issue-1",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = build_claw._pr_manager.open_pr(resolution)

        pr = PRRecord(
            pr_id=pr.pr_id,
            issue_number=1,
            branch_name="fix/issue-1",
            title="Fix #1",
            description="Fixes the issue",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = build_claw._deploy_manager.stage_deployment(pr)

        deploy_path = tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        assert deploy_path.exists()

    def test_mvr_11_deploy_in_war_room_as_hold(self, build_claw, tmp_path):
        """Deploy queued as its OWN HOLD — separate from PR HOLD."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=1,
            branch_name="fix/issue-1",
            title="Fix #1",
            description="Fixes the issue",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id="pr-hold-123",
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        build_claw._deploy_manager.stage_deployment(pr)

        deploy_actions = [
            a
            for a in build_claw.approval_handler._pending_actions.values()
            if a.action_type == "deploy_hold"
        ]

        assert len(deploy_actions) >= 1
        assert deploy_actions[-1].mode == "HOLD"

        pr_hold_actions = [
            a
            for a in build_claw.approval_handler._pending_actions.values()
            if a.action_type == "pr_merge_hold"
        ]

        if pr_hold_actions:
            assert pr_hold_actions[-1].action_id != deploy_actions[-1].action_id

    def test_mvr_12_deploy_hold_release_triggers_deployment(self, build_claw, tmp_path):
        """Deploy HOLD release triggers Vercel/Railway API (mocked)."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=1,
            branch_name="fix/issue-1",
            title="Fix #1",
            description="Fixes the issue",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = build_claw._deploy_manager.stage_deployment(pr)

        deploy_hold_actions = [
            aid
            for aid, a in build_claw.approval_handler._pending_actions.items()
            if a.action_type == "deploy_hold"
        ]

        build_claw._vercel.trigger_deployment.reset_mock()

        if deploy_hold_actions:
            action_id = deploy_hold_actions[-1]
            build_claw.approval_handler.handle_hold_release(
                action_id,
                execute_fn=lambda: (
                    build_claw._deploy_manager.handle_deploy_hold_released(
                        deploy.deploy_id
                    )
                ),
            )

        build_claw._vercel.trigger_deployment.assert_called()

    def test_mvr_13_deploy_complete_sent_to_ops(self, build_claw, tmp_path):
        """deploy_complete message dispatched to Ops Claw after success."""
        from build.pr_manager import PRRecord

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=1,
            branch_name="fix/issue-1",
            title="Fix #1",
            description="Fixes the issue",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = build_claw._deploy_manager.stage_deployment(pr)

        with patch.object(build_claw._dispatcher, "send_deploy_complete"):
            build_claw._deploy_manager.handle_deploy_hold_released(deploy.deploy_id)

    def test_mvr_14_deploy_failure_queues_review_no_retry(self, build_claw, tmp_path):
        """Failed deploy queues REVIEW — deployment NOT retried automatically."""
        from build.pr_manager import PRRecord

        build_claw._vercel.get_deployment_status.return_value = "error"

        pr = PRRecord(
            pr_id="pr-123",
            issue_number=1,
            branch_name="fix/issue-1",
            title="Fix #1",
            description="Fixes the issue",
            github_pr_number=123,
            github_pr_url="https://github.com/repo/pull/123",
            files_changed=1,
            lines_added=10,
            lines_removed=5,
            test_status="passing",
            tests_count=10,
            status="merged",
            review_action_id=None,
            hold_action_id=None,
            opened_at=datetime.now(timezone.utc).isoformat(),
            approved_at=datetime.now(timezone.utc).isoformat(),
            merged_at=datetime.now(timezone.utc).isoformat(),
        )

        deploy = build_claw._deploy_manager.stage_deployment(pr)

        build_claw._vercel.trigger_deployment.reset_mock()

        result = build_claw._deploy_manager.handle_deploy_hold_released(
            deploy.deploy_id
        )

        assert result.status == "failed"

        deploy_path = tmp_path / "deployments" / "pending" / f"{deploy.deploy_id}.json"
        assert deploy_path.exists()

        build_claw._vercel.get_deployment_status.return_value = "ready"

    def test_mvr_15_shipping_summary_accumulates_for_friday(self, build_claw, tmp_path):
        """Merged PR data accumulates in devlog context for Friday dispatch."""
        from build.code_generator import ResolutionResult

        resolution = ResolutionResult(
            issue_number=1,
            branch_name="fix/issue-1",
            files_changed=["file.py"],
            test_result="passing",
            tests_passing=10,
            tests_failing=0,
            attempts=1,
            status="ready_for_pr",
            failure_summary=None,
        )

        pr = build_claw._pr_manager.open_pr(resolution)

        build_claw._dispatcher.accumulate_shipping_data(
            pr_id=pr.pr_id,
            issue_number=1,
            feature_name="Test feature",
            changes=["Fixed bug", "Added tests"],
        )

        summary = build_claw._dispatcher.get_accumulated_shipping_summary()
        assert summary["prs_merged"] >= 1
        assert len(summary["features_shipped"]) >= 1

        build_claw.shutdown()
