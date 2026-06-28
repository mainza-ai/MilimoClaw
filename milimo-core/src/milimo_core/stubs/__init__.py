# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Stub implementations for service protocols (graceful degradation)."""

from .stub_github import StubGitHubClient
from .stub_sentry import StubSentryClient
from .stub_stripe import StubStripeClient
from .stub_vercel import StubVercelClient

__all__ = [
    "StubGitHubClient",
    "StubSentryClient",
    "StubStripeClient",
    "StubVercelClient",
]
