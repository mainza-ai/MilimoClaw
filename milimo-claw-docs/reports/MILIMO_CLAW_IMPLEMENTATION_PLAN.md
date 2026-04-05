> ⚠️ **DEPRECATED** — Historical audit report. Kept for reference only.

---
# Milimo Claw Implementation Plan

**Version:** 1.0
**Date:** March 18, 2026
**Status:** Draft

---

## Overview

This implementation plan addresses the gaps and recommendations identified in the Milimo Claw audit. The plan is organized into three phases aligned with the project roadmap, with clear deliverables, dependencies, and success criteria.

---

## Phase 3: Production Hardening

**Timeline:** Months 1-3
**Goal:** Transition from simulation layer to production-ready distributed system

---

### 3.1 OpenShell Gateway Integration

**Priority:** Critical
**Effort:** 4-6 weeks
**Dependencies:** OpenShell gateway API documentation, multi-sandbox testing environment

#### Objective

Replace the file-based mesh simulation with true inter-sandbox communication via OpenShell gateway.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 3.1.1 | Research OpenShell IPC | Document OpenShell gateway message passing API | `docs/technical/openshell-ipc.md` |
| 3.1.2 | Create Gateway Adapter | Build Python adapter for OpenShell gateway | `milimo-blueprint/orchestrator/gateway_adapter.py` |
| 3.1.3 | Update Mesh Coordinator | Replace file queues with gateway calls | `milimo-blueprint/orchestrator/mesh.py` (modified) |
| 3.1.4 | Implement Message Serialization | Ensure ClawMessage → gateway payload conversion | `milimo-blueprint/orchestrator/gateway_serializer.py` |
| 3.1.5 | Add Connection Management | Handle gateway connection lifecycle | `milimo-blueprint/orchestrator/gateway_connection.py` |
| 3.1.6 | Integration Tests | Test mesh across multiple sandboxes | `test/integration/mesh-integration.test.js` |

#### Success Criteria

- [ ] Message delivery between two sandboxes on same host
- [ ] Message delivery between sandboxes on different hosts (LAN)
- [ ] Latency < 100ms for local mesh communication
- [ ] All existing mesh tests pass with gateway adapter

#### Files to Create/Modify

```
milimo-blueprint/
├── orchestrator/
│   ├── gateway_adapter.py        # NEW
│   ├── gateway_connection.py     # NEW
│   ├── gateway_serializer.py     # NEW
│   └── mesh.py                   # MODIFY
└── tests/
    └── test_gateway_adapter.py   # NEW

test/integration/
└── mesh-integration.test.js      # NEW

docs/technical/
└── openshell-ipc.md              # NEW
```

---

### 3.2 Tool Code Generation

**Priority:** High
**Effort:** 3-4 weeks
**Dependencies:** Evolution cycle framework (complete), LLM prompt engineering

#### Objective

Implement actual tool code generation for evolved tools, replacing the current framework stubs.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 3.2.1 | Design Tool Schema | Define JSON schema for generated tool specifications | `milimo-blueprint/schemas/tool-spec.json` |
| 3.2.2 | Create Prompt Templates | LLM prompts for each tool type (classifier, predictor, optimizer, etc.) | `milimo-blueprint/prompts/tool-generation/*.txt` |
| 3.2.3 | Implement Tool Generator | Python class that generates tool code via LLM | `milimo-blueprint/orchestrator/tool_generator.py` |
| 3.2.4 | Add Code Validation | Static analysis of generated code before deployment | `milimo-blueprint/orchestrator/tool_validator.py` |
| 3.2.5 | Sandbox Testing | Execute generated tools in isolated test environment | `milimo-blueprint/orchestrator/tool_sandbox.py` |
| 3.2.6 | Update Evolution Cycle | Integrate generator into BUILD stage | `milimo-blueprint/orchestrator/evolution_cycle.py` (modified) |

#### Success Criteria

- [ ] Generate working Python tool from pattern observation
- [ ] Generated tool passes backtest with >5% improvement
- [ ] Generated code passes security validation
- [ ] Tool deployed to registry and callable by claw

#### Tool Types to Support

| Type | Description | Example |
|------|-------------|---------|
| `classifier` | Categorizes inputs into predefined classes | Tone classifier, client type scorer |
| `predictor` | Predicts continuous values | Deadline risk score, payment delay probability |
| `optimizer` | Suggests optimal parameters | Timing optimizer, rate advisor |
| `detector` | Identifies anomalies or patterns | Scope creep detector, anomaly detector |
| `generator` | Produces content variants | A/B variant generator |

