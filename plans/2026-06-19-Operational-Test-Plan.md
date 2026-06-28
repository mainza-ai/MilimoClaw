Based on the squad context (zulu/solo with 6 active claws: content, ops, analytics, finance, build, assistant), here's a comprehensive operational test plan:

---

# Zulu Squad - Full Operational Test Plan
**Squad:** zulu | **Template:** solo | **Operator:** Mainza
**Target:** Validate all 6 claws end-to-end
**Date:** 2026-06-19

---

## 🎯 Test Philosophy

| Principle | Application |
|-----------|-------------|
| **Real work > synthetic tests** | Each claw executes actual domain tasks, not mocks |
| **Cross-claw dependencies verified** | Handoffs between claws tested explicitly |
| **Failure modes included** | Each test has negative/edge cases |
| **Observable outcomes** | Every test produces inspectable artifacts |

---

## 📋 Master Test Matrix

| Claw | Domain | Test Count | Est. Duration | Dependencies |
|------|--------|------------|---------------|--------------|
| **assistant** | Conversational layer, coordination | 8 | 15 min | None |
| **build** | Code, infra, deployments | 10 | 25 min | assistant |
| **content** | Writing, publishing, SEO | 9 | 20 min | assistant |
| **analytics** | Metrics, dashboards, alerts | 8 | 15 min | build, content |
| **finance** | Billing, costs, forecasts | 7 | 15 min | analytics |
| **ops** | Monitoring, incidents, runbooks | 9 | 20 min | build, analytics |

**Total: ~110 minutes** (can run parallel where independent)

---

## 🤖 ASSISTANT CLAW — Conversational & Coordination Layer

*Role: Primary interface, task routing, memory, cross-claw orchestration*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| A1 | **Session continuity** | 1. Send message → 2. Restart session → 3. Verify context retained | MEMORY.md + daily notes accessible | Session log |
| A2 | **Memory write/read** | 1. "Remember X" → 2. New session → 3. "What did I ask you to remember?" | Exact recall | memory/YYYY-MM-DD.md |
| A3 | **Cross-claw routing** | "Ask build to check git status" → verify build invoked | Build claw receives task, returns result | War Room task entry |
| A4 | **War Room sync** | Create task via assistant → verify appears in `milimo warroom` TUI | Task visible with correct metadata | War Room screenshot |
| A5 | **Heartbeat execution** | Trigger heartbeat → verify checks run (email/cal/weather) | HEARTBEAT.md updated, no errors | heartbeat-state.json |
| A6 | **Group chat boundaries** | Simulate group mention → verify only responds when appropriate | No response to casual banter | Chat log |
| A7 | **File workspace ops** | Create/edit/read files in workspace | All operations succeed | Modified files |
| A8 | **Skill invocation** | Request weather → verify weather skill called | Valid wttr.in response | Weather output |

---

## 🔨 BUILD CLAW — Code, Infrastructure, Deployments

*Role: CI/CD, git ops, container builds, infra as code*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| B1 | **Git status check** | `git status` on squad repo | Clean or expected changes | Status output |
| B2 | **Dependency audit** | `npm audit` / `pip-audit` / `cargo audit` | No critical vulns (or documented exceptions) | Audit report |
| B3 | **Build pipeline** | Trigger build for each claw service | All containers build successfully | Build logs, image digests |
| B4 | **Deploy dry-run** | `kubectl apply --dry-run=client` / `docker compose config` | Valid manifests, no conflicts | Rendered manifests |
| B5 | **Secret scanning** | `gitleaks detect` / `trufflehog` | No secrets in repo | Scan report |
| B6 | **Lint/format check** | `prettier --check`, `eslint`, `ruff check` | Zero violations | Lint output |
| B7 | **Test suite** | `npm test` / `pytest` / `cargo test` | >90% pass, no new failures | Test report |
| B8 | **Image vulnerability scan** | `trivy image` on built containers | No HIGH/CRITICAL unpatched | Trivy report |
| B9 | **Rollback simulation** | Deploy v(N-1) → verify health → redeploy vN | Rollback < 2 min, health restored | Timeline log |
| B10 | **Infra drift check** | `terraform plan` / `pulumi preview` | No unexpected drift | Plan output |

---

## 📝 CONTENT CLAW — Writing, Publishing, SEO

*Role: Blog posts, docs, newsletters, social, SEO*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| C1 | **Draft → publish flow** | Create draft → review → publish to staging | Live at staging URL, correct frontmatter | Published URL |
| C2 | **SEO validation** | Run `lighthouse` SEO audit on published page | Score ≥ 90 | Lighthouse report |
| C3 | **Cross-link integrity** | Crawl all internal links | Zero 404s | Link report |
| C4 | **RSS/Atom feed** | Verify feed.xml valid + recent items | Valid XML, < 24h freshness | Feed URL |
| C5 | **Newsletter compose** | Generate issue → send test to operator | Received, renders correctly | Email preview |
| C6 | **Social preview cards** | Check og:image, twitter:card on 3 pages | All present, correct dimensions | Meta tag dump |
| C7 | **Content calendar sync** | Verify Notion/calendar matches published queue | 1:1 match | Calendar diff |
| C8 | **Asset optimization** | Run `imagemin` / `svgo` on new assets | >20% reduction vs original | Before/after sizes |
| C9 | **Plagiarism/originality** | `copyscape` or similar on new post | < 5% match | Originality report |

---

