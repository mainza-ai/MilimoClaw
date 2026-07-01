# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Core - Shared orchestrator library for MilimoClaw.

This package contains the shared business logic for all six claws:
- Build Claw
- Content Claw
- Ops Claw
- Analytics Claw
- Finance Claw
- Assistant Claw

Plus shared infrastructure:
- Contracts & message validation
- Privacy router & inference routing
- Provenance signing
- Tool generation, validation, sandboxing
- Service factory for external integrations
"""

from .contracts import (
    ClawMessage,
    ContractValidator,
    ValidationResult,
    VALID_MESSAGE_TYPES,
    VALID_SENDERS,
    VALID_RECIPIENTS,
    VALID_ROLES,
    ASSISTANT_ROLE,
)

from .privacy_router import (
    PrivacyRouter,
    InferenceBackend,
    RoutingDecision,
    RoutingRule,
    RoleOverride,
    PrivacyPolicy,
)

from .inference_client import (
    NvidiaInferenceClient,
    InferenceUsage,
    InferenceResponse,
)

from .protocols import (
    GitHubClientProtocol,
    DeployClientProtocol,
    MonitoringClientProtocol,
    PaymentsClientProtocol,
    ClawTask,
    ClawResult,
    DelegationAdapter,
    ScheduledJob,
    SchedulerInterface,
)

from .service_factory import (
    create_github_client,
    create_vercel_client,
    create_sentry_client,
    create_stripe_client,
)

from .provenance_signer import (
    ProvenanceSigner,
    Attestation,
    generate_key_pair,
    save_key_pair,
    load_key_pair,
)

from .tool_generator import ToolGenerator, ToolSpec
from .tool_validator import ToolValidator
from .tool_sandbox import ToolSandbox
from .evolution_scheduler import (
    EvolutionScheduler,
    EvolutionSchedulerConfig,
    run_evolution_cycle_sync,
    run_tool_backtest_sync,
    run_hold_queue_review_sync,
)
from .ssrf_validator import SSRFValidator, SSRFPolicy, SSRFValidationResult, SSRFValidationReport
from .notifications import (
    SlackConfig,
    TelegramConfig,
    NotificationPayload,
    SlackNotifier,
    TelegramNotifier,
    WarRoomNotifier,
    get_warroom_notifier,
    init_warroom_notifier,
)

from .claw_layouts import (
    ClawLayout,
    CLAW_LAYOUTS,
    CLAW_ROLES,
    BUILD_LAYOUT,
    CONTENT_LAYOUT,
    OPS_LAYOUT,
    ANALYTICS_LAYOUT,
    FINANCE_LAYOUT,
    ASSISTANT_LAYOUT,
)

__version__ = "0.1.0"

__all__ = [
    # Contracts
    "ClawMessage",
    "ContractValidator",
    "ValidationResult",
    "VALID_MESSAGE_TYPES",
    "VALID_SENDERS",
    "VALID_RECIPIENTS",
    "VALID_ROLES",
    "ASSISTANT_ROLE",
    # Privacy
    "PrivacyRouter",
    "InferenceBackend",
    "RoutingDecision",
    "RoutingRule",
    "RoleOverride",
    "PrivacyPolicy",
    # Inference
    "NvidiaInferenceClient",
    "InferenceUsage",
    "InferenceResponse",
    # Services
    "GitHubClientProtocol",
    "DeployClientProtocol",
    "MonitoringClientProtocol",
    "PaymentsClientProtocol",
    "create_github_client",
    "create_vercel_client",
    "create_sentry_client",
    "create_stripe_client",
    # Provenance
    "ProvenanceSigner",
    "Attestation",
    "generate_key_pair",
    "save_key_pair",
    "load_key_pair",
    # Tools
    "ToolGenerator",
    "ToolSpec",
    "ToolValidator",
    "ToolSandbox",
    # Protocols
    "ClawTask",
    "ClawResult",
    "DelegationAdapter",
    "ScheduledJob",
    "SchedulerInterface",
    # Credentials
    "HermesCredentialAdapter",
    # Evolution Scheduler
    "EvolutionScheduler",
    "EvolutionSchedulerConfig",
    "run_evolution_cycle_sync",
    "run_tool_backtest_sync",
    "run_hold_queue_review_sync",
    # Claw Layouts
    "ClawLayout",
    "CLAW_LAYOUTS",
    "CLAW_ROLES",
    "BUILD_LAYOUT",
    "CONTENT_LAYOUT",
    "OPS_LAYOUT",
    "ANALYTICS_LAYOUT",
    "FINANCE_LAYOUT",
    "ASSISTANT_LAYOUT",
    # Cost Guard
    "CostGuard",
    "CostGuardConfig",
    "get_cost_guard",
    # SSRF Validator
    "SSRFValidator",
    "SSRFPolicy",
    "ValidationReport",
    # Notifications
    "SlackConfig",
    "TelegramConfig",
    "NotificationPayload",
    "SlackNotifier",
    "TelegramNotifier",
    "WarRoomNotifier",
    "get_warroom_notifier",
    "init_warroom_notifier",
]
