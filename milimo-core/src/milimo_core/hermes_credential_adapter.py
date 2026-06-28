# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Hermes Credential Adapter — Adapts service clients for Hermes credential model.

NemoClaw Hermes uses OpenShell L7 proxy for credential injection at egress.
However, GitHub tokens are handled differently: NemoClaw never persists GITHUB_TOKEN
itself. Instead it calls `gh auth token` which reads from GitHub CLI's credential store
(macOS Keychain, Windows Credential Manager, Linux Secret Service, or ~/.config/gh/).

This adapter provides the correct credential path for each service:
- GitHub: calls `gh auth token`
- Stripe, Vercel, Sentry, NVIDIA: uses OpenShell gateway placeholders
"""

import os
import subprocess
from typing import Any


class HermesCredentialAdapter:
    """Adapts service clients for Hermes credential model."""

    # OpenShell provider placeholders — substituted at egress by OpenShell L7 proxy
    OPENSHELL_PLACEHOLDERS = {
        "stripe": "STRIPE_API_KEY",
        "vercel": "VERCEL_TOKEN",
        "sentry": "SENTRY_AUTH_TOKEN",
        "nvidia": "NVIDIA_API_KEY",
    }

    @staticmethod
    def get_github_token() -> str:
        """
        Get GitHub token via gh CLI.

        NemoClaw never persists GITHUB_TOKEN itself. Instead it calls `gh auth token`
        which reads from whatever the GitHub CLI has stored — macOS Keychain,
        Windows Credential Manager, Linux Secret Service, or ~/.config/gh/ on headless hosts.
        """
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get GitHub token via gh auth token: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("gh CLI not found. Install GitHub CLI and run 'gh auth login'")

    @staticmethod
    def get_openshell_placeholder(service: str) -> str:
        """Get the OpenShell gateway placeholder for a service."""
        return HermesCredentialAdapter.OPENSHELL_PLACEHOLDERS.get(service.lower(), "")

    @classmethod
    def create_github_client(cls, config: dict[str, Any] | None = None) -> Any:
        """Create GitHub client with Hermes-appropriate credentials."""
        config = config or {}
        token = cls.get_github_token()
        from .github_client import GitHubClient
        return GitHubClient(token=token, **config)

    @classmethod
    def create_stripe_client(cls, config: dict[str, Any] | None = None) -> Any:
        """Create Stripe client using OpenShell gateway placeholder."""
        config = config or {}
        from .service_factory import create_stripe_client
        # The OpenShell proxy substitutes STRIPE_API_KEY at egress
        return create_stripe_client(config)

    @classmethod
    def create_vercel_client(cls, config: dict[str, Any] | None = None) -> Any:
        """Create Vercel client using OpenShell gateway placeholder."""
        config = config or {}
        from .service_factory import create_vercel_client
        return create_vercel_client(config)

    @classmethod
    def create_sentry_client(cls, config: dict[str, Any] | None = None) -> Any:
        """Create Sentry client using OpenShell gateway placeholder."""
        config = config or {}
        from .service_factory import create_sentry_client
        return create_sentry_client(config)

    @classmethod
    def create_nvidia_client(cls, config: dict[str, Any] | None = None) -> Any:
        """Create NVIDIA inference client using OpenShell gateway placeholder."""
        config = config or {}
        # NVIDIA inference uses the NVIDIA_API_KEY placeholder
        return config  # Placeholder - actual client created elsewhere


__all__ = ["HermesCredentialAdapter"]