#### Files to Create/Modify

```
milimo-blueprint/
├── orchestrator/
│   ├── tool_generator.py         # NEW
│   ├── tool_validator.py         # NEW
│   ├── tool_sandbox.py           # NEW
│   └── evolution_cycle.py        # MODIFY
├── schemas/
│   └── tool-spec.json            # NEW
├── prompts/
│   └── tool-generation/
│       ├── classifier.txt        # NEW
│       ├── predictor.txt         # NEW
│       ├── optimizer.txt         # NEW
│       ├── detector.txt          # NEW
│       └── generator.txt         # NEW
└── tests/
    └── test_tool_generator.py    # NEW
```

---

### 3.3 Integration Test Suite

**Priority:** High
**Effort:** 2 weeks
**Dependencies:** None

#### Objective

Create comprehensive integration tests for TypeScript ↔ Python boundary.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 3.3.1 | Create Test Harness | Test runner for TS-Python integration | `test/integration/harness.js` |
| 3.3.2 | Blueprint Manager Tests | Test TS CLI → Python blueprint manager | `test/integration/blueprint-manager.test.js` |
| 3.3.3 | Mesh Coordinator Tests | Test TS CLI → Python mesh coordinator | `test/integration/mesh-coordinator.test.js` |
| 3.3.4 | Privacy Router Tests | Test routing decisions from TS layer | `test/integration/privacy-router.test.js` |
| 3.3.5 | Evolution Cycle Tests | Test full evolution cycle trigger from TS | `test/integration/evolution-cycle.test.js` |
| 3.3.6 | Add CI Pipeline | GitHub Actions workflow for integration tests | `.github/workflows/integration.yml` |

#### Success Criteria

- [ ] All integration tests pass in CI
- [ ] >80% coverage of TS-Python boundary
- [ ] Tests run in <5 minutes

#### Files to Create

```
test/integration/
├── harness.js                        # NEW
├── blueprint-manager.test.js         # NEW
├── mesh-coordinator.test.js          # NEW
├── privacy-router.test.js            # NEW
└── evolution-cycle.test.js           # NEW

.github/workflows/
└── integration.yml                   # NEW
```

---

### 3.4 Rate Limiting

**Priority:** Medium
**Effort:** 1 week
**Dependencies:** None

#### Objective

Implement auto-approval rate limits for free tier compliance.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 3.4.1 | Add Rate Limiter | Token bucket implementation | `milimo/src/warroom/rate-limiter.ts` |
| 3.4.2 | Integrate with Approval Engine | Apply limits before auto-approval | `milimo/src/warroom/approval.ts` (modified) |
| 3.4.3 | Add Configuration | Tier-based rate limit config | `milimo-blueprint/rate-limits.yaml` |
| 3.4.4 | Add Monitoring | Track rate limit metrics | `milimo/src/warroom/rate-limit-metrics.ts` |

#### Rate Limits by Tier

| Tier | Auto-approvals/day | Burst limit |
|------|-------------------|-------------|
| Free | 10 | 3/hour |
| Pro | Unlimited | N/A |

#### Success Criteria

- [ ] Free tier enforces 10 auto-approvals/day
- [ ] Burst limit prevents abuse
- [ ] Rate limit status visible in War Room

#### Files to Create/Modify

```
milimo/
├── src/warroom/
│   ├── rate-limiter.ts           # NEW
│   ├── rate-limit-metrics.ts     # NEW
│   └── approval.ts               # MODIFY

milimo-blueprint/
└── rate-limits.yaml              # NEW
```

---

## Phase 4: Scale & Distribution

**Timeline:** Months 4-6
**Goal:** Enable multi-region deployment and mobile access

---

### 4.1 Multi-Region Mesh Support

**Priority:** High
**Effort:** 4 weeks
**Dependencies:** Phase 3.1 (OpenShell Gateway Integration)

#### Objective

Enable squad members in different geographic regions to participate in the same mesh.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 4.1.1 | Design Mesh Routing | Document multi-region mesh topology | `docs/technical/multi-region-mesh.md` |
| 4.1.2 | Implement Relay Nodes | Optional relay for NAT traversal | `milimo-blueprint/orchestrator/mesh_relay.py` |
| 4.1.3 | Add Region Detection | Auto-detect optimal mesh routing | `milimo-blueprint/orchestrator/region_detector.py` |
| 4.1.4 | Implement Latency Monitoring | Track inter-region latency | `milimo-blueprint/orchestrator/latency_monitor.py` |
| 4.1.5 | Add Failover Logic | Handle node disconnection gracefully | `milimo-blueprint/orchestrator/mesh_failover.py` |

