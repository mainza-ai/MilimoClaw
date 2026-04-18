# File Structure

**Summary**: Complete project file map for MilimoClaw.

**Sources**: Project filesystem scan

**Last updated**: 2026-04-14

**Tags**: #reference #structure #files

---

## Root Directory

```
/Users/mck/Desktop/MilimoClaw/
├── .agents/              # Agent configuration and skills
├── .github/              # GitHub workflows and templates
├── .kilo/                # Kilo development/planning tool
├── .openclaw/            # OpenClaw configuration
├── assets/               # Images and logos
├── ci/                   # CI configuration
├── docs/                 # Root documentation
├── ISSUE_TEMPLATE/       # GitHub issue templates
├── k8s/                  # Kubernetes deployment configs
├── milimo/               # TypeScript CLI plugin
├── milimo-admin/         # Admin panel (TypeScript)
├── milimo-blueprint/     # Python backend
├── milimo-claw-docs/     # Comprehensive documentation
├── milimo-claw-wiki/     # Obsidian vault
├── milimo-mobile/        # Mobile app (React Native)
├── milimo-server/        # Backend server (TypeScript/Express)
├── plans/                # Implementation plans
├── scripts/              # Utility scripts
└── test/                 # Integration tests
```

---

## milimo-blueprint/ — Python Backend

```
milimo-blueprint/
├── orchestrator/              # Main claw implementations
│   ├── analytics/             # Analytics Claw (15 modules)
│   │   ├── analytics_claw.py
│   │   ├── analytics_init.py
│   │   ├── analytics_scheduler.py
│   │   ├── anomaly_detector.py
│   │   ├── baseline_manager.py
│   │   ├── collection_workers.py
│   │   ├── data_collectors.py
│   │   ├── forward_projector.py
│   │   ├── opportunity_scorer.py
│   │   ├── query_handler.py
│   │   ├── report_generator.py
│   │   ├── signal_dispatcher.py
│   │   └── signal_processor.py
│   │
│   ├── build/                 # Build Claw (13 modules)
│   │   ├── build_claw.py
│   │   ├── build_init.py
│   │   ├── build_scheduler.py
│   │   ├── code_generator.py
│   │   ├── cost_monitor.py
│   │   ├── dependency_auditor.py
│   │   ├── deploy_manager.py
│   │   ├── doc_maintainer.py
│   │   ├── error_monitor.py
│   │   ├── issue_manager.py
│   │   ├── pr_manager.py
│   │   ├── sentry_client.py
│   │   └── vercel_client.py
│   │
│   ├── content/               # Content Claw (11 modules)
│   │   ├── content_claw.py
│   │   ├── content_init.py
│   │   ├── content_generator.py
│   │   ├── content_scheduler.py
│   │   ├── brief_manager.py
│   │   ├── brand_voice.py
│   │   ├── platform_publisher.py
│   │   ├── performance_monitor.py
│   │   ├── publish_scheduler.py
│   │   └── approval_handler.py
│   │
│   ├── finance/               # Finance Claw (12 modules)
│   │   ├── finance_claw.py
│   │   ├── finance_init.py
│   │   ├── finance_scheduler.py
│   │   ├── pricing_engine.py
│   │   ├── invoice_manager.py
│   │   ├── payment_monitor.py
│   │   ├── payment_risk_scorer.py
│   │   ├── expense_tracker.py
│   │   ├── revenue_tracker.py
│   │   ├── stripe_client.py
│   │   └── signal_dispatcher.py
│   │
│   ├── ops/                   # Ops Claw (13 modules)
│   │   ├── ops_claw.py
│   │   ├── ops_init.py
│   │   ├── ops_scheduler.py
│   │   ├── intake_manager.py
│   │   ├── project_manager.py
│   │   ├── comms_manager.py
│   │   ├── scope_monitor.py
│   │   ├── health_scorer.py
│   │   ├── incident_analyzer.py
│   │   ├── runbook_executor.py
│   │   ├── webhook_server.py
│   │   └── signal_dispatcher.py
│   │
│   ├── evolution/             # Evolution system
│   │   └── sandbox_runner.py
│   │
│   └── [root modules]        # Core orchestrator modules
│       ├── contracts.py       # Message schemas
│       ├── mesh.py            # Mesh coordinator
│       ├── claw_launcher.py   # Claw launcher
│       ├── privacy_router.py  # Privacy routing
│       ├── evolution_cycle.py # Evolution cycle
│       └── [25+ more modules]
│
├── roles/                     # Claw role definitions
│   ├── analytics-claw.yaml
│   ├── build-claw.yaml
│   ├── content-claw.yaml
│   ├── finance-claw.yaml
│   └── ops-claw.yaml
│
├── policies/                  # Sandbox policies
│   ├── analytics-sandbox.yaml
│   ├── assistant-sandbox.yaml
│   ├── build-sandbox.yaml
│   ├── content-sandbox.yaml
│   ├── finance-sandbox.yaml
│   └── ops-sandbox.yaml
│
├── templates/                 # Squad templates
│   ├── solo-founder.yaml
│   ├── ai-micro-saas.yaml
│   ├── campus-ai-tool.yaml
│   ├── content-agency.yaml
│   ├── design-studio.yaml
│   ├── event-promotion.yaml
│   └── freelance-collective.yaml
│
├── schemas/                   # JSON schemas
├── prompts/                   # Tool generation prompts
└── tests/                     # Python tests
```

