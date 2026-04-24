# Milimo Claw
## Project Description — v1.0

> *"Your friend group is a startup. Your laptops are the infrastructure. Your claws do the work."*

> **On the name:** *Milimo* (mi-LEE-mo) is a Zambian name from the Tonga people, meaning **"works," "tasks," or "labour."** It is the most honest name a hustle platform has ever had.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Problem](#2-the-problem)
3. [The Insight](#3-the-insight)
4. [What Is Milimo Claw](#4-what-is-milimo-claw)
5. [NemoClaw Architecture — Full Exploitation](#5-nemoclaw-architecture--full-exploitation)
6. [Product Features](#6-product-features)
7. [User Roles & The Squad Model](#7-user-roles--the-squad-model)
8. [Core User Flows](#8-core-user-flows)
9. [Self-Evolving Intelligence Loop](#9-self-evolving-intelligence-loop)
10. [Blueprint Economy](#10-blueprint-economy)
11. [Tech Stack](#11-tech-stack)
12. [Go-To-Market Strategy](#12-go-to-market-strategy)
13. [Monetization](#13-monetization)
14. [Competitive Landscape](#14-competitive-landscape)
15. [Moats & Defensibility](#15-moats--defensibility)
16. [Milestones & Roadmap](#16-milestones--roadmap)
17. [Risk & Mitigation](#17-risk--mitigation)
18. [Why Now](#18-why-now)

---

## 1. Executive Summary

**Milimo Claw** is a multi-agent autonomous hustle platform built entirely on top of NVIDIA NemoClaw. It turns a squad of college students — each running a NemoClaw sandbox on their RTX laptop — into a coordinated AI-powered business operation that runs 24/7, whether they're in class, asleep, or out.

Each person in the squad deploys a self-evolving NemoClaw claw that specializes in one business function: content creation, client operations, analytics, finance, or engineering. The claws communicate through the OpenShell gateway, coordinate work across a shared project pipeline, and get smarter autonomously every week. Blueprint versioning means the squad's accumulated intelligence is a forkable, tradeable artifact — a startup that outlives its founders.

Milimo Claw is not an app. It is infrastructure. It is the first product to exploit every layer of the NemoClaw stack simultaneously for a consumer use case — and the first to turn friend-group laptops into a distributed AI company.

**Target audience:** College students aged 18–24 with RTX-capable laptops who want to monetize their skills collectively without the coordination overhead of a traditional freelance operation.

**One-line pitch:** *Milimo Claw is what happens when your squad's laptops form a company at 2am and keep running it forever.*

---

## 2. The Problem

### 2.1 The College Hustle is Real — But Chaotic

An estimated 70% of Gen Z want to start a business. Over 45% of college students actively freelance or side-hustle. The hustle is not the problem. The problem is coordination.

- The writer has to remind the designer the deadline moved
- The designer doesn't know the client changed the brief
- The person managing the inbox didn't tell anyone about the new client inquiry
- Finals week kills momentum for everyone simultaneously
- When someone graduates, everything they knew walks out with them

Today's tools — Notion, Trello, Discord, Fiverr, Google Docs — are designed for human coordination at human speed. They require attention. They require discipline. They demand that students choose between their grades and their hustle.

### 2.2 AI Tools Exist, But They Are Dumb and Reactive

Current AI tools (ChatGPT, Claude, Gemini) are assistants. You prompt them, they respond, they forget everything the next session. They don't grow. They don't specialize. They don't run without you.

They are also generic. A content generation tool doesn't know that your client hates Oxford commas, that your audience peaks on Tuesday at 9pm, or that your best-performing posts always have a specific emotional arc your squad perfected over six months. The generic tool produces generic output.

### 2.3 The Student Squad Has No Infrastructure Built for It

There is zero tooling today that:
- Treats a group of friends as a distributed business unit
- Lets each person contribute their specialty without stepping on each other
- Runs the operation when nobody is watching
- Preserves and compounds knowledge between members and across graduating cohorts
- Does all of this privately, on-device, without subscription fees per seat

This gap is enormous and completely unaddressed.

---

## 3. The Insight

**The NemoClaw multi-sandbox architecture, combined with self-evolving claws and blueprint versioning, makes something new possible: a company where every department is an AI agent that gets smarter every week, coordinates with each other through a policy-governed gateway, and can't accidentally cross department boundaries or expose confidential data.**

That is not a feature. That is a new category of product — one that didn't exist before NemoClaw.

The specific insight: **the OpenShell inter-sandbox gateway is the organizational chart.** Each sandbox is a department. Each claw is the department head. The policy layer is the employment contract. Blueprint versioning is institutional memory.

You don't need to build a company. You deploy one.

---

## 4. What Is Milimo Claw

Milimo Claw is a platform with three layers:

### Layer 1: The Claw Deployment Kit
A one-command installer that takes a student from zero to a running NemoClaw sandbox in under 10 minutes. The kit includes:
- A curated menu of starter blueprint templates organized by category: Creative & Content, Commerce & Services, and Tech Startups — with a fifth Build Claw role exclusive to tech squads
- Role-specific claw configurations (Content, Ops, Analytics, Finance, Build, and Assistant for tech squads — detailed in Section 6.1)
- A guided squad onboarding wizard that establishes the inter-sandbox mesh for the group

### Layer 2: The Squad Mesh
The infrastructure layer that connects each member's claw through the OpenShell gateway. Establishes:
- Shared project pipeline visible to all sandboxes
- Policy-governed inter-claw messaging (what each claw can say to each other, and when)
- A collective operator approval dashboard — the "War Room" — where the whole squad reviews and approves pending actions from all claws simultaneously

### Layer 3: The Blueprint Economy
A marketplace where squads share, fork, and sell their evolved blueprints. A blueprint encodes months of learned intelligence — client communication patterns, content cadences, pricing rules, platform-specific strategies. A sophomore buys a senior's evolved agency blueprint and inherits a running head start.

---

## 5. NemoClaw Architecture — Full Exploitation

This section documents exactly how every NemoClaw capability is exploited. This is the technical moat.

### 5.1 Multi-Sandbox Mesh = Organizational Chart

Each squad member deploys one primary NemoClaw sandbox on their RTX laptop. The squad is a distributed mesh — each sandbox running one specialized claw, each claw on a different physical machine, all coordinated through the OpenShell gateway. No central server. No shared cloud environment. The company runs across the squad's laptops.

**Creative & Commerce squad (4-claw mesh):**

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MILIMO CLAW MESH                             │
│                                                                      │
│  [Laptop A]               [Laptop B]               [Laptop C]        │
│  ┌─────────────────┐      ┌─────────────────┐      ┌──────────────┐  │
│  │  CONTENT CLAW   │      │    OPS CLAW     │      │  ANALYTICS   │  │
│  │  /sandbox/      │      │  /sandbox/      │      │    CLAW      │  │
│  │  content        │      │  clients        │      │  /sandbox/   │  │
│  │  OpenShell GW ──┼──────┼── OpenShell GW ─┼──────┼─ OpenShell GW│  │
│  └─────────────────┘      └─────────────────┘      └──────────────┘  │
│           │                        │                       │          │
│           └────────────────────────┼───────────────────────┘          │
│                                    │                                  │
│                     ╔══════════════╧══════════════╗                  │
│                     ║    INTER-SANDBOX CHANNEL     ║                  │
│                     ║  (typed contracts · logged · ║                  │
│                     ║   policy-enforced by OpenShell)                 │
│                     ╚══════════════╤══════════════╝                  │
│                                    │                                  │
│                           [Laptop D]                                  │
│                      ┌─────────────────┐                             │
│                      │  FINANCE CLAW   │                             │
│                      │  /sandbox/      │                             │
│                      │  finance        │                             │
│                      │  OpenShell GW ──┘                             │
│                      └─────────────────┘                             │
│                                                                      │
│  ══════════════════════════════════════════════════════════════════  │
│                         WAR ROOM (TUI)                               │
│           Every squad member · every pending action · one view       │
└──────────────────────────────────────────────────────────────────────┘
```

**Tech squad (5-claw mesh — adds Build Claw; 6-claw mesh with Assistant):**

```
┌──────────────────────────────────────────────────────────────────────┐
│                         MILIMO CLAW MESH                             │
│                                                                      │
│  [Laptop A]          [Laptop B]          [Laptop C]    [Laptop D]    │
│  ┌────────────┐      ┌────────────┐      ┌──────────┐  ┌──────────┐  │
│  │  CONTENT   │      │    OPS     │      │ANALYTICS │  │ FINANCE  │  │
│  │   CLAW     │      │   CLAW     │      │  CLAW    │  │  CLAW    │  │
│  │ OpenShell ─┼──────┼─ OpenShell ┼──────┼OpenShell ┼──┼OpenShell │  │
│  └────────────┘      └────────────┘      └──────────┘  └──────────┘  │
│        │                   │                  │              │        │
│        └───────────────────┴──────────────────┴──────────────┘        │
│                                    │                                  │
│                     ╔══════════════╧══════════════╗                  │
│                     ║    INTER-SANDBOX CHANNEL     ║                  │
│                     ║  (typed contracts · logged · ║                  │
│                     ║   policy-enforced by OpenShell)                 │
│                     ╚══════════════╤══════════════╝                  │
│                                    │                                  │
│                           [Laptop E]                                  │
│                      ┌─────────────────────┐                         │
│                      │     BUILD CLAW      │                         │
│                      │  /sandbox/build     │                         │
│                      │  (codebase · secrets│                         │
│                      │   · deploy configs) │                         │
│                      │  OpenShell GW ──────┘                         │
│                      └─────────────────────┘                         │
│                                                                      │
│  ══════════════════════════════════════════════════════════════════  │
│                         WAR ROOM (TUI)                               │
│           Every squad member · every pending action · one view       │
└──────────────────────────────────────────────────────────────────────┘
```

**What the diagrams show that the earlier version missed:**

Each sandbox exposes its filesystem mount label — `/sandbox/content`, `/sandbox/clients`, `/sandbox/finance`, `/sandbox/build` — because the mount is as architecturally significant as the claw role itself. It defines what the claw can see. A claw cannot operate outside its mount. The Finance Claw cannot read `/sandbox/clients`. The Build Claw cannot read `/sandbox/finance`. These are not access control lists enforced by software convention — they are Landlock kernel-level filesystem restrictions that cannot be bypassed by any instruction the claw receives.

**The inter-sandbox channel is not a chat API.** Every message that crosses the channel is a typed contract — a structured payload with a defined schema, a declared sender, a declared recipient, and a declared message type. The OpenShell gateway validates each message against the sending claw's outbound policy and the receiving claw's inbound policy before it is delivered. A message type not defined in both policies is dropped and logged. There is no freeform text passing between claws. There is no way for the Content Claw to instruct the Finance Claw to change a pricing rule — that message type does not exist in Finance Claw's inbound policy.

**The War Room sits above the mesh, not inside it.** It is not a sixth sandbox. It is the human oversight layer — the `nemoclaw term` TUI extended by Milimo Claw to surface the full squad's pending action queue simultaneously. Every claw action that meets the REVIEW, HOLD, or VETO approval threshold is paused and held in the War Room queue until a squad member acts. The mesh runs autonomously; the War Room is where the humans remain in control.

**Two topologies, one architecture.** Creative and commerce squads run 4-claw meshes. Tech squads run 5-claw meshes (6-claw with Assistant). The Build Claw is the only structural difference — it connects to the same inter-sandbox channel using the same typed contract system, but its inbound policy accepts a distinct set of message types (feature briefs from Ops, retention signals from Analytics) and its outbound policy emits a distinct set (shipping summaries to Content, deploy signals to Ops). The Assistant Claw connects similarly, providing a conversational bridge between the operator and the autonomous claws. Adding or removing a claw from the mesh is a blueprint change — the squad's shared policy is updated, the gateway is hot-reloaded, and the new topology is live without restarting any sandbox.

### 5.2 Self-Evolving Claws = Departments That Get Smarter Autonomously

Self-evolution is the most consequential NemoClaw capability in the Milimo Claw stack. It is what separates the platform from every other multi-agent framework: the claws do not just execute instructions. They observe their own operational history, identify patterns, build new tools to capitalize on those patterns, validate the tools in sandbox isolation, and deploy them — all without a human prompt. The platform compounds value continuously, with or without the squad's active involvement.

#### The Evolution Mechanism

Each claw runs a weekly **Evolution Cycle** in the background — a structured 5-stage process that operates entirely inside the sandbox:

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEEKLY EVOLUTION CYCLE                       │
│                                                                 │
│  1. OBSERVE       Review the week's operational log:            │
│                   — which actions were taken                    │
│                   — which were approved / edited / rejected     │
│                   — what outcomes were measured                 │
│                   — what inter-claw signals were received       │
│                                 │                               │
│                                 ▼                               │
│  2. IDENTIFY      Surface recurring patterns in the log:        │
│                   — approval rate by content type               │
│                   — client response time by communication style │
│                   — feature adoption by user segment            │
│                   — cost drift by inference provider            │
│                                 │                               │
│                                 ▼                               │
│  3. PROPOSE       Nominate a new tool to address the pattern:   │
│                   — classifier, predictor, optimizer,           │
│                     generator variant, anomaly detector         │
│                   Tool is proposed but NOT yet deployed         │
│                                 │                               │
│                                 ▼                               │
│  4. BUILD & TEST  Tool is built and validated inside the        │
│                   sandbox against 4 weeks of historical data.   │
│                   Must outperform the claw's current baseline   │
│                   on the target metric before it qualifies.     │
│                   Failed tools are discarded. Passed tools      │
│                   are staged for deployment.                    │
│                                 │                               │
│                                 ▼                               │
│  5. DEPLOY        Tool activates in the claw's live toolkit.    │
│                   Blueprint is versioned to record the change.  │
│                   Performance uplift is logged to War Room.     │
│                   Tool can be disabled by the squad at any time.│
│                                                                 │
│              ◄─────────── loop repeats weekly ──────────────►   │
└─────────────────────────────────────────────────────────────────┘
```

**Critical constraint:** Every tool built by the Evolution Cycle can only access data sources and network endpoints that are already in the claw's approved policy. Evolution cannot expand a claw's permissions. A tool proposed by the Content Claw that would require access to `/sandbox/clients` is rejected at the build stage — that mount is not in the Content Claw's policy and no evolved tool can change that. Evolution makes claws smarter within their boundaries. It does not move the boundaries.

#### Each Claw Evolves Differently

Self-evolution is not a generic capability — it produces fundamentally different types of tools depending on the claw's role and the data it has access to. The Intelligence gap between a 1-month-old claw and a 9-month-old claw is not just quantitative. The tools that emerge are qualitatively different in kind.

| Claw | Primary Evolution Signal | Types of Tools That Emerge | Compound Effect by Month 9 |
|---|---|---|---|
| **Content** | Squad approval decisions, post engagement data | Style classifiers, timing optimizers, A/B variant engines, platform calibrators | Drafts require fewer revision rounds; engagement per post measurably increases |
| **Ops** | Client response patterns, project completion rates | Triage scorers, deadline risk predictors, scope creep detectors, relationship health monitors | New client conversion rate improves; late deliverables become rare |
| **Analytics** | Cross-claw performance data, external market signals | Anomaly detectors, opportunity scorers, retention correlators, forward projection engines | The squad's weekly intelligence becomes predictive rather than descriptive |
| **Finance** | Invoice outcomes, scope estimates vs actuals | Cost estimators, payment risk scorers, margin trackers, rate optimization advisors | Underpricing is flagged before proposals go out; margin compression surfaces weeks early |
| **Build** | PR merge patterns, production error logs, user retention data | PR style enforcers, issue complexity scorers, error pattern classifiers, churn correlators | Bugs from common error classes stop reaching production; roadmap prioritization is data-driven |

#### Cross-Claw Evolution — The Compound Effect

The most powerful dimension of self-evolution in a multi-sandbox mesh is not what a single claw learns about its own domain. It is what claws learn by consuming each other's outputs over time.

This is a capability no single-agent or single-sandbox product can replicate. Cross-claw evolution works as follows:

**Example 1: Analytics → Content evolution loop**

The Analytics Claw publishes a weekly intelligence report. The Content Claw consumes that report as an input to its Evolution Cycle. Over time, the Content Claw builds a tool not derivable from its own data alone — a **cross-signal content predictor** that correlates content format choices with the audience retention patterns the Analytics Claw tracks. The Content Claw learns that tutorial-format posts drive 3x higher retention for this squad's specific audience — not because anyone told it, but because it ingested the Analytics Claw's retention data week after week and built a model on that cross-signal.

**Example 2: Build → Analytics → Ops evolution chain**

The Build Claw ships a feature and logs deployment metadata. The Analytics Claw tracks feature adoption and publishes a signal: "Feature X has 12% adoption at day 7." The Ops Claw ingests that signal and, over time, builds a **proactive client education tool** — it learns that clients who are sent a feature walkthrough within 48 hours of deployment show 3x higher adoption than those who aren't. No single claw had the data to build this tool. It emerged from the chain.

**Example 3: Finance → Ops evolution**

The Finance Claw tracks that 40% of invoices from a specific project type are paid late. It publishes a payment risk signal. The Ops Claw ingests that signal and builds a **contract risk scorer** that flags new inquiries of that project type for upfront payment negotiation before the work begins. The Finance Claw knew about the payment problem. The Ops Claw knew about the client intake stage. The tool that fixed the problem required both datasets — and emerged from the cross-claw evolution loop.

```
                    CROSS-CLAW EVOLUTION FLOWS

   Content Claw ────── consumes ──────► Analytics Claw outputs
        │                                       │
        │  builds cross-signal content           │  builds retention
        │  predictor from engagement +           │  correlators from
        │  retention data combined               │  all claw signals
        │                                       │
        ▼                                       ▼
   Ops Claw ──────── consumes ──────────► Finance Claw outputs
        │                                       │
        │  builds proactive client              │  builds payment
        │  education tool from deploy           │  risk models from
        │  signals + adoption patterns          │  project type data
        │                                       │
        └───────────────────────────────────────┘
                 Build Claw feeds signals to all
```

#### Evolution and the War Room

The squad is never surprised by what their claws are becoming. Every tool built by the Evolution Cycle is logged in the War Room with:

- **Tool name and plain-language description** of what it does
- **The pattern that triggered it** — the specific operational observation that led to the proposal
- **Performance delta** — measured improvement vs baseline, expressed as percentage uplift on the relevant metric (approval rate, engagement rate, payment collection rate, PR cycle time)
- **Disable toggle** — any squad member can deactivate a tool instantly if its behavior is undesirable

The squad does not need to manage the evolution. They need to be able to understand and override it. The War Room makes both possible.

#### The Compounding Moat

A squad that has been running Milimo Claw for 9 months has claws with tool inventories that didn't exist at launch — tools built from their specific client mix, their specific audience, their specific codebase, their specific pricing history. A new squad joining the platform starts from a blueprint template. The 9-month squad's claw starts from 9 months of operational intelligence.

That gap grows every week. It cannot be closed by a competitor launching a new platform. It cannot be purchased except by buying the squad's evolved blueprint from the marketplace. It is, by architecture, the deepest form of lock-in — not because switching is costly, but because the thing being built is genuinely irreplaceable.

### 5.3 Blueprint Versioning = Institutional Memory + Trade Currency

Every claw state is a versioned blueprint — a cryptographically verified artifact with a digest that proves its provenance. The blueprint captures:

- The full claw configuration (prompt architecture, tool inventory, policy settings)
- The trained tools the claw has autonomously built
- The learned priors from operational history (calibrated timing, style parameters, pricing rules)
- The network egress policy (exactly which APIs the claw can reach)
- The operator approval thresholds (what gets auto-approved vs surfaced for review)

Blueprints can be:
- **Forked** — a collaborator takes your blueprint as a starting point and evolves it in their own direction
- **Merged** — two blueprints are combined, with conflict resolution rules, to create a hybrid (the basis of creative collaboration in Milimo Claw)
- **Sold** — an evolved blueprint is exported and sold through the Milimo Claw Blueprint Marketplace
- **Inherited** — when a squad member graduates, they export their evolved claw to the next person who takes their role

**Blueprint versioning commands (exposed through Milimo Claw CLI):**

```bash
# Fork a public blueprint
milimo blueprint fork @seniorSquad2025/content-agency-v8.3 --into my-content-claw

# Compare your blueprint evolution against a baseline
milimo blueprint diff v2.1 v8.3

# Export your evolved blueprint to the marketplace
milimo blueprint publish --name "NYC streetwear content claw" --price 0.05eth

# Roll back to a previous era
milimo blueprint rollback --to v3.0 --reason "new client wants retro style"
```

### 5.4 Privacy Router = Personal Data Never Leaves the Laptop

NemoClaw ships with three inference profiles: NVIDIA cloud (the configured NEMOCLAW_MODEL), local NIM, and vLLM. The Milimo Claw privacy router adds a fourth layer: a **sensitivity classifier** that intercepts every inference call and routes it based on data type.

| Data Type | Routing Decision | Rationale |
|---|---|---|
| Client proposals, public content drafts | Cloud (NEMOCLAW_MODEL) | Max quality for client-facing work |
| Internal squad comms, client contact details | Local NIM on RTX | Private business data stays on device |
| Financial records, payment details | Local NIM only | No cloud touch for financial data |
| Personal notes, private context | Local vLLM | Tightest isolation, never leaves machine |
| Trend data, market research | Cloud (NEMOCLAW_MODEL) | Public data, cloud quality preferred |

The routing happens transparently — the claw doesn't know which inference backend was used. The privacy router makes the decision based on the configured sensitivity policy, which the squad sets once at onboarding.

**Why this matters for students:** College students sharing client work, payment details, and personal data in a business context have real exposure if that data leaks. The privacy router gives them enterprise-grade data segregation with zero configuration overhead. This is also the institutional trust story — universities can recommend Milimo Claw because sensitive data is architecturally isolated, not just policy-protected.

### 5.5 Network Egress Policy = Clean Persona Separation + Safe Client Boundaries

Each claw's sandbox has a network egress policy — a whitelist of external APIs and domains it can reach. In Milimo Claw, this policy serves three functions:

**Function 1: Persona separation.** Your Fiverr persona and your Etsy store are different egress policies. The Fiverr claw can reach api.fiverr.com and the approved client contact list. It literally cannot reach Etsy. Your two business personas are architecturally separate — a client from one channel cannot accidentally discover your identity on the other.

**Function 2: Client boundary enforcement.** Each client project is a sandboxed sub-context. The claw's policy only allows it to access the client's approved communication channels. It cannot CC anyone not on the client's approved list. It cannot use assets from one client's folder in another client's work. These rules aren't written in a prompt — they're enforced at the network and filesystem layer.

**Function 3: Finals Mode.** One command hot-reloads all squad claws into "maintenance mode" — the egress policy shrinks to outgoing-only automated check-ins. No new client intake routes through. Existing deadlines are flagged. The squad's professional reputation is maintained while they go dark academically. Unpausing is a single command after finals.

### 5.6 Operator Approval TUI = The War Room

`nemoclaw term` opens the OpenShell TUI — Milimo Claw surfaces this as the **War Room**: a live dashboard where every pending action from every claw in the squad is visible to all members simultaneously.

**War Room features:**

- **Live action feed:** Real-time stream of what every claw is doing — drafts queued, client messages pending, invoices staged, analytics alerts surfaced
- **Approval flow:** Each pending action shows its claw source, the action type, a summary, and the full content. Squad members can approve, block, or delegate
- **Escalation rules:** Each claw's policy defines escalation thresholds — e.g., any invoice over $500 requires squad-wide approval, not just the Ops claw member's sign-off
- **Audit trail:** Every action ever taken by every claw is logged with timestamp, claw ID, and decision record. Full replay capability
- **Override queue:** Any squad member can queue an override instruction that will apply to a claw on its next action cycle

**Approval modes:**

```
AUTO     — Claw acts immediately, logs for review. Low-stakes actions below threshold.
REVIEW   — Claw drafts, queues for human approval before executing.
HOLD     — Claw flags and pauses. Requires explicit squad confirmation.
VETO     — Any squad member can block. Requires re-vote to proceed.
```

Thresholds for each mode are set by the squad's shared policy, versioned in the blueprint, and hot-reloadable without restarting any sandboxes.

### 5.7 Seccomp + Landlock = Trust Between Squad Members

In a friend group running a business, the most sensitive risk is internal. One squad member's claw should never be able to read another member's private context, personal notes, or relationship data — even accidentally.

NemoClaw's Landlock and seccomp layers enforce this at the kernel level. Each member's sandbox can only read and write from its own designated directories. The inter-sandbox channel (OpenShell gateway) is the only sanctioned communication path. There is no side-channel. There is no "oops I shared the wrong folder."

This is a trust primitive that makes Milimo Claw viable for real squads — where people are friends, business partners, and potential sources of liability all at once.

---

## 6. Product Features

### 6.1 The Six Claws

Every Milimo Claw squad is assembled from six specialized claw roles. Creative and commerce squads typically run four (Content, Ops, Analytics, Finance). Tech squads unlock the fifth — the Build Claw — which transforms the squad from a service operation into a shipping product company. The sixth — the Assistant Claw — serves as the conversational interface between the operator and the autonomous claw agents.

Each claw is a fully isolated NemoClaw sandbox with its own filesystem mount, its own network egress policy, its own inference routing rules, and its own self-evolution cycle. They coordinate exclusively through the OpenShell inter-sandbox gateway — a policy-governed channel where every message is typed, logged, and subject to the squad's shared approval rules. No claw has ambient access to another claw's data. The coordination is intentional and auditable, not accidental and invisible.

---

#### Content Claw

**Primary responsibility:** All creative output — social posts, long-form copy, email campaigns, pitch decks, proposals, content calendars, creative briefs, and brand voice documentation.

**Filesystem mount:** `/sandbox/content` — approved brand assets, style guides, past approved posts, and client creative briefs fed from the Ops Claw via inter-sandbox message. No access to client contact data, financial records, or source code.

**Network egress policy:** Approved social platform APIs (scheduled publishing only — no reading of DMs or private data), stock asset libraries, SEO trend APIs, the squad's public-facing website. No access to payment processors or internal comms channels.

**Inference routing:**
- Public-facing drafts → Cloud (NEMOCLAW_MODEL) (peak quality for anything a client or audience will see)
- Internal drafts and ideation → Local NIM (private creative process stays on device)
- Trend research and competitive analysis → Cloud (NEMOCLAW_MODEL) (public data, speed preferred)

**Inter-claw coordination:**
- Receives creative briefs from Ops Claw when a new client project opens
- Queries Analytics Claw weekly for top-performing content patterns before starting new drafts
- Sends completed drafts to the War Room approval queue before any external publication
- Receives audience feedback summaries from Analytics Claw post-publication to inform next cycle

**Self-evolution timeline:**

| Week | Tool Built | What It Does |
|---|---|---|
| 2 | Style descriptor | Characterizes the squad's brand voice from approved post history |
| 4 | Tone classifier | Auto-categorizes drafts: hype, educational, soft sell, community, humor |
| 7 | Approval predictor | Estimates likelihood of squad approval before surfacing — stops wasting War Room time |
| 10 | Platform calibrator | Adjusts format, length, and register automatically per platform without being asked |
| 14 | Timing optimizer | Identifies the squad's audience-specific peak windows — not generic best-practice, their actual data |
| 18 | A/B variant engine | Generates two variants per post, tracks which performs better, folds winners into future generation |
| 24 | Client voice adapter | Automatically writes in each client's brand voice without re-prompting, trained from brief history |
| 32 | Trend injector | Identifies rising content formats within the squad's niche before saturation — not after |

---

#### Ops Claw

**Primary responsibility:** The full client lifecycle — intake, scoping, brief management, scheduling, deliverable tracking, follow-up, conflict escalation, and offboarding. The Ops Claw is the squad's account manager, project manager, and client communications director, running 24/7.

**Filesystem mount:** `/sandbox/clients` — the squad's most sensitive data store. Contains full client records, contact details, project histories, communication logs, and contract terms. Accessible only to the Ops Claw and approved read-queries from the Finance Claw (billing context only). No other claw has direct access.

**Network egress policy:** Approved client communication channels (email API, platform messaging APIs), scheduling tools, project management APIs, contract platforms. No access to social publishing, financial systems, or code repositories.

**Inference routing:**
- Client-facing communications → Cloud (NEMOCLAW_MODEL) (client sees this — quality is the priority)
- Internal project summaries and briefs → Local NIM (business context is sensitive)
- Contract review and risk flagging → Local NIM (legal-adjacent content never touches cloud)
- Scheduling optimization → Cloud (NEMOCLAW_MODEL) (non-sensitive computation)

**Inter-claw coordination:**
- Opens a new project context in `/sandbox/clients/[id]` when a client is onboarded and broadcasts a project brief to the Content Claw or Build Claw via inter-sandbox message
- Queries Finance Claw before sending any proposal to confirm pricing floor and scope cost estimates
- Receives deliverable completion signals from Content or Build Claw and coordinates client delivery
- Escalates all deadline conflicts, scope changes, and new client inquiries to the War Room immediately

**Self-evolution timeline:**

| Week | Tool Built | What It Does |
|---|---|---|
| 3 | Client triage scorer | Rates incoming inquiries on budget signal, scope clarity, and niche fit before the squad sees them |
| 6 | Brief quality checker | Flags incomplete or ambiguous client briefs before work begins — reduces revision cycles |
| 10 | Deadline risk predictor | Monitors active projects and surfaces deadline risk 5+ days in advance |
| 15 | Communication tone calibrator | Learns how each client prefers to be communicated with — formal vs casual, verbose vs brief |
| 20 | Scope creep detector | Identifies when client requests exceed original scope and auto-drafts a change order for approval |
| 28 | Relationship health scorer | Assigns each active client a satisfaction signal score based on response patterns and feedback sentiment |

---

#### Analytics Claw

**Primary responsibility:** The intelligence layer of the squad. Tracks everything — content performance, client satisfaction signals, revenue trends, delivery velocity, platform algorithm shifts, and competitive opportunity scoring. Synthesizes raw operational data into actionable weekly intelligence that every other claw consumes.

**Filesystem mount:** `/sandbox/analytics` — aggregated performance data, anonymized engagement metrics, revenue summaries, and trend datasets. Writes weekly intelligence reports accessible to all claws via approved read queries. No access to raw client contact data or source code.

**Network egress policy:** Platform analytics APIs (read-only), market research data feeds, competitor monitoring APIs, the squad's published content endpoints (to track post-publication performance). No write access to any external platform.

**Inference routing:**
- Public trend and market analysis → Cloud (NEMOCLAW_MODEL) (public data, maximum reasoning quality)
- Internal performance synthesis → Local NIM (squad's operational data is sensitive)
- Predictive modeling and anomaly detection → Local NIM (models trained on proprietary squad data)

**Inter-claw coordination:**
- Publishes a weekly intelligence report to a shared read-accessible directory, consumed by Content, Build, and Finance Claws
- Responds to on-demand queries from Content Claw ("what performed best in the last 2 weeks?") and Build Claw ("which features are correlated with retention?")
- Feeds churn signals and user behavior patterns to Build Claw for product roadmap decisions (tech squads)
- Sends revenue anomaly and pricing opportunity alerts directly to Finance Claw

**Self-evolution timeline:**

| Week | Tool Built | What It Does |
|---|---|---|
| 2 | Engagement baseline model | Establishes the squad's historical performance baseline for content and delivery |
| 5 | Anomaly detector | Flags performance outliers — unusually high or low — for squad review |
| 9 | Opportunity scorer | Surfaces clients, content formats, or product features with above-average growth signal |
| 14 | Retention correlator | Identifies which actions (content type, response speed, feature usage) correlate with client retention |
| 22 | Competitor signal tracker | Monitors the squad's competitive set for strategic moves worth responding to |
| 30 | Forward projection engine | Generates 4-week revenue and engagement projections from current trend data |

---

#### Finance Claw

**Primary responsibility:** The complete financial nervous system of the squad — revenue tracking, proposal pricing, invoicing, payment follow-up, expense logging, profit margin monitoring, and tax-ready reporting. Every financial action requires explicit operator approval. No money moves without a human sign-off.

**Filesystem mount:** `/sandbox/finance` — revenue records, invoice history, expense logs, pricing rules, and payment status. The most tightly isolated store in the squad. Zero cross-claw read access except approved summary queries from the Analytics Claw (revenue totals only, no line-item detail).

**Network egress policy:** Approved payment processors (Stripe, PayPal — read-only status checks and invoice generation only), accounting APIs, banking APIs (read-only balance checks). Zero access to social platforms, code repositories, or client communication channels.

**Inference routing:**
- All financial data → Local NIM, always. No exceptions. Financial records, payment details, pricing strategy, and tax data never touch a cloud inference endpoint. This is an architectural constraint enforced by the privacy router, not a policy preference.

**Inter-claw coordination:**
- Responds to pricing queries from Ops Claw before any proposal is sent ("what's our floor for a project of this scope?")
- Receives project completion signals from Ops Claw to trigger invoice generation
- Sends overdue payment alerts and revenue anomalies to the Analytics Claw and directly to the War Room
- Provides revenue summary data to Analytics Claw for performance reporting (totals only — no line-item exposure)

**Self-evolution timeline:**

| Week | Tool Built | What It Does |
|---|---|---|
| 3 | Scope cost estimator | Estimates project cost from brief keywords, calibrated to squad's actual delivery velocity |
| 7 | Pricing floor guardian | Automatically flags proposals that fall below the squad's profitable rate threshold |
| 12 | Payment risk scorer | Predicts likelihood of late payment from client communication patterns before invoice is sent |
| 18 | Margin tracker | Monitors actual hours/effort vs estimated and surfaces margin compression early |
| 25 | Tax category classifier | Auto-categorizes all income and expenses for quarterly tax prep with zero manual sorting |
| 35 | Rate optimization advisor | Identifies when the squad is systematically undercharging relative to their delivery quality metrics |

---

#### Build Claw *(Tech Squads only)*

**Primary responsibility:** The engineering department. Writes code, opens pull requests, runs tests, monitors production systems, maintains documentation, and manages the development backlog — autonomously and continuously. The Build Claw is not a code assistant you prompt. It is an always-on engineering operator that takes the mechanical work off the squad's plate so the human engineers can focus entirely on architecture and product decisions.

**Filesystem mount:** `/sandbox/build` — the squad's codebase (via approved GitHub repository mount), environment configuration (secrets encrypted at rest, never exposed to any other claw or inter-sandbox message), test suites, deployment configs, and error logs. Source code and secrets are among the most sensitive assets in the squad and are treated accordingly.

**Network egress policy:** GitHub API, Vercel API, Railway API, Stripe API, Sentry API, Datadog API, npm registry, PyPI, Cloudflare API, approved AI provider APIs (for inference cost benchmarking), RapidAPI marketplace. No access to social platforms, client communication channels, or financial records.

**Inference routing:**
- Proprietary source code, API keys, environment variables → Local NIM, always. Code is IP. It never leaves the machine.
- Architecture discussions and code review → Local NIM (sensitive design decisions)
- Boilerplate generation, test writing, documentation drafts → Cloud (NEMOCLAW_MODEL) (non-sensitive, quality preferred)
- Public-facing docs and changelogs → Cloud (NEMOCLAW_MODEL) (client and community will read these)
- Production log analysis with user data → Local NIM (user data privacy is non-negotiable)

**Inter-claw coordination:**
- Receives new feature briefs from Ops Claw when a client or user request is scoped and approved
- Queries Analytics Claw for user behavior patterns before beginning roadmap planning each sprint
- Sends deployment completion signals to Ops Claw to trigger client delivery notifications
- Sends weekly shipping summaries to Content Claw to generate build-in-public posts and devlog updates
- Escalates all production incidents, security alerts, and breaking changes directly to the War Room

**Self-evolution timeline:**

| Week | Tool Built | What It Does |
|---|---|---|
| 2 | PR style enforcer | Flags PRs that don't meet the squad's code conventions before human review |
| 5 | Issue complexity scorer | Estimates engineering hours from issue descriptions, calibrated to the squad's actual velocity |
| 9 | Prompt regression tester | Runs baseline prompts against each new model version and surfaces quality deltas automatically |
| 14 | Cost anomaly detector | Alerts when per-user inference cost drifts above the squad's target margin |
| 18 | Dependency audit runner | Weekly scan for vulnerable packages, auto-opens security PRs for well-understood fixes |
| 22 | Error pattern classifier | Groups Sentry errors by root cause and auto-drafts patches for recurring error classes |
| 28 | Churn signal correlator | Cross-references Analytics Claw retention data with feature usage to predict churn 2 weeks out |
| 36 | Auto-roadmap drafter | Synthesizes user feedback, churn signals, error patterns, and issue backlog into a prioritized roadmap draft — published to the War Room every Monday morning |

---

#### Claw Coordination Summary

| From \ To | Content | Ops | Analytics | Finance | Build | Assistant |
|---|---|---|---|---|---|
| **Content** | — | Delivers completed drafts | Requests performance data | — | — | — |
| **Ops** | Sends client briefs | — | — | Requests pricing estimates | Sends feature briefs | — |
| **Analytics** | Sends performance intel | Sends client health signals | — | Sends revenue summaries | Sends retention signals | — |
| **Finance** | — | Sends invoice triggers, rate alerts | Sends revenue totals | — | — | — |
| **Build** | Sends shipping updates for devlog | Sends deploy completion | Requests user behavior data | — | — | — |
| **Assistant** | — | — | — | — | — | — |

All inter-claw messages are typed contracts, not freeform text. Each message type is defined in the squad's shared blueprint and enforced by the OpenShell gateway. A claw cannot send a message type that isn't in its outbound policy. A claw cannot receive a message type that isn't in its inbound policy. The coordination structure is the blueprint.

### 6.2 Milimo Templates

Pre-built squad blueprints for common college hustle archetypes, organized by category. Category C tech templates unlock the **Build Claw** — a fifth specialized claw role exclusive to tech squads, fully documented in Section 6.1.

---

#### Category A — Creative & Content

| Template | Claws Active | Typical Squad Size | Common Platforms |
|---|---|---|---|
| Content Agency | Content + Ops + Analytics | 2–4 | Instagram, TikTok, LinkedIn |
| Design Studio | Content + Ops + Finance | 2–3 | Behance, Upwork, Direct clients |
| Social Media Mgmt | Content + Analytics + Ops | 2–4 | All major platforms |
| Event Promotion | Content + Ops + Analytics | 3–6 | Eventbrite, Instagram, Campus |

---

#### Category B — Commerce & Services

| Template | Claws Active | Typical Squad Size | Common Platforms |
|---|---|---|---|
| Streetwear / Resale | Content + Ops + Finance | 2–4 | Depop, GOAT, StockX, Instagram |
| Tutoring Network | Ops + Analytics + Finance | 2–6 | WyzAnt, Craigslist, Campus |

---

#### Category C — Tech Startups (AI Era)

This is the highest-leverage category. Tech squads get access to the **Build Claw** — a fifth specialized claw that autonomously writes, tests, deploys, and iterates on code. The Build Claw treats your GitHub repository as its workspace, your issue tracker as its task queue, and your users' feedback as its training signal. It does not replace engineers — it multiplies them.

| Template | Claws Active | Typical Squad Size | What It Ships |
|---|---|---|---|
| AI Micro-SaaS | Build + Ops + Analytics + Finance | 2–4 | Focused AI-powered web tools (summarizers, generators, classifiers) deployed to Vercel/Railway with Stripe billing auto-configured |
| API Startup | Build + Ops + Analytics + Finance | 2–5 | Documented REST or MCP-compatible APIs with developer portal, usage metering, and tiered pricing — ready to list on RapidAPI |
| AI Agent Studio | Build + Ops + Analytics | 3–6 | Custom NemoClaw-based agents built and packaged as blueprints for sale on the Milimo Claw Blueprint Marketplace |
| Campus AI Tool | Build + Content + Ops | 2–4 | University-specific AI tools (campus event aggregators, professor review summarizers, roommate matching, dining optimizers) — built fast, distributed virally within one campus |
| Open Source + Monetize | Build + Analytics + Finance | 2–5 | Open source library or framework with a hosted paid tier — Build Claw manages issues, PRs, and release notes autonomously |
| No-Code AI Wrapper | Build + Content + Ops | 2–3 | Beautiful consumer-facing wrappers around existing AI APIs — the Build Claw handles the integration engineering, the Content Claw handles the product story |

---

##### The Build Claw

Full technical specification — filesystem mount, network egress policy, inference routing, inter-claw coordination, and the complete 36-week self-evolution timeline — is documented in **Section 6.1: The Six Claws → Build Claw**.

**Why this matters for tech templates:** A 3-person tech squad with a Build Claw, an Ops Claw, and an Analytics Claw has the operational output of a team twice its size. The Build Claw handles the mechanical engineering work — issues, PRs, tests, docs, monitoring — freeing the human engineers for architecture decisions and product thinking. For an AI micro-SaaS, this is the difference between shipping monthly and shipping weekly.

### 6.3 War Room Dashboard (TUI)

The primary operator interface. Built on top of `nemoclaw term`. Displays:

- Squad status: which claws are active, idle, or in review-hold
- Pending action queue: count per claw, urgency flags
- Recent completions feed: last 24 hours of completed autonomous actions
- Revenue snapshot: current pipeline, outstanding invoices, this month's earnings
- Blueprint health: last evolution timestamp, tool count per claw, model routing stats
- Escalation alerts: anything requiring squad attention in the next 4 hours

### 6.4 Blueprint Marketplace

A peer-to-peer marketplace where squads list their evolved blueprints. Listings show:

- Business type and niche
- Blueprint age and evolution depth (number of autonomously-built tools)
- Performance metrics shared by the seller (optional) — average revenue/month, client retention rate, content engagement averages
- Verification badge for blueprints with cryptographically verifiable operational history
- Fork count — how many squads have already used this as a starting point

Payment is peer-to-peer. Milimo Claw takes a 10% platform fee on paid blueprint sales.

### 6.5 Finals Mode

One command that simultaneously:
1. Hot-reloads all squad sandbox egress policies to outgoing-only maintenance configuration
2. Enables auto-responses to all active clients from a pre-approved template set
3. Pauses all new client intake routes
4. Flags all pending deadlines in the War Room with urgency scoring
5. Sets the Analytics claw to passive monitoring only (no new experiments launched)

```bash
milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
```

A scheduled resume command reloads all policies to their pre-finals state and sends a reactivation message to paused clients.

---

## 7. User Roles & The Squad Model

### 7.1 Squad Composition

A Milimo Claw squad is 2–6 members. Each member owns one or more claw roles. Squad composition flexes by template category:

**Creative & Commerce squads (4-claw model):**
- 2-person squad: Person A runs Content + Analytics, Person B runs Ops + Finance
- 3-person squad: Content, Ops + Finance, Analytics
- 4-person squad: one specialized claw per person

**Tech squads (5-claw model — includes Build Claw):**
- 2-person squad: Person A runs Build + Analytics, Person B runs Ops + Finance. Content is optional or handled by Build Claw's devlog tooling
- 3-person squad: Build, Ops + Finance, Analytics + Content (build-in-public content generated from shipping summaries)
- 5-person squad: one specialized claw per person — the full autonomous company configuration

There is no hierarchy within the squad — every member has War Room access and equal approval weight by default. Squads can optionally designate a **Squad Lead** whose approval is required for Finance Claw actions above a threshold, production deployments from the Build Claw, and Blueprint Marketplace listings.

### 7.2 The Mesh Formation Ritual

When a squad forms on Milimo Claw, they go through a guided **Mesh Formation** — a 20-minute onboarding that:

1. Each member installs NemoClaw and runs `milimo init` on their laptop
2. The squad selects a Milimo Template or starts from scratch
3. Each member is assigned a claw role
4. The squad sets shared policies: approval thresholds, Finals Mode trigger criteria, revenue split rules
5. Each member's OpenShell gateway registers with the squad mesh
6. Milimo Claw deploys the initial blueprint to each member's sandbox
7. Each claw runs a 5-minute calibration session — basic questions about the squad's niche, target clients, and communication style

After Mesh Formation, the squad's claws are live and immediately functional.

### 7.3 The Claw Handoff Protocol

When a squad member graduates or leaves, their claw doesn't die. It exports a **Handoff Blueprint** — the fully evolved version of their claw, including all autonomously-built tools and learned patterns. The incoming member deploys the Handoff Blueprint as their starting point.

The incoming member's claw starts at the evolution level the departing member left off. The squad's institutional intelligence is preserved. This is the feature that makes Milimo Claw a platform with genuine network effects across graduating cohorts — not just within a single squad's lifecycle.

---

## 8. Core User Flows

### 8.1 New Client Intake

```
1. External inquiry arrives (email, platform DM, web form)
2. Ops Claw intercepts via approved ingress channel
3. Ops Claw runs client triage: industry match, budget estimate, scope clarity score
4. If score above threshold → Ops Claw drafts welcome message + intake questionnaire
5. Action queued in War Room: "New client intake from @CreativeAgency — approve to send?"
6. Squad member approves
7. Ops Claw sends, awaits response
8. Client responds → Ops Claw extracts brief, creates project context in /sandbox/clients/[id]
9. Ops Claw sends brief summary to Content Claw via inter-sandbox channel
10. Content Claw generates initial proposal draft
11. War Room: "Proposal ready for [client] — review before sending?"
12. Squad reviews, edits inline in War Room, approves
13. Ops Claw sends proposal
```

Total squad member time: ~4 minutes of War Room review. Everything else was autonomous.

### 8.2 Weekly Content Pipeline

```
1. Monday 6am: Content Claw pulls week's brief from Ops Claw via inter-sandbox channel
2. Content Claw runs trend analysis via Analytics Claw query: "what performed best last 2 weeks?"
3. Analytics Claw responds with top 3 content patterns (from its local training data)
4. Content Claw generates 10 post drafts incorporating top patterns
5. Content Claw self-applies tone classifier, A/B variant generator, timing optimizer
6. Result: 10 drafts, each with 2 variants, scheduled for optimal times, categorized by emotional register
7. Monday 9am War Room notification: "20 drafts ready for weekly review"
8. Squad spends 15 minutes in War Room reviewing, approving 12 of 20, editing 4, rejecting 4
9. Approved content auto-schedules across approved platforms per egress policy
10. Post-publish: Analytics Claw monitors performance, feeds back to Content Claw for next cycle
```

Squad member time investment: 15 minutes Monday morning. The operation runs itself for the rest of the week.

### 8.3 Tech Squad — Weekly Sprint Shipping Flow

```
1. Monday 7am: Build Claw pulls open issues from GitHub, scores by complexity
2. Build Claw queries Analytics Claw: "which features have lowest retention correlation?"
3. Analytics Claw responds with ranked feature gaps from user behavior data
4. Build Claw generates sprint plan: top 3 issues prioritized by complexity score +
   retention impact, surfaced to War Room for squad approval
5. War Room: "Sprint plan ready — 3 issues, est. 14hrs total — approve to begin?"
6. Squad approves. Build Claw begins autonomous work on Issue #1.
7. Build Claw writes code, opens PR, runs test suite, surfaces failures with diagnosis
8. War Room: "PR #47 ready — all tests passing — approve to merge?"
9. Squad reviews PR diff in War Room, approves
10. Build Claw merges and triggers Vercel deployment
11. Ops Claw receives deploy signal, sends release note to relevant clients
12. Content Claw receives shipping summary from Build Claw, drafts devlog post + changelog
13. War Room: "Devlog post ready — approve to publish?"
14. Squad approves. Content Claw publishes to build-in-public channels.
15. Analytics Claw monitors new feature adoption, feeds performance data back to
    Build Claw for next sprint prioritization
```

Squad member time investment: ~20 minutes of War Room review across the week. The Build Claw ships, the Ops Claw communicates, the Content Claw tells the story, the Analytics Claw closes the loop.

### 8.4 Finals Mode Activation & Reactivation

```
milimo squad finals-mode --duration 3weeks

→ All claws receive hot-reload policy update simultaneously
→ Content Claw: drafts paused, no new content generated
→ Ops Claw: "Finals mode" auto-response active for all clients
  "Hey [name], we're in finals the next 3 weeks. Your project
   is on track for [date]. Will be in full swing by May 12. 🙏"
→ Finance Claw: invoice sends continue, no new project initiations
→ Analytics Claw: passive monitoring only, weekly digest still generated
→ War Room: simplified view, only urgent escalations shown

milimo squad finals-resume (scheduled for May 12)
→ All policies restored to pre-finals configuration
→ Ops Claw sends reactivation messages to paused clients
→ Content Claw resumes draft generation
→ Full War Room view restored
```

---

## 9. Self-Evolving Intelligence Loop

Section 5.2 documents the mechanism and the cross-claw theory. This section shows what that looks like lived — a real squad's evolution arc across a full academic semester, and what the War Room shows the squad as it happens.

### 9.1 A Full Semester of Evolution — One Squad's Arc

The following traces the evolution of a 4-person creative agency squad — Content, Ops, Analytics, Finance — from Mesh Formation in Week 1 through the end of a 16-week semester. It is the compound effect of 5.2 made concrete.

**Weeks 1–3: Baseline formation**

The claws run from starter blueprints. Content generates drafts using basic style instructions. Ops handles client intake with generic templates. Analytics collects raw engagement data. Finance tracks invoices manually. Squad spends ~45 minutes per day in the War Room reviewing and approving actions. The claws are useful but not yet distinctly theirs.

**Weeks 4–6: First generation tools emerge**

Content Claw builds its first tool — a style descriptor trained on the squad's 60 approved posts. Drafts now arrive pre-categorized by tone. War Room review time drops to ~20 minutes per day. Ops Claw builds a client triage scorer — 40% of low-quality inquiries are now filtered without reaching the squad. The squad notices they're spending less time on noise.

**Weeks 7–10: Cross-claw signals start flowing**

Analytics Claw has enough data to publish its first meaningful intelligence report: the squad's audience engagement peaks Tuesday and Thursday 7–9pm, not the generic "post in the morning" advice. Content Claw ingests this report in its next Evolution Cycle and builds a timing optimizer calibrated to that specific window. First post scheduled by the optimizer outperforms the previous month's average by 34%. The squad didn't configure this. The Analytics → Content cross-signal loop produced it.

Ops Claw builds a deadline risk predictor. Finance Claw builds a scope cost estimator and flags the first underpriced proposal before it goes out — saves the squad from a $200 margin loss on a project they'd have taken at cost.

**Weeks 11–13: Compound tools — built from cross-claw data**

Content Claw builds a client voice adapter — it now writes differently for each of the squad's 4 active clients without being re-prompted. This tool was built using brief histories from Ops Claw's intelligence reports, cross-referenced with engagement outcomes from Analytics. Neither claw could have built this alone.

Analytics Claw builds a retention correlator: squads that receive deliverables with a performance summary included retain at 2x the rate of those that don't. Ops Claw receives this signal and builds an auto-attach tool — every deliverable now ships with a performance summary drafted by Analytics and attached by Ops. The squad didn't design this workflow. It emerged from the cross-claw evolution loop.

Finance Claw identifies that 3 of 12 clients have a pattern of paying late specifically on revision-heavy projects. It flags this as a payment risk signal. Ops Claw, ingesting the Finance signal, builds a change order auto-trigger — any revision request beyond the first is now automatically scoped and priced before work begins. Late payment rate drops to zero for those client types.

**Weeks 14–16: The squad runs on 10 minutes a day**

By the end of the semester the squad's claws have a combined toolkit of 19 autonomously-built tools across the four roles. War Room review has dropped to a single 10-minute morning session. Content drafts arrive pre-styled, pre-timed, pre-calibrated to each client's voice. Ops handles intake, tracking, and delivery with minimal escalation. Analytics surfaces a weekly report that is genuinely predictive — it flags the next 2 weeks' risk before it materializes. Finance has never sent an underpriced proposal in 6 weeks.

The squad spent their time on client relationships, creative direction, and growth — the things that require human judgment. Their claws handled everything else.

**At semester end:** The squad's blueprint set is 16 weeks of evolved operational intelligence. They list it on the Blueprint Marketplace. Three incoming sophomore squads fork it as their starting point. Those squads begin week 1 with the toolkit the graduating squad built across an entire semester — and their Evolution Cycles start from there, not from zero.

### 9.2 Example Evolution Timeline — Build Claw (Tech Squad)

The Content Claw's week-by-week evolution is documented in full in Section 6.1. Here is the Build Claw's equivalent — showing how an engineering-focused claw compounds intelligence over a product's first 9 months in production.

| Week | Tool Built | What It Does |
|---|---|---|
| 2 | PR style enforcer | Flags PRs that don't meet squad conventions before human review |
| 5 | Issue complexity scorer | Estimates engineering hours from issue descriptions, calibrated to squad's actual velocity |
| 9 | Prompt regression tester | Runs baseline prompts against each new model version, surfaces quality deltas automatically |
| 14 | Cost anomaly detector | Alerts when per-user inference cost drifts above the squad's target margin |
| 18 | Dependency audit runner | Weekly scan for vulnerable packages, auto-opens PRs for well-understood fixes |
| 22 | Error pattern classifier | Groups production errors by root cause, auto-drafts patches for recurring error classes |
| 28 | Churn signal correlator | Cross-references Analytics Claw retention data with feature usage to predict churn 2 weeks out |
| 36 | Auto-roadmap drafter | Synthesizes user feedback, churn signals, error patterns, and backlog into a prioritized roadmap — published to the War Room every Monday morning |

By week 36 the Build Claw has a toolkit of 8 engineering-specific tools trained entirely on the squad's actual codebase, velocity history, and user behavior data. No off-the-shelf developer tool has this context. Note that the week-28 churn signal correlator is a cross-claw tool — it could not have been built without the Analytics Claw's retention signals. The cross-claw compound effect applies to tech squads exactly as it does to creative squads.

### 9.3 Squad Control — The Evolution Interface in the War Room

The War Room's evolution log gives the squad full visibility and control over what their claws are becoming. For each autonomously-built tool, the log surfaces:

| Field | What It Shows |
|---|---|
| Tool name | Plain-language label, not technical jargon |
| Trigger pattern | The specific operational observation that prompted the proposal — e.g. "37% of Tuesday drafts were edited for tone before approval over the past 4 weeks" |
| Metric target | The single metric the tool was built to improve |
| Baseline vs current | Before/after measurement — e.g. "Approval rate: 63% → 81%" |
| Data sources used | Which sandbox mounts and inter-claw signals the tool accesses |
| Status toggle | Active / Paused / Disabled — any squad member can change this instantly |

Squad members are never passive observers of their own claws' evolution. They can disable a tool, adjust its activation threshold, or export its logic as a named workflow they can modify directly. The Evolution Cycle is autonomous. The squad's authority over the result is absolute.

---

## 10. Blueprint Economy

### 10.1 What a Blueprint Encodes

A Milimo Claw blueprint is a versioned, cryptographically signed artifact that contains:

```
blueprint.json
├── meta
│   ├── version, created_at, evolved_from (parent blueprint hash)
│   ├── squad_size, niche_tags, business_type
│   └── operational_months, revenue_tier (optional)
├── claw_config
│   ├── role (content | ops | analytics | finance | build)
│   ├── base_model_preferences (cloud | nim | vllm per data type)
│   └── nemotron_profile
├── tools_inventory
│   ├── [tool_id]: {name, version, performance_delta, training_data_hash}
│   └── ...
├── policy
│   ├── network_egress_allowlist
│   ├── filesystem_mounts
│   ├── approval_thresholds (auto | review | hold | veto per action type)
│   └── privacy_routing_rules
├── learned_priors
│   ├── style_parameters (brand voice, tone distribution, vocabulary profile)
│   ├── timing_parameters (platform-specific, audience-specific)
│   ├── client_patterns (communication style preferences, red flags)
│   └── pricing_calibration (rate floor, rate ceiling, scope estimation weights)
└── integrity
    ├── digest (sha256 of entire content)
    └── provenance_chain (hashes of all parent blueprints)
```

### 10.2 Blueprint Marketplace Dynamics

**Supply side:** Graduating seniors, successful squads, and expert operators list their evolved blueprints. A 12-month-evolved content agency blueprint for the streetwear niche is a genuinely scarce asset — no one else has trained specifically on streetwear content performance for a year.

**Demand side:** Incoming students, new squads, and people pivoting niches buy blueprints to avoid starting from zero. Buying a battle-tested blueprint means inheriting months of learned priors — an effective jumpstart of 3–6 months of real operational data.

**Pricing dynamics:**
- Free tier: simple starter blueprints, little evolution depth
- $5–$50: mid-tier, a semester of evolution, specific niche
- $50–$500: premium, multi-year operational history, verifiable revenue track record
- Revenue share: seller can list a blueprint with ongoing revenue share (e.g., "2% of revenue generated while using this blueprint for first 6 months") creating passive income for blueprint creators

**Fork network effect:** Every fork of a blueprint creates a lineage. The original blueprint creator earns attribution and, optionally, a revenue share on all downstream forks. A highly forked blueprint becomes a platform within the platform — an "OS" for a specific niche.

### 10.3 The Blueprint as Cultural Object

For Gen Z, a well-evolved blueprint is a flex. It's proof of operational history. It has receipts. Milimo Claw surfaces blueprint lineage publicly — you can see that your Content Claw descends from the "NYU media squad 2024" blueprint, which descended from the "Columbia PR squad 2023" blueprint. Provenance is social currency.

---

## 11. Tech Stack

### 11.1 Foundation Layer

| Component | Technology | Role |
|---|---|---|
| Agent runtime | NVIDIA NemoClaw | Sandbox lifecycle, policy enforcement |
| Sandbox isolation | NVIDIA OpenShell (Landlock + seccomp + netns) | Process, filesystem, network isolation |
| Inference (cloud) | Nemotron 3 Super 120B via NVIDIA Cloud API | High-quality public-facing generation |
| Inference (local) | Nemotron 3 NIM on RTX | Private data, on-device processing |
| Inference (dev) | Nemotron 3 Nano 30B via vLLM | Lightweight local testing |
| Inference routing | NemoClaw privacy router | Automatic sensitivity-based model selection |
| Blueprint artifacts | NemoClaw blueprint system | Versioned, verified, forkable claw configs |
| Inter-claw comms | OpenShell gateway | Policy-governed inter-sandbox messaging |

### 11.2 Milimo Claw Application Layer

| Component | Technology | Role |
|---|---|---|
| CLI | TypeScript (extends NemoClaw plugin pattern) | Squad management, blueprint ops, Finals Mode |
| War Room TUI | Extends `nemoclaw term` | Live action feed, approval flow, audit trail |
| Privacy router plugin | Python (NemoClaw blueprint layer) | Sensitivity classifier + routing logic |
| Self-evolution engine | Python agent (runs in-sandbox) | Weekly evolution cycle, tool builder |
| Blueprint Marketplace | Next.js + IPFS for blueprint storage | P2P blueprint trading, fork tracking |
| Analytics dashboard | React (local-only, data never leaves sandbox) | Performance metrics, trend visualization |
| Squad mesh coordinator | TypeScript (OpenShell gateway extension) | Squad formation, mesh health, escalation routing |

### 11.3 Hardware Requirements

**Minimum:** NVIDIA RTX 3060 12GB (local NIM, vLLM dev profile)
**Recommended:** NVIDIA RTX 4070 or better (full local NIM at production quality)
**Optimal:** NVIDIA RTX 4090 (full local inference at NEMOCLAW_MODEL-equivalent quality)

Milimo Claw automatically selects the right inference profile based on detected GPU capabilities. A student with a 3060 gets a slightly lower-quality local model but the same architectural guarantees around privacy and isolation.

---

## 12. Go-To-Market Strategy

### 12.1 The Wedge: RTX Laptop Owners

NVIDIA already has a direct pipeline to the target customer. Students who bought RTX-capable gaming laptops for CS, design, or gaming are exactly the demographic. Milimo Claw is GTM'd as "the thing that makes your GPU do something besides render Elden Ring."

**Channel 1: NVIDIA student program co-marketing.** Position Milimo Claw as the productivity app bundled with RTX student laptop purchases. NVIDIA wins by demonstrating ROI for RTX hardware in the AI era. Milimo Claw wins distribution.

**Channel 2: CS and design school ambassador program.** Recruit one ambassador per school — the student who's already side-hustling and has social cred in their cohort. Give them a premium blueprint from a graduating squad at their school. Their public deployment story is the marketing.

**Channel 3: Blueprint virality.** When a squad publicly lists a successful blueprint on the marketplace ("our content agency blueprint made $8K this semester — forked by 40 squads"), the blueprint becomes a press story. Founder communities, tech Twitter/X, and college-specific subreddits will amplify these organically.

**Channel 4: University startup incubator partnerships.** Position Milimo Claw as the AI infrastructure layer for student entrepreneurship programs. Universities want their students to be entrepreneurially active. Milimo Claw is the tool that makes a 3-person squad viable as a real business — a story incubators want to tell.

### 12.2 The Flywheel

```
More squads use Milimo Claw
        ↓
More evolved blueprints created
        ↓
Blueprint Marketplace becomes richer
        ↓
New squads start better (higher quality blueprints)
        ↓
New squads achieve faster results
        ↓
More compelling success stories
        ↓
More squads use Milimo Claw
```

The flywheel accelerates because the inputs (evolved blueprints) are non-fungible assets. A year-old streetwear content agency blueprint trained on real operational data cannot be replicated by a competitor launching a new platform.

### 12.3 Expansion Beyond College

College is the beachhead, not the ceiling. The same architecture serves:
- Recent graduates launching real agencies
- Small creative studios (5–15 person)
- Independent contractor networks (law, design, consulting)
- Non-traditional education cohorts (bootcamps, trade schools)

The RTX laptop requirement naturally expands as the installed base grows and as NVIDIA expands local inference to more devices.

---

## 13. Monetization

### 13.1 Revenue Streams

**Free Tier — "The Starter Claw"**
- Up to 2 squad members
- 1 active claw per member
- Access to community blueprint templates (no evolved blueprints)
- War Room with 7-day audit history
- Cloud inference (NVIDIA Cloud API key required, user-provided)
- 10 auto-approvals per day

**Pro Tier — "Full Send" — $12/month per squad**
- Up to 6 squad members
- All 6 claw roles active simultaneously (including Build Claw for tech squads and Assistant Claw)
- Full Blueprint Marketplace access (buying + selling)
- War Room with 90-day audit history + full replay
- Priority cloud inference routing
- Unlimited auto-approvals
- Finals Mode + scheduling
- Blueprint export and version history
- Privacy router full configuration

**Blueprint Marketplace Revenue**
- 10% fee on all paid blueprint transactions
- 5% fee on revenue-share blueprint arrangements (ongoing)
- Milimo Claw takes no fee on free blueprint forks

**Enterprise / University Tier — custom pricing**
- White-label deployment for university entrepreneurship programs
- Managed mesh formation for incubator cohorts
- Analytics dashboard for program administrators
- Custom blueprint library for school-specific templates

### 13.2 Revenue Model Economics

Assume 10,000 active squads at Pro tier: **$1.44M ARR**
Average blueprint transaction: $25. Assume 500 transactions/month: **$30K/month = $360K ARR**
University partnerships (20 at $10K/yr): **$200K ARR**

**Year 1 target ARR: ~$2M**

With NemoClaw handling all the hard infrastructure — sandboxing, inference management, policy enforcement, blueprint system — the marginal cost of serving an additional squad is effectively zero beyond the cloud inference pass-through (which is a user-provided API key at the Pro tier).

---

## 14. Competitive Landscape

| Competitor | What They Do | Why Milimo Claw Wins |
|---|---|---|
| ChatGPT / Claude | Reactive AI assistants | Stateless, generic, zero autonomy, no multi-agent coordination |
| Notion AI | AI features in a PM tool | Human-dependent, no autonomy, no privacy separation |
| Buffer / Hootsuite | Social media scheduling | No AI generation, no autonomy, no squad architecture |
| Jasper / Copy.ai | AI copywriting tools | Single-player, generic output, no evolution, no coordination |
| Fiverr / Upwork | Freelance marketplaces | They are the market, not the infrastructure. Complementary. |
| Multi-agent frameworks (LangChain, CrewAI) | Dev tools for building agents | Require engineering skills; Milimo Claw is the consumer product on top |

**The honest competitive moat:** No competitor can replicate the multi-sandbox mesh + self-evolving blueprint architecture without building on NemoClaw or building a comparable infrastructure from scratch (18–24 month engineering effort). Milimo Claw's advantage is in being the first consumer product layer on top of this infrastructure, establishing a user base and blueprint library before any competitor reaches parity.

---

## 15. Moats & Defensibility

### Moat 1: Evolved Blueprint Library (Data Moat)
Blueprints trained on real operational data from real student squads are non-replicable. A new entrant launching in year 2 has no access to 12 months of streetwear content agency operational history. The marketplace library gets stronger every week.

### Moat 2: Self-Evolution Depth (Time Moat)
A squad's claws after 6 months have tools that didn't exist at launch. A new user starting on a competing platform starts at zero. The self-evolution gap grows continuously in Milimo Claw's favor.

### Moat 3: Cross-Cohort Blueprint Chains (Network Moat)
Blueprint provenance chains create a social graph that crosses graduating cohorts. The NYU 2027 squad can trace their blueprint lineage back to the NYU 2024 squad. That social continuity is a community flywheel with no analog in any competitor.

### Moat 4: NemoClaw Infrastructure Partnership (Platform Moat)
Milimo Claw is built as a NemoClaw plugin in the official plugin architecture. As NVIDIA invests in the NemoClaw ecosystem, Milimo Claw benefits from infrastructure improvements, distribution opportunities, and enterprise partnerships that a standalone product couldn't access.

### Moat 5: Privacy Architecture (Trust Moat)
The on-device privacy routing architecture creates a genuine trust differentiation that cannot be matched by a cloud-native competitor without a complete architectural rebuild. As privacy regulations tighten and student data protection becomes more scrutinized, this architectural advantage becomes more valuable.

---

## 16. Milestones & Roadmap

### Phase 0 — Foundation (Months 1–2)
- [x] NemoClaw plugin architecture implemented — MilimoClaw rebuilt as extension, not fork
- [x] Six claw role blueprints (Content, Ops, Analytics, Finance, Build, Assistant) completed
- [x] Squad mesh formation protocol built on OpenShell gateway
- [x] War Room TUI (extends `nemoclaw term`) built
- [x] Privacy router sensitivity classifier implemented
- [x] Two Milimo Templates (Content Agency, Design Studio) deployed
- [x] Build Claw (complete) — 13 modules, 3,921 lines, 116/116 tests passing
- [x] All 6 critical security issues resolved
- [x] 1192/1192 blueprint tests passing
- [ ] Alpha test with 3 squads at one university

### Phase 1 — Private Beta (Months 3–4)
- [ ] All Category A + B Milimo Templates available (6 templates)
- [ ] Build Claw — real Vercel/AWS deployment integration (currently mock)
- [ ] AI Micro-SaaS and Campus AI Tool tech templates deployed
- [x] Blueprint versioning and export implemented
- [ ] Finals Mode with scheduling
- [x] Self-evolution engine (Week 1 cycle: style descriptor + tone classifier)
- [ ] 50 beta squads across 5 universities
- [x] War Room approval flow polished, escalation rules configurable

### Phase 2 — Public Launch (Months 5–6)
- [ ] Blueprint Marketplace v1 (free sharing only, no paid listings yet)
- [ ] Milimo Claw Pro tier launched ($12/month/squad)
- [ ] Blueprint fork + lineage tracking
- [ ] NVIDIA student program co-marketing initiated
- [ ] University ambassador program (10 schools)
- [ ] Target: 1,000 active squads

### Phase 3 — Blueprint Economy (Months 7–9)
- [ ] Blueprint Marketplace paid listings enabled
- [ ] Revenue-share blueprint contracts
- [ ] Blueprint performance verification system (cryptographic proof of operational history)
- [ ] Claw Handoff Protocol (graduation export)
- [ ] Self-evolution depth: 6+ tools per claw standard
- [ ] Target: 5,000 active squads, 500+ marketplace blueprints

### Phase 4 — Scale & University Tier (Months 10–12)
- [ ] University Enterprise Tier launched
- [ ] 20 university incubator partnerships
- [ ] Cross-cohort blueprint lineage visible in public profiles
- [ ] Mobile War Room companion app (approve/block from phone)
- [ ] Target: 10,000 active squads, $2M ARR

---

## 17. Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| RTX laptop requirement limits TAM | High | Medium | Phase in support for cloud-offloaded inference for non-RTX users; NVIDIA expanding RTX base aggressively |
| NemoClaw is alpha / breaking changes | High | High | Maintain abstraction layer between Milimo Claw and NemoClaw internals; contribute fixes upstream |
| Blueprint Marketplace quality dilution | Medium | Medium | Introduce verification badges, operational proof requirements for paid listings |
| University AUP conflicts with autonomous agents | Medium | Medium | Position as study-adjacent business tool, not academic tool; engage compliance teams early |
| Squad member departure disrupts operation | Medium | Low | Claw Handoff Protocol designed specifically for this; automated graceful degradation when a node goes offline |
| Competitor (large) copies the concept | Low (year 1) | High | The blueprint library and self-evolution depth create a multi-year head start; speed to market is critical |

---

## 18. Why Now

Three conditions have converged that make this product viable today and not 18 months ago:

**Condition 1: NemoClaw exists.** The multi-sandbox mesh, self-evolving claws, blueprint versioning, and privacy router are NemoClaw primitives that went live in early 2026. Without this infrastructure, building Milimo Claw would require 18–24 months of infrastructure engineering before writing a single line of product code.

**Condition 2: RTX laptops are in dorm rooms.** The GPU installed base capable of running local NIM is now large enough to be a real consumer market. An estimated 12M+ students globally have RTX-capable laptops — gaming laptops that are now, with NemoClaw, genuinely powerful AI computation platforms.

**Condition 3: Gen Z expects autonomy, not assistance.** The cohort entering college today has grown up with AI. They don't want a tool they prompt. They want a system that runs. The cultural expectation of "my AI handles that" is now present in the target demographic. Milimo Claw is built for the first generation of students who will be genuinely upset if they have to manually do something an AI could have done while they were asleep.

The window to establish the blueprint library, the cohort network effects, and the self-evolution depth advantage is approximately 12–18 months before a well-capitalized competitor can reach architectural parity. This document describes the product that captures that window.

---

*Milimo Claw — built on NVIDIA NemoClaw*
*Document version: 2.0 — April 2026*
*Status: Phase 0 complete — all core infrastructure implemented*
*Last major update: NemoClaw rebuild + Build Claw implementation + security hardening (2026-04-04)*

---
