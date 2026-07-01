# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Centralized claw filesystem layout definitions.

All six claws define their directory structures and required files here
instead of inline in ``*_init.py`` modules.  Every ``*FilesystemInit``
class reads its layout from this module so that:

- Path changes are auditable in one place.
- The inventory / sync tool can discover files without importing claw code.
- The Dockerfile ``RUN mkdir -p`` block is generated from the same source.

Usage
-----
    from milimo_core.claw_layouts import CLAW_LAYOUTS

    for role, layout in CLAW_LAYOUTS.items():
        base = claw_base(role)
        for subdir in layout.dirs:
            (base / subdir).mkdir(parents=True, exist_ok=True)
        for fpath, default in layout.files.items():
            target = base / fpath
            if not target.exists():
                target.write_text(default)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ClawLayout:
    """Filesystem layout for a single claw role.

    Attributes
    ----------
    dirs:
        Relative directory paths to create under the claw base.
        Each entry may contain slashes for nested directories
        (e.g. ``"context/sprint"``).
    files:
        Relative file paths → default text content.
        Files whose content is an empty string will be created empty.
        JSON defaults should be valid JSON (e.g. ``"{}\\n"``).
    description:
        Human-readable description of the claw's purpose.
    """

    dirs: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)
    description: str = ""


# ── Build Claw ──────────────────────────────────────────────────────────────

BUILD_LAYOUT = ClawLayout(
    description="Engineering claw: GitHub issues, code generation, deployments, dependency audits",
    dirs=[
        "repo",
        "context/sprint",
        "context/errors/patterns",
        "context/errors/active",
        "context/costs",
        "prs/drafted",
        "prs/approved",
        "prs/merged",
        "deployments/pending",
        "deployments/history",
        "docs/api-reference",
        "docs/devlog",
        "logs",
        "tasks",
        "memory/daily",
        "memory/projects",
        "memory/errors",
    ],
    files={
        "context/sprint/current-plan.json": '{}\n',
        "context/sprint/backlog-scored.json": '{}\n',
        "context/sprint/velocity.json": '{}\n',
        "context/costs/inference-weekly.json": '{}\n',
        "docs/changelog.md": "",
        "logs/operational.log": "",
        "logs/pr-activity.log": "",
        "logs/deploy-activity.log": "",
        "logs/cost-alerts.log": "",
    },
)

# ── Content Claw ────────────────────────────────────────────────────────────

CONTENT_LAYOUT = ClawLayout(
    description="Creative claw: posts, copy, email campaigns, brand assets",
    dirs=[
        "brand/style-guides",
        "brand/assets",
        "brand/voice-profiles",
        "drafts/pending",
        "drafts/approved",
        "drafts/rejected",
        "drafts/published",
        "briefs/active",
        "briefs/completed",
        "calendar/scheduled",
        "calendar/published",
        "intelligence/analytics-feed",
        "tools/style-descriptor",
        "tools/tone-classifier",
        "tools/approval-predictor",
        "tools/timing-optimizer",
        "tools/ab-variant-engine",
        "tools/platform-calibrator",
        "tools/client-voice-adapter",
        "tools/trend-injector",
        "logs",
    ],
    files={
        "logs/operational.log": "",
        "logs/approvals.log": "",
        "logs/performance.log": "",
        "intelligence/analytics-feed/weekly-intelligence.json": '{}\n',
    },
)

# ── Ops Claw ────────────────────────────────────────────────────────────────

OPS_LAYOUT = ClawLayout(
    description="Management claw: client lifecycle, scope briefs, deadline risk, intake",
    dirs=[
        "active",
        "prospects",
        "completed",
        "contracts",
        "templates",
        "logs",
    ],
    files={
        "templates/welcome-message.md": "",
        "templates/intake-questionnaire.md": "",
        "templates/proposal-template.md": "",
        "templates/change-order-template.md": "",
        "templates/delivery-message.md": "",
        "templates/deep-work-response.md": "",
        "logs/operational.log": "",
        "logs/comms.log": "",
        "logs/decisions.log": "",
    },
)

# ── Analytics Claw ──────────────────────────────────────────────────────────

ANALYTICS_LAYOUT = ClawLayout(
    description="Intelligence claw: weekly reports, anomaly detection, opportunity scores",
    dirs=[
        "reports/weekly-intelligence-archive",
        "signals/anomalies",
        "signals/opportunities",
        "signals/alerts",
        "data/content-performance",
        "data/client-health",
        "data/revenue",
        "data/delivery-velocity",
        "baselines",
        "tools/engagement-baseline-model",
        "tools/anomaly-detector",
        "tools/opportunity-scorer",
        "tools/retention-correlator",
        "tools/competitor-signal-tracker",
        "tools/forward-projection-engine",
        "logs",
    ],
    files={
        "logs/operational.log": "",
        "logs/queries.log": "",
        "logs/signals.log": "",
        "reports/opportunity-scores.json": '{}\n',
        "reports/monthly-summary.json": '{}\n',
    },
)

# ── Finance Claw ────────────────────────────────────────────────────────────

FINANCE_LAYOUT = ClawLayout(
    description="Treasury claw: Stripe invoicing, pricing, expense tracking, tax categorization",
    dirs=[
        "revenue/history",
        "invoices/pending",
        "invoices/approved",
        "invoices/sent",
        "invoices/paid",
        "invoices/overdue",
        "expenses/categories",
        "pricing/estimates",
        "pricing/history",
        "tax/quarterly",
        "tax/annual",
        "logs",
    ],
    files={
        "revenue/weekly-summary.json": '{}\n',
        "revenue/monthly-summary.json": '{}\n',
        "revenue/annual-summary.json": '{}\n',
        "pricing/rules.json": '{}\n',
        "tax/categories.json": '{}\n',
        "expenses/log.jsonl": "",
        "logs/operational.log": "",
        "logs/decisions.log": "",
        "logs/payment-events.log": "",
    },
)

# ── Assistant Claw ──────────────────────────────────────────────────────────

ASSISTANT_LAYOUT = ClawLayout(
    description="Orchestrator claw: stateful process supervisor, operator query router, mesh coordinator",
    dirs=[
        "logs",
        "memories",
        "queries",
    ],
    files={
        "logs/operational.log": "",
    },
)

# ── Registry ────────────────────────────────────────────────────────────────

CLAW_LAYOUTS: Dict[str, ClawLayout] = {
    "build": BUILD_LAYOUT,
    "content": CONTENT_LAYOUT,
    "ops": OPS_LAYOUT,
    "analytics": ANALYTICS_LAYOUT,
    "finance": FINANCE_LAYOUT,
    "assistant": ASSISTANT_LAYOUT,
}

CLAW_ROLES: List[str] = list(CLAW_LAYOUTS.keys())