#### Success Criteria

- [ ] Squad members in different AWS regions can communicate
- [ ] Latency < 500ms for inter-region messages
- [ ] Automatic failover when node disconnects
- [ ] Mesh recovers from network partition

#### Files to Create

```
milimo-blueprint/
├── orchestrator/
│   ├── mesh_relay.py             # NEW
│   ├── region_detector.py        # NEW
│   ├── latency_monitor.py        # NEW
│   └── mesh_failover.py          # NEW

docs/technical/
└── multi-region-mesh.md          # NEW
```

---

### 4.2 Mobile War Room Companion

**Priority:** High
**Effort:** 6-8 weeks
**Dependencies:** War Room API abstraction

#### Objective

Build mobile app for approve/veto actions from phone.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 4.2.1 | Design API Layer | REST/WebSocket API for War Room | `docs/technical/war-room-api.md` |
| 4.2.2 | Implement War Room Server | Express/Fastify server for mobile access | `milimo-server/` (new package) |
| 4.2.3 | Build iOS App | React Native iOS application | `milimo-mobile/` (new package) |
| 4.2.4 | Build Android App | React Native Android application | Same as iOS |
| 4.2.5 | Add Push Notifications | Firebase/APNs integration | `milimo-server/notifications/` |
| 4.2.6 | Implement Auth | Secure mobile authentication | `milimo-server/auth/` |

#### Success Criteria

- [ ] Approve/veto actions from mobile
- [ ] Push notifications for urgent items
- [ ] Biometric authentication
- [ ] Offline queue for poor connectivity

#### Files to Create

```
milimo-server/
├── src/
│   ├── server.ts                 # NEW
│   ├── routes/
│   │   ├── pending.ts            # NEW
│   │   ├── actions.ts            # NEW
│   │   └── status.ts             # NEW
│   ├── notifications/
│   │   ├── firebase.ts           # NEW
│   │   └── apns.ts               # NEW
│   └── auth/
│       ├── jwt.ts                # NEW
│       └── biometric.ts          # NEW
├── package.json                  # NEW
└── tsconfig.json                 # NEW

milimo-mobile/
├── src/
│   ├── App.tsx                   # NEW
│   ├── screens/
│   │   ├── PendingList.tsx       # NEW
│   │   ├── ActionDetail.tsx      # NEW
│   │   └── Settings.tsx          # NEW
│   └── components/               # NEW
├── package.json                  # NEW
└── app.json                      # NEW

docs/technical/
└── war-room-api.md               # NEW
```

---

### 4.3 Real-Time Mesh Health Monitoring

**Priority:** Medium
**Effort:** 3 weeks
**Dependencies:** None

#### Objective

Dashboard showing real-time health of all squad claws.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 4.3.1 | Design Health Metrics | Define health score calculation | `docs/technical/health-metrics.md` |
| 4.3.2 | Implement Health Collector | Periodic health aggregation | `milimo-blueprint/orchestrator/health_collector.py` |
| 4.3.3 | Add Health Endpoint | HTTP endpoint for health status | `milimo/src/commands/health.ts` |
| 4.3.4 | Build Dashboard UI | Real-time health visualization | `milimo/src/warroom/health-dashboard.ts` |

#### Health Metrics

| Metric | Weight | Description |
|--------|--------|-------------|
| Heartbeat latency | 30% | Response time for health pings |
| Message throughput | 25% | Messages processed per minute |
| Evolution status | 20% | Last evolution cycle success |
| Approval backlog | 15% | Pending actions in queue |
| Error rate | 10% | Failed operations per hour |

#### Success Criteria

- [ ] Health score calculated for each claw
- [ ] Real-time updates in War Room
- [ ] Alert on health degradation

#### Files to Create

```
milimo-blueprint/
└── orchestrator/
    └── health_collector.py       # NEW

milimo/
├── src/commands/
│   └── health.ts                 # NEW
└── src/warroom/
    └── health-dashboard.ts       # NEW

docs/technical/
└── health-metrics.md             # NEW
```

---

## Phase 5: Blueprint Economy

**Timeline:** Months 7-9
**Goal:** Production-ready marketplace with real transactions

---

### 5.1 Payment Integration

**Priority:** Critical
**Effort:** 4 weeks
**Dependencies:** Legal review, payment provider selection

#### Objective