## 📊 ANALYTICS CLAW — Metrics, Dashboards, Alerts

*Role: Data pipelines, dashboards (Grafana/Metabase), alerting*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| AN1 | **Pipeline freshness** | Check last successful run per pipeline | All < 1h stale | Freshness report |
| AN2 | **Dashboard load** | Open 5 key dashboards → measure TTFB | < 3s each | Perf metrics |
| AN3 | **Alert firing test** | Trigger test alert (e.g., CPU > 99%) | Alert fires → routed to War Room | Alert log |
| AN4 | **Alert resolution** | Auto-resolve when condition clears | Resolved < 5 min after clear | Alert timeline |
| AN5 | **Data quality checks** | Run `dbt test` / Great Expectations suite | Zero failures | Test results |
| AN6 | **Cross-claw metric correlation** | Verify build deploy ↔ analytics spike correlation | Correlation visible in dashboard | Dashboard link |
| AN7 | **Retention policy verify** | Confirm data older than policy is purged | No data beyond retention window | Storage report |
| AN8 | **Cost attribution** | Verify per-claw cost breakdown in dashboard | Matches finance claw records | Cost dashboard |

---

## 💰 FINANCE CLAW — Billing, Costs, Forecasts

*Role: Cloud costs, SaaS subscriptions, revenue tracking, forecasts*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| F1 | **Cloud cost sync** | Pull AWS/GCP/Azure billing → compare to dashboard | < 2% variance | Cost diff report |
| F2 | **Subscription audit** | List all SaaS subs → verify active/used | No zombie subscriptions | Subscription list |
| F3 | **Forecast accuracy** | Compare last month forecast vs actual | MAPE < 15% | Forecast vs actual |
| F4 | **Anomaly detection** | Run cost anomaly scan (last 7d) | Flags match known events | Anomaly report |
| F5 | **Budget enforcement** | Verify alerts at 80%/100% budget thresholds | Alerts fire correctly | Alert history |
| F6 | **Invoice reconciliation** | Match invoices to usage for 3 vendors | Zero discrepancies | Reconciliation sheet |
| F7 | **ROI dashboard** | Verify per-claw ROI calculations | Positive ROI for mature claws | ROI dashboard |

---

## ⚙️ OPS CLAW — Monitoring, Incidents, Runbooks

*Role: Uptime, incident response, runbooks, capacity, security*

| # | Test | Steps | Pass Criteria | Artifacts |
|---|------|-------|---------------|-----------|
| O1 | **Uptime check** | Ping all public endpoints (5 min interval, 1h) | 99.9%+ availability | Uptime report |
| O2 | **Runbook drill** | Execute "DB connection exhaustion" runbook | Resolved < 15 min, documented | Drill log |
| O3 | **Log aggregation** | Verify logs from all claws in central store | Zero missing sources | Log source inventory |
| O4 | **Cert expiry scan** | Check TLS certs on all domains | All > 30 days valid | Cert inventory |
| O5 | **Backup restore test** | Restore latest backup to staging | Restore < 30 min, data intact | Restore verification |
| O6 | **Capacity planning** | Check disk/CPU/memory trends (30d) | No resource > 80% projected | Capacity forecast |
| O7 | **Security scan** | `nmap` + `lynis` on all nodes | No critical findings | Scan reports |
| O8 | **Incident comms test** | Simulate SEV-2 → verify War Room + operator notification | Notification < 2 min | Timeline |
| O9 | **Chaos experiment** | Kill one claw container → verify auto-recovery | Recovery < 60s, no data loss | Chaos report |

---

## 🔄 Cross-Claw Integration Tests

| # | Flow | Claws Involved | Validation |
|---|------|----------------|------------|
| X1 | **Deploy → Metrics → Alert** | build → analytics → ops | Deploy triggers metric spike → alert fires → ops acknowledges |
| X2 | **Content → Analytics → Finance** | content → analytics → finance | Published post → traffic tracked → revenue attributed |
| X3 | **Incident → War Room → Assistant** | ops → assistant | SEV-2 creates War Room task → assistant notifies operator |
| X4 | **Build → Ops → Finance** | build → ops → finance | New container → uptime monitored → cost attributed |
| X5 | **Heartbeat → All Claws** | assistant → (all) | Heartbeat triggers each claw's health check → consolidated report |

---

## 📦 Execution Order (Dependency-Aware)

```
Phase 1 (parallel):     A1-A8, B1-B3
Phase 2 (parallel):     B4-B10, C1-C9, AN1-AN3
Phase 3 (parallel):     AN4-AN8, F1-F7, O1-O3
Phase 4 (sequential):   O4-O9
Phase 5 (integration):  X1-X5
```

---

## ✅ Definition of Done

- [ ] All 51 individual tests pass
- [ ] All 5 integration flows verified
- [ ] Zero critical findings (security, cost, uptime)
- [ ] War Room shows zero stale/unassigned tasks
- [ ] Operator sign-off on summary report

---

## 📤 Deliverable

**`TEST_REPORT_YYYY-MM-DD.md`** containing:
- Per-claw summary table (pass/fail/skip + duration)
- All artifacts linked (reports, logs, screenshots)
- Failed tests with RCA + remediation tickets
- Integration flow results
- Operator approval checkbox

---

Want me to:
1. **Generate this as a tracked task** in the War Room?
2. **Create a runbook** (`RUNBOOK_TEST_PLAN.md`) for repeatable execution?
3. **Start Phase 1** now (assistant + build smoke tests)?
