#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Milimo Claw — Privacy Router

Sensitivity classifier that intercepts inference calls and routes them
to the appropriate backend (cloud, local NIM, local vLLM) based on
data type and the squad's configured sensitivity policy.

The routing is transparent: the calling claw does not know which
backend handled the request. The privacy router makes the decision
based on:
  1. Role-level override (e.g., Finance → always local-nim)
  2. Data type match from the sensitivity policy
  3. Fallback to default backend (local-nim)

Usage:
    from privacy_router import PrivacyRouter

    router = PrivacyRouter.from_policy_file("/path/to/privacy_policy.yaml")
    decision = router.route(role="content", data_type="public_drafts")
    # decision.backend == "cloud"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("milimo.privacy_router")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class InferenceBackend(str, Enum):
    """Available inference backends."""

    CLOUD = "cloud"
    LOCAL_NIM = "local-nim"
    LOCAL_VLLM = "local-vllm"


@dataclass(frozen=True)
class RoutingRule:
    """A single data-type → backend routing rule."""

    data_type: str
    description: str
    backend: InferenceBackend
    locked: bool = False


@dataclass(frozen=True)
class RoleOverride:
    """Per-role constraints that always apply."""

    force_backend: InferenceBackend | None = None
    cloud_allowed: bool = True
    force_local_types: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoutingDecision:
    """Result of a privacy routing decision."""

    backend: InferenceBackend
    reason: str
    matched_rule: str | None = None
    was_overridden: bool = False


@dataclass
class PrivacyPolicy:
    """Loaded privacy routing policy."""

    policy_version: str
    default_backend: InferenceBackend
    routes: list[RoutingRule] = field(default_factory=list)
    role_overrides: dict[str, RoleOverride] = field(default_factory=dict)
    fallback_log_unclassified: bool = True


# ---------------------------------------------------------------------------
# Privacy Router
# ---------------------------------------------------------------------------


