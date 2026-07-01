# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
MilimoClaw Hermes Plugin

Provides 6 claw skills for Hermes profile:
- Build Claw: CI/CD, deployments, dependency auditing
- Content Claw: Content generation, scheduling, publishing
- Ops Claw: Incident management, project tracking, client health
- Analytics Claw: Signal processing, anomaly detection, reporting
- Finance Claw: Invoicing, payments, pricing, revenue tracking
- Assistant Claw: Conversational interface (Lucy)
"""

from typing import Any

from milimo_core.build import BuildClaw, BuildFilesystemInit
from milimo_core.content import ContentClaw, ContentGenerator
from milimo_core.ops import OpsClaw, IntakeManager, OpsApprovalHandler
from milimo_core.analytics import AnalyticsClaw, SignalProcessor
from milimo_core.finance import FinanceClaw, PricingEngine
from milimo_core.assistant import LucyAssistant, PendingQuery
from milimo_core.contracts import ClawMessage, ContractValidator
from milimo_core.privacy_router import PrivacyRouter, InferenceBackend, RoutingDecision
from milimo_core.inference_client import NvidiaInferenceClient
from milimo_core.service_factory import (
    create_github_client,
    create_vercel_client,
    create_sentry_client,
    create_stripe_client,
)
from milimo_core.provenance_signer import ProvenanceSigner
from milimo_core.tool_generator import ToolGenerator
from milimo_core.tool_validator import ToolValidator
from milimo_core.tool_sandbox import ToolSandbox
from milimo_core.protocols.delegation import DelegationAdapter, ClawTask, ClawResult
from milimo_core import WarRoomNotifier, init_warroom_notifier
from milimo_core.cost_guard import get_cost_guard
from milimo_core.hermes_credential_adapter import HermesCredentialAdapter
from milimo_core.milimo_paths import CLAWS_DIR
from .delegation import HermesDelegateAdapter
from .tools import register_core_tools, set_claw_launcher, set_approval_handler, set_cost_guard


# Global registry for instantiated claws
_claw_instances: dict[str, Any] = {}
_privacy_router: PrivacyRouter | None = None
_inference_client: NvidiaInferenceClient | None = None


def on_load(config: dict[str, Any] | None = None) -> None:
    """Initialize plugin on load."""
    global _privacy_router, _inference_client

    config = config or {}

    # Initialize privacy router with default policy
    from milimo_core.privacy_router import PrivacyPolicy, InferenceBackend, PrivacyRouter
    default_policy = PrivacyPolicy(
        policy_version="1.0",
        default_backend=InferenceBackend.LOCAL_NIM,
        routes=[],
        role_overrides={},
    )
    _privacy_router = PrivacyRouter(default_policy)

    # Initialize inference client
    _inference_client = NvidiaInferenceClient()

    # Initialize approval handler for War Room
    fs_base = CLAWS_DIR / "ops"
    approval_handler = OpsApprovalHandler(fs_base=fs_base)
    set_approval_handler(approval_handler)

    # Initialize cost guard
    cost_guard = get_cost_guard()
    set_cost_guard(cost_guard)

    # Initialize War Room notifier (Slack/Telegram)
    warroom_notifier = init_warroom_notifier()
    from .tools import set_warroom_notifier
    set_warroom_notifier(warroom_notifier)

    print(f"[milimo-hermes] Plugin loaded")


def on_unload() -> None:
    """Cleanup on plugin unload."""
    global _claw_instances, _privacy_router, _inference_client

    for claw in _claw_instances.values():
        if hasattr(claw, "shutdown"):
            claw.shutdown()

    _claw_instances.clear()
    _privacy_router = None
    _inference_client = None

    print("[milimo-hermes] Plugin unloaded")


def get_privacy_router() -> PrivacyRouter:
    """Get the global privacy router instance."""
    if _privacy_router is None:
        _privacy_router = PrivacyRouter()
    return _privacy_router


def get_inference_client() -> NvidiaInferenceClient:
    """Get the global inference client instance."""
    if _inference_client is None:
        _inference_client = NvidiaInferenceClient()
    return _inference_client


# Skill registration functions
def register_build_claw(skill_registry: Any) -> None:
    """Register Build Claw skill."""
    def create_build_claw(config: dict[str, Any] | None = None) -> BuildClaw:
        return BuildClaw(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="build_claw",
        factory=create_build_claw,
        description="CI/CD, deployments, dependency auditing, error monitoring",
        capabilities=[
            "create_pr",
            "deploy_to_vercel",
            "audit_dependencies",
            "monitor_errors",
            "monitor_costs",
            "generate_docs",
            "generate_code",
        ],
    )


def register_content_claw(skill_registry: Any) -> None:
    """Register Content Claw skill."""
    def create_content_claw(config: dict[str, Any] | None = None) -> ContentClaw:
        return ContentClaw(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="content_claw",
        factory=create_content_claw,
        description="Content generation, scheduling, multi-platform publishing",
        capabilities=[
            "generate_content",
            "schedule_content",
            "publish_to_twitter",
            "publish_to_linkedin",
            "publish_to_tiktok",
            "manage_brand_voice",
            "track_performance",
        ],
    )


def register_ops_claw(skill_registry: Any) -> None:
    """Register Ops Claw skill."""
    def create_ops_claw(config: dict[str, Any] | None = None) -> OpsClaw:
        return OpsClaw(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="ops_claw",
        factory=create_ops_claw,
        description="Incident management, project tracking, client health scoring",
        capabilities=[
            "create_incident",
            "manage_project",
            "score_client_health",
            "track_scope",
            "run_runbook",
            "handle_webhook",
        ],
    )


def register_analytics_claw(skill_registry: Any) -> None:
    """Register Analytics Claw skill."""
    def create_analytics_claw(config: dict[str, Any] | None = None) -> AnalyticsClaw:
        return AnalyticsClaw(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="analytics_claw",
        factory=create_analytics_claw,
        description="Signal processing, anomaly detection, opportunity scoring, reporting",
        capabilities=[
            "process_signals",
            "detect_anomalies",
            "score_opportunities",
            "generate_reports",
            "query_analytics",
            "project_forecasts",
            "manage_baselines",
        ],
    )


def register_finance_claw(skill_registry: Any) -> None:
    """Register Finance Claw skill."""
    def create_finance_claw(config: dict[str, Any] | None = None) -> FinanceClaw:
        return FinanceClaw(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="finance_claw",
        factory=create_finance_claw,
        description="Invoicing, payment monitoring, pricing, revenue tracking",
        capabilities=[
            "create_invoice",
            "track_payments",
            "monitor_stripe",
            "calculate_pricing",
            "track_revenue",
            "track_expenses",
            "assess_risk",
            "request_agent_spend",
        ],
    )


def register_assistant_claw(skill_registry: Any) -> None:
    """Register Assistant Claw skill."""
    def create_assistant_claw(config: dict[str, Any] | None = None) -> LucyAssistant:
        return LucyAssistant(
            inference_client=get_inference_client(),
            privacy_router=get_privacy_router(),
            config=config or {},
        )

    skill_registry.register_skill(
        name="assistant_claw",
        factory=create_assistant_claw,
        description="Conversational interface for all claws (Lucy)",
        capabilities=[
            "answer_questions",
            "route_to_claw",
            "handle_pending_queries",
            "provide_status",
        ],
    )


from .skills import register_all_skills


def register(ctx: Any) -> None:
    """
    Main plugin registration entry point.

    Called by Hermes when loading the plugin.
    Registers all 6 claw skills with the skill registry.
    """
    skill_registry = ctx.get_skill_registry()

    # Register all claw skills via skills package
    register_all_skills(skill_registry)

    # Register core tools (milimo_status, milimo_warroom, milimo_approve, milimo_veto, delegate_task)
    register_core_tools(skill_registry)

    # Register shared infrastructure skills
    skill_registry.register_skill(
        name="privacy_router",
        factory=lambda config: get_privacy_router(),
        description="Privacy-aware inference routing",
        capabilities=["route_inference", "check_privacy"],
    )

    skill_registry.register_skill(
        name="inference_client",
        factory=lambda config: get_inference_client(),
        description="NVIDIA inference client",
        capabilities=["complete", "embed", "chat"],
    )

    skill_registry.register_skill(
        name="provenance_signer",
        factory=lambda config: ProvenanceSigner.generate(),
        description="Provenance signing for audit trails",
        capabilities=["sign", "verify", "generate_keys"],
    )

    skill_registry.register_skill(
        name="tool_generator",
        factory=lambda config: ToolGenerator(get_inference_client()),
        description="AI-powered tool generation",
        capabilities=["generate_tool", "validate_tool"],
    )

    skill_registry.register_skill(
        name="tool_validator",
        factory=lambda config: ToolValidator(),
        description="Tool validation and safety checking",
        capabilities=["validate", "lint", "security_check"],
    )

    skill_registry.register_skill(
        name="tool_sandbox",
        factory=lambda config: ToolSandbox(),
        description="Isolated tool execution sandbox",
        capabilities=["execute", "backtest", "dry_run"],
    )

    # Register external service clients
    skill_registry.register_skill(
        name="github_client",
        factory=lambda config: create_github_client(config),
        description="GitHub API client",
        capabilities=["create_pr", "get_repo", "merge_pr", "webhook"],
    )

    skill_registry.register_skill(
        name="vercel_client",
        factory=lambda config: create_vercel_client(config),
        description="Vercel deployment client",
        capabilities=["deploy", "get_deployment", "list_projects"],
    )

    skill_registry.register_skill(
        name="sentry_client",
        factory=lambda config: create_sentry_client(config),
        description="Sentry error monitoring client",
        capabilities=["capture_exception", "get_issues", "resolve_issue"],
    )

    skill_registry.register_skill(
        name="stripe_client",
        factory=lambda config: create_stripe_client(config),
        description="Stripe payments client",
        capabilities=["create_invoice", "check_payment", "list_customers"],
    )

    print("[milimo-hermes] All 6 claw skills + infrastructure registered")


# For backward compatibility and direct imports
__all__ = [
    "register",
    "on_load",
    "on_unload",
    "get_privacy_router",
    "get_inference_client",
    "BuildClaw",
    "ContentClaw",
    "OpsClaw",
    "AnalyticsClaw",
    "FinanceClaw",
    "LucyAssistant",
    "ContractValidator",
    "PrivacyRouter",
    "NvidiaInferenceClient",
    "ProvenanceSigner",
    "ToolGenerator",
    "ToolValidator",
    "ToolSandbox",
    "DelegationAdapter",
    "ClawTask",
    "ClawResult",
    "HermesDelegateAdapter",
]