Implement real payment processing for blueprint marketplace.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 5.1.1 | Select Payment Provider | Evaluate Stripe, PayPal, crypto options | `docs/technical/payment-provider-selection.md` |
| 5.1.2 | Implement Payment Service | Backend for payment processing | `milimo-server/payments/` |
| 5.1.3 | Add Platform Fee Logic | 10% fee calculation and distribution | `milimo-server/payments/fee-calculator.ts` |
| 5.1.4 | Implement Payouts | Seller payout processing | `milimo-server/payments/payouts.ts` |
| 5.1.5 | Add Invoice Generation | Transaction receipts and invoices | `milimo-server/payments/invoices.ts` |
| 5.1.6 | Build Payment UI | Checkout flow in marketplace | `milimo/src/commands/payment.ts` |

#### Success Criteria

- [ ] Process real credit card payments
- [ ] Platform fee automatically deducted
- [ ] Sellers receive payouts within 7 days
- [ ] Full audit trail for accounting

#### Files to Create

```
milimo-server/
└── payments/
    ├── stripe.ts                 # NEW
    ├── fee-calculator.ts         # NEW
    ├── payouts.ts                # NEW
    ├── invoices.ts               # NEW
    └── webhooks.ts               # NEW

docs/technical/
└── payment-provider-selection.md # NEW
```

---

### 5.2 Cryptographic Provenance Verification

**Priority:** High
**Effort:** 3 weeks
**Dependencies:** None

#### Objective

Implement strong cryptographic proof of blueprint operational history.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 5.2.1 | Design Provenance Scheme | Document cryptographic approach | `docs/technical/provenance-scheme.md` |
| 5.2.2 | Implement Signing | Sign blueprints with Ed25519 | `milimo-blueprint/orchestrator/provenance_signer.py` |
| 5.2.3 | Implement Verification | Verify blueprint signatures | `milimo-blueprint/orchestrator/provenance_verifier.py` |
| 5.2.4 | Add Chain Validation | Validate full provenance chain | `milimo-blueprint/orchestrator/chain_validator.py` |
| 5.2.5 | Build Verification UI | Show verification status in marketplace | `milimo/src/commands/verify.ts` |

#### Success Criteria

- [ ] All published blueprints cryptographically signed
- [ ] Provenance chain verifiable from origin
- [ ] Tampering detection

#### Files to Create

```
milimo-blueprint/
└── orchestrator/
    ├── provenance_signer.py      # NEW
    ├── provenance_verifier.py    # NEW
    └── chain_validator.py        # NEW

milimo/
└── src/commands/
    └── verify.ts                 # NEW

docs/technical/
└── provenance-scheme.md          # NEW
```

---

### 5.3 Blueprint Performance Verification

**Priority:** Medium
**Effort:** 3 weeks
**Dependencies:** 5.2 (Cryptographic Provenance)

#### Objective

Allow sellers to prove claimed performance metrics.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 5.3.1 | Design Attestation Format | JSON format for performance claims | `milimo-blueprint/schemas/performance-attestation.json` |
| 5.3.2 | Implement Attestation Generator | Create signed performance claims | `milimo-blueprint/orchestrator/attestation_generator.py` |
| 5.3.3 | Add Third-Party Verification | Optional auditor verification | `docs/technical/third-party-verification.md` |
| 5.3.4 | Build Verification Badge | UI indicator for verified performance | `milimo/src/commands/badge.ts` |

#### Success Criteria

- [ ] Sellers can generate performance attestations
- [ ] Attestations linked to provenance chain
- [ ] Buyers can verify claims before purchase

#### Files to Create

```
milimo-blueprint/
├── schemas/
│   └── performance-attestation.json  # NEW
└── orchestrator/
    └── attestation_generator.py      # NEW

milimo/
└── src/commands/
    └── badge.ts                      # NEW

docs/technical/
└── third-party-verification.md       # NEW
```

---

## Phase 6: Enterprise & University Tier

**Timeline:** Months 10-12
**Goal:** White-label deployment and institutional partnerships

---

### 6.1 University Enterprise Tier

**Priority:** Medium
**Effort:** 6 weeks
**Dependencies:** Phase 5 complete

#### Objective

White-label deployment for university entrepreneurship programs.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 6.1.1 | Design Tenant Architecture | Multi-tenant deployment model | `docs/technical/multi-tenant.md` |
| 6.1.2 | Implement Tenant Management | Create/manage university tenants | `milimo-server/tenants/` |
| 6.1.3 | Add Custom Branding | White-label UI configuration | `milimo-admin/branding/` |
| 6.1.4 | Build Admin Dashboard | University administrator interface | `milimo-admin/dashboard/` |
| 6.1.5 | Implement Custom Blueprints | University-specific template library | `milimo-admin/templates/` |
| 6.1.6 | Add Usage Analytics | Per-tenant usage reporting | `milimo-admin/analytics/` |