class PrivacyRouter:
    """
    Sensitivity classifier and inference routing interceptor.

    Intercepts inference calls and routes them to the appropriate backend
    based on data type, claw role, and the squad's configured privacy policy.
    """

    def __init__(self, policy: PrivacyPolicy) -> None:
        self._policy = policy
        # Build lookup index for O(1) data type matching
        self._route_index: dict[str, RoutingRule] = {
            rule.data_type: rule for rule in policy.routes
        }

    @classmethod
    def from_policy_file(cls, path: str | Path) -> PrivacyRouter:
        """Load a privacy router from a YAML policy file."""
        policy_path = Path(path)
        if not policy_path.exists():
            raise FileNotFoundError(f"Privacy policy not found: {policy_path}")

        with policy_path.open() as f:
            raw: dict[str, Any] = yaml.safe_load(f)

        policy = _parse_policy(raw)
        return cls(policy)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PrivacyRouter:
        """Create a privacy router from a parsed YAML dictionary."""
        policy = _parse_policy(raw)
        return cls(policy)

    @property
    def policy(self) -> PrivacyPolicy:
        """Access the loaded privacy policy."""
        return self._policy

    def route(
        self,
        role: str,
        data_type: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        """
        Route an inference call to the appropriate backend.

        Args:
            role: The claw role making the inference call.
            data_type: The data type tag on the inference request.
            context: Optional additional context (reserved for future use).

        Returns:
            RoutingDecision with the selected backend and reasoning.
        """
        # 1. Check role-level override (highest priority)
        role_override = self._policy.role_overrides.get(role)
        if role_override is not None:
            # Force backend override (e.g., Finance → always local-nim)
            if role_override.force_backend is not None:
                return RoutingDecision(
                    backend=role_override.force_backend,
                    reason=f"Role override: {role} forces {role_override.force_backend.value}",
                    matched_rule=f"role_override:{role}",
                    was_overridden=True,
                )

            # Force local for specific data types (e.g., Build → source_code)
            if data_type in role_override.force_local_types:
                return RoutingDecision(
                    backend=InferenceBackend.LOCAL_NIM,
                    reason=f"Role override: {role} forces local for {data_type}",
                    matched_rule=f"role_override:{role}:{data_type}",
                    was_overridden=True,
                )

            # Cloud not allowed for this role
            if not role_override.cloud_allowed:
                rule = self._route_index.get(data_type)
                if rule and rule.backend == InferenceBackend.CLOUD:
                    return RoutingDecision(
                        backend=InferenceBackend.LOCAL_NIM,
                        reason=f"Role {role}: cloud not allowed, downgraded to local-nim",
                        matched_rule=f"role_cloud_block:{role}",
                        was_overridden=True,
                    )

        # 2. Check data type routing rules (first match wins)
        rule = self._route_index.get(data_type)
        if rule is not None:
            return RoutingDecision(
                backend=rule.backend,
                reason=f"Policy rule: {rule.description}",
                matched_rule=f"route:{rule.data_type}",
                was_overridden=False,
            )

        # 3. Fallback to default backend
        if self._policy.fallback_log_unclassified:
            logger.warning(
                "Unclassified data type '%s' from role '%s' — routing to %s (fallback)",
                data_type,
                role,
                self._policy.default_backend.value,
            )

        return RoutingDecision(
            backend=self._policy.default_backend,
            reason=f"Fallback: unclassified data type '{data_type}'",
            matched_rule=None,
            was_overridden=False,
        )

    def is_locked(self, data_type: str) -> bool:
        """Check if a data type's routing is locked (non-overridable)."""
        rule = self._route_index.get(data_type)
        return rule.locked if rule is not None else False

    def list_routes(self) -> list[dict[str, Any]]:
        """Return all routing rules as a list of dictionaries."""
        return [
            {
                "data_type": r.data_type,
                "backend": r.backend.value,
                "locked": r.locked,
                "description": r.description,
            }
            for r in self._policy.routes
        ]

    def get_backend_for_role(self, role: str) -> InferenceBackend | None:
        """Get the forced backend for a role, if any."""
        override = self._policy.role_overrides.get(role)
        if override and override.force_backend:
            return override.force_backend
        return None

    def validate_squad_override(
        self, data_type: str, new_backend: str
    ) -> tuple[bool, str]:
        """
        Check if a squad can override a routing rule.

        Returns (allowed, reason).
        """
        rule = self._route_index.get(data_type)
        if rule is None:
            return True, "No existing rule — custom route allowed"
        if rule.locked:
            return False, f"Route for '{data_type}' is locked: {rule.description}"
        return True, f"Route for '{data_type}' can be overridden"


# ---------------------------------------------------------------------------
# Policy parsing
# ---------------------------------------------------------------------------


def _parse_policy(raw: dict[str, Any]) -> PrivacyPolicy:
    """Parse a raw YAML dictionary into a PrivacyPolicy."""
    routes: list[RoutingRule] = []
    for r in raw.get("routes", []):
        routes.append(
            RoutingRule(
                data_type=r["data_type"],
                description=r.get("description", ""),
                backend=InferenceBackend(r["backend"]),
                locked=r.get("locked", False),
            )
        )

    role_overrides: dict[str, RoleOverride] = {}
    for role_name, override_raw in raw.get("role_overrides", {}).items():
        force_backend = None
        if "force_backend" in override_raw:
            force_backend = InferenceBackend(override_raw["force_backend"])
        force_local_types = tuple(override_raw.get("force_local_types", []))
        role_overrides[role_name] = RoleOverride(
            force_backend=force_backend,
            cloud_allowed=override_raw.get("cloud_allowed", True),
            force_local_types=force_local_types,
        )

    fallback = raw.get("fallback", {})

    return PrivacyPolicy(
        policy_version=raw.get("policy_version", "0.1.0"),
        default_backend=InferenceBackend(raw.get("default_backend", "local-nim")),
        routes=routes,
        role_overrides=role_overrides,
        fallback_log_unclassified=fallback.get("log_unclassified", True),
    )