---

## milimo/ — TypeScript CLI

```
milimo/
├── src/
│   ├── index.ts              # Plugin entry point
│   ├── cli.ts                # Command registration
│   ├── commands/             # CLI commands (14 files)
│   │   ├── action.ts
│   │   ├── assistant.ts
│   │   ├── badge.ts
│   │   ├── blueprint.ts
│   │   ├── init.ts
│   │   ├── logs.ts
│   │   ├── onboard.ts
│   │   ├── payment.ts
│   │   ├── slash.ts
│   │   ├── squad.ts
│   │   ├── verify.ts
│   │   └── warroom.ts
│   │
│   ├── warroom/              # War Room TUI (12 files)
│   │   ├── warroom-tui.ts
│   │   ├── approval.ts
│   │   ├── audit.ts
│   │   ├── digest.ts
│   │   ├── evolution.ts
│   │   ├── health-*.ts
│   │   ├── notifier.ts
│   │   ├── rate-limiter.ts
│   │   └── realtime-bridge.ts
│   │
│   ├── mesh/                 # Mesh protocol
│   ├── lib/                  # Shared utilities
│   └── onboard/              # Onboarding flows
│
├── __tests__/                # TypeScript tests
└── dist/                     # Compiled output
```

---

## milimo-claw-docs/ — Documentation

```
milimo-claw-docs/
├── ARCHITECTURE.md           # Technical architecture
├── CLI_REFERENCE.md          # CLI documentation
├── CHANGELOG.md              # Version history
├── BLUEPRINT_ECONOMY.md      # Blueprint marketplace
├── PRIVACY_AND_SECURITY.md   # Security guide
├── MILIMO_CLAW_PROJECT_DESCRIPTION.md  # Full product spec
│
├── guides/                   # User guides (7 files)
├── prompts/                  # Implementation prompts (10 files)
├── reference/                # Spec documents (8 files)
├── reports/                  # Audit reports (30+ files)
├── troubleshooting/          # Troubleshooting (6 files)
├── blog/                     # Blog posts
└── stripe/                   # Stripe documentation
```

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Environment template |
| `package.json` | Node.js project config |
| `pyproject.toml` | Python project config |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Container build |
| `Makefile` | Build automation |
| `install.sh` | Main installer |
| `mesh_config.yaml` | Mesh configuration |
| `evolution_config.yaml` | Evolution settings |

---

## Related Pages

- [[system-overview]] — Architecture overview
- [[ground-truth-hierarchy]] — Document authority
- [[testing]] — Test locations
