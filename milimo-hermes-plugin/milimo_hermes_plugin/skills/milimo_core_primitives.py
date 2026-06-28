# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Milimo Core Primitives Shared Handler for Hermes.

This handler provides shared infrastructure primitives that all 6 claw handlers
can depend on without duplicating business logic.
"""

from typing import Any

from milimo_core.contracts import ClawMessage, ContractValidator
from milimo_core.privacy_router import PrivacyRouter, InferenceBackend, RoutingDecision
from milimo_core.inference_client import NvidiaInferenceClient
from milimo_core.provenance_signer import ProvenanceSigner
from milimo_core.tool_generator import ToolGenerator
from milimo_core.tool_validator import ToolValidator
from milimo_core.tool_sandbox import ToolSandbox
from milimo_core.service_factory import (
    create_github_client,
    create_vercel_client,
    create_sentry_client,
    create_stripe_client,
)


# Global instances for shared infrastructure
_privacy_router: PrivacyRouter | None = None
_inference_client: NvidiaInferenceClient | None = None
_provenance_signer: ProvenanceSigner | None = None
_tool_generator: ToolGenerator | None = None
_tool_validator: ToolValidator | None = None
_tool_sandbox: ToolSandbox | None = None


def get_privacy_router() -> PrivacyRouter:
    """Get the global privacy router instance."""
    global _privacy_router
    if _privacy_router is None:
        _privacy_router = PrivacyRouter()
    return _privacy_router


def get_inference_client() -> NvidiaInferenceClient:
    """Get the global inference client instance."""
    global _inference_client
    if _inference_client is None:
        _inference_client = NvidiaInferenceClient()
    return _inference_client


def get_provenance_signer() -> ProvenanceSigner:
    """Get the global provenance signer instance."""
    global _provenance_signer
    if _provenance_signer is None:
        _provenance_signer = ProvenanceSigner.generate()
    return _provenance_signer


def get_tool_generator() -> ToolGenerator:
    """Get the global tool generator instance."""
    global _tool_generator
    if _tool_generator is None:
        _tool_generator = ToolGenerator(get_inference_client())
    return _tool_generator


def get_tool_validator() -> ToolValidator:
    """Get the global tool validator instance."""
    global _tool_validator
    if _tool_validator is None:
        _tool_validator = ToolValidator()
    return _tool_validator


def get_tool_sandbox() -> ToolSandbox:
    """Get the global tool sandbox instance."""
    global _tool_sandbox
    if _tool_sandbox is None:
        _tool_sandbox = ToolSandbox()
    return _tool_sandbox


def register(skill_registry: Any) -> None:
    """Register milimo-core-primitives shared handler."""

    # Privacy Router
    skill_registry.register_skill(
        name="privacy_router",
        factory=lambda config: get_privacy_router(),
        description="Privacy-aware inference routing with policy enforcement",
        capabilities=["route_inference", "check_privacy", "get_policy"],
        provides=["privacy_router"],
    )

    # Inference Client
    skill_registry.register_skill(
        name="inference_client",
        factory=lambda config: get_inference_client(),
        description="NVIDIA inference client for LLM completions",
        capabilities=["complete", "embed", "chat", "get_usage"],
        provides=["inference_client"],
    )

    # Provenance Signer
    skill_registry.register_skill(
        name="provenance_signer",
        factory=lambda config: get_provenance_signer(),
        description="Provenance signing for audit trails and attestations",
        capabilities=["sign", "verify", "generate_keys", "load_keys"],
        provides=["provenance_signer"],
    )

    # Tool Generator
    skill_registry.register_skill(
        name="tool_generator",
        factory=lambda config: get_tool_generator(),
        description="AI-powered tool generation from natural language",
        capabilities=["generate_tool", "validate_tool", "backtest_tool"],
        provides=["tool_generator"],
    )

    # Tool Validator
    skill_registry.register_skill(
        name="tool_validator",
        factory=lambda config: get_tool_validator(),
        description="Tool validation, linting, and security checking",
        capabilities=["validate", "lint", "security_check", "type_check"],
        provides=["tool_validator"],
    )

    # Tool Sandbox
    skill_registry.register_skill(
        name="tool_sandbox",
        factory=lambda config: get_tool_sandbox(),
        description="Isolated tool execution sandbox for safe backtesting",
        capabilities=["execute", "backtest", "dry_run", "resource_limits"],
        provides=["tool_sandbox"],
    )

    # Contract Validator
    skill_registry.register_skill(
        name="contract_validator",
        factory=lambda config: ContractValidator(),
        description="Claw message contract validation",
        capabilities=["validate_message", "validate_schema", "get_valid_types"],
        provides=["contract_validator"],
    )

    # GitHub Client
    skill_registry.register_skill(
        name="github_client",
        factory=lambda config: create_github_client(config),
        description="GitHub API client for repo operations",
        capabilities=["create_pr", "get_repo", "merge_pr", "webhook", "list_issues"],
        provides=["github_client"],
    )

    # Vercel Client
    skill_registry.register_skill(
        name="vercel_client",
        factory=lambda config: create_vercel_client(config),
        description="Vercel deployment client",
        capabilities=["deploy", "get_deployment", "list_projects", "get_logs"],
        provides=["vercel_client"],
    )

    # Sentry Client
    skill_registry.register_skill(
        name="sentry_client",
        factory=lambda config: create_sentry_client(config),
        description="Sentry error monitoring client",
        capabilities=["capture_exception", "get_issues", "resolve_issue", "get_stats"],
        provides=["sentry_client"],
    )

    # Stripe Client
    skill_registry.register_skill(
        name="stripe_client",
        factory=lambda config: create_stripe_client(config),
        description="Stripe payments client",
        capabilities=["create_invoice", "check_payment", "list_customers", "create_customer"],
        provides=["stripe_client"],
    )


__all__ = ["register"]