#### Success Criteria

- [ ] Deploy branded instance for university
- [ ] Admin can manage student squads
- [ ] Custom blueprint library per tenant
- [ ] Usage analytics for program reporting

#### Files to Create

```
milimo-server/
└── tenants/
    ├── manager.ts                # NEW
    ├── provisioning.ts           # NEW
    └── limits.ts                 # NEW

milimo-admin/
├── src/
│   ├── dashboard/
│   │   ├── Overview.tsx          # NEW
│   │   ├── Squads.tsx            # NEW
│   │   └── Analytics.tsx         # NEW
│   ├── branding/
│   │   ├── Logo.tsx              # NEW
│   │   └── Theme.tsx             # NEW
│   └── templates/
│       └── TemplateManager.tsx   # NEW
├── package.json                  # NEW
└── tsconfig.json                 # NEW

docs/technical/
└── multi-tenant.md               # NEW
```

---

### 6.2 Squad Formation Automation

**Priority:** Medium
**Effort:** 3 weeks
**Dependencies:** 6.1

#### Objective

Automated mesh formation for incubator cohorts.

#### Tasks

| # | Task | Description | Deliverable |
|---|------|-------------|-------------|
| 6.2.1 | Design Cohort Template | Bulk squad creation schema | `milimo-blueprint/schemas/cohort.json` |
| 6.2.2 | Implement Batch Onboarding | Create multiple squads from template | `milimo-blueprint/orchestrator/cohort_creator.py` |
| 6.2.3 | Add Role Assignment | Auto-assign roles based on cohort config | `milimo-blueprint/orchestrator/role_assigner.py` |
| 6.2.4 | Build Cohort Dashboard | Admin view of cohort progress | `milimo-admin/dashboard/Cohorts.tsx` |

#### Success Criteria

- [ ] Admin creates cohort of 50+ squads in one action
- [ ] Automatic role assignment
- [ ] Cohort progress visible in admin dashboard

#### Files to Create

```
milimo-blueprint/
├── schemas/
│   └── cohort.json               # NEW
└── orchestrator/
    ├── cohort_creator.py         # NEW
    └── role_assigner.py          # NEW

milimo-admin/
└── src/dashboard/
    └── Cohorts.tsx               # NEW
```

---

## Summary Timeline

| Phase | Duration | Key Deliverable |
|-------|----------|-----------------|
| 3: Production Hardening | Months 1-3 | OpenShell integration, tool generation, integration tests |
| 4: Scale & Distribution | Months 4-6 | Multi-region mesh, mobile app, health monitoring |
| 5: Blueprint Economy | Months 7-9 | Payment processing, provenance verification |
| 6: Enterprise Tier | Months 10-12 | University white-label, cohort automation |

---

## Resource Requirements

### Engineering

- **Backend Engineers (Python):** 2 FTE for phases 3-6
- **Frontend Engineers (TypeScript/React):** 1 FTE for phases 4-6
- **Mobile Engineers (React Native):** 1 FTE for phase 4
- **DevOps/Infrastructure:** 0.5 FTE for phases 3-6

### Infrastructure

- **Staging Environment:** Multi-region test mesh
- **CI/CD Pipeline:** GitHub Actions with integration test matrix
- **Payment Provider Account:** Stripe or equivalent
- **Push Notification Service:** Firebase/APNs

### External Dependencies

- OpenShell gateway API stability
- NVIDIA NemoClaw compatibility
- Payment provider approval
- Legal review for marketplace terms

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OpenShell API changes | Medium | High | Abstract gateway layer, version pinning |
| Payment provider rejection | Low | High | Multiple provider options, pre-approval |
| Mobile app store rejection | Low | Medium | Follow platform guidelines, beta testing |
| Performance at scale | Medium | Medium | Load testing, caching, optimization |

---

## Success Metrics

### Phase 3

- 100% integration test pass rate
- <100ms mesh message latency
- Generated tools pass backtest

### Phase 4

- <500ms inter-region latency
- 1000+ mobile users
- 99.5% mesh uptime

### Phase 5

- $10K+ monthly marketplace volume
- <1% payment failure rate
- All blueprints cryptographically signed

### Phase 6

- 5+ university partnerships
- 500+ squads per university cohort
- 90%+ customer satisfaction

---

**Implementation Plan Complete**
