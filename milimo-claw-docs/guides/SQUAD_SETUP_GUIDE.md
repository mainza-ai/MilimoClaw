# Milimo Claw — Squad Setup Guide

> Step-by-step walkthrough for forming a squad and deploying your first claws.

---

## Overview

This guide walks a squad through the complete setup process — from installing prerequisites to having a running multi-claw mesh.

**Time required:** ~20 minutes for a 2–4 person squad.

---

## Prerequisites

### Every Squad Member Needs

| Requirement | Details |
|---|---|
| **GPU** | RTX-capable NVIDIA GPU (for local inference) |
| **OS** | Linux Ubuntu 22.04+ or macOS with Docker |
| **Docker** | Installed and running |
| **Node.js** | v20.0.0 or later |
| **Git** | Latest version |
| **Network** | All squad members on the same network (or VPN) |

### One Squad Member Decides

- **Squad name** — identifies your squad
- **Template** — which pre-built configuration to start from
- **Role assignments** — who runs which claw

---

## Step 1: Clone & Install

Every squad member runs:

```bash
git clone https://github.com/mainza-ai/MilimoClaw.git
cd MilimoClaw
npm install
```

---

## Step 2: Build the Docker Image

Every squad member builds the sandbox image:

```bash
docker build -t milimo-claw -f Dockerfile .
```

This creates a Docker image with:
- OpenClaw CLI
- NemoClaw plugin
- Milimo Claw plugin
- All blueprints and policies
- PyYAML for the orchestrator

---

## Step 3: Onboard NemoClaw (Inference)

Before using MilimoClaw, each member must onboard NemoClaw for inference:

```bash
openclaw nemoclaw onboard
```

This configures:
- Inference endpoint (NVIDIA Build, NCP, or local)
- API key authentication
- Model selection

---

## Step 4: Choose a Template

Before running `milimo onboard`, decide which template fits your squad:

### Creative & Commerce (3-Claw Mesh)

| Template | Best For | Claws |
|---|---|---|
| `content-agency` | Social media content creation | Content + Ops + Analytics |
| `design-studio` | Design services with invoicing | Content + Ops + Analytics + Build |

### Tech Startups (5-Claw Mesh)

| Template | Best For | Claws |
|---|---|---|
| `tech-consultancy` | Full-stack tech consulting | Build + Ops + Analytics + Finance + Content |

### Solo Operation

| Template | Best For | Claws |
|---|---|---|
| `solo-founder` | One-person operation | All 5 claws |

---

## Step 5: Assign Roles

Each squad member owns one or more claw roles:

### For a 2-Person Squad

| Person | Roles |
|---|---|
| Person A | Content + Analytics |
| Person B | Ops + Finance |

### For a 3-Person Squad

| Person | Role |
|---|---|
| Person A | Content |
| Person B | Ops + Finance |
| Person C | Analytics |

### For a 4-Person Squad

| Person | Role |
|---|---|
| Person A | Content |
| Person B | Ops |
| Person C | Analytics |
| Person D | Finance |

### For a 5-Person Tech Squad

| Person | Role |
|---|---|
| Person A | Content |
| Person B | Ops |
| Person C | Analytics |
| Person D | Finance |
| Person E | Build |

---

## Step 6: Onboard the Squad

### First Member (Squad Creator)

The first person creates the squad:

```bash
openclaw milimo onboard
```

Follow the wizard:
1. Select template (e.g., `content-agency`)
2. Choose **Mesh mode** (not solo)
3. Enter squad name
4. Select your role
5. Enter operator name
6. Choose War Room mode
7. **Generate mesh secret** — save this!

The wizard will output:
```
Generated mesh secret (share with squad members):
  AbCdEf1234567890...
```

### Subsequent Members

Each additional member joins with their assigned role:

```bash
openclaw milimo onboard
```

Follow the wizard:
1. Select same template
2. Choose **Mesh mode**
3. Enter same squad name
4. Select their role
5. Enter operator name
6. Choose War Room mode
7. **Enter existing mesh secret** (from step 6)

---

## Step 7: Verify the Mesh

Every member can check the mesh status:

```bash
openclaw milimo squad status
```

Expected output:

```
Squad: my-squad
Template: content-agency
Blueprint: v0.1.0
Mode: normal

Mesh Topology:
✅ content — online (Laptop A)
✅ ops — online (Laptop B)
✅ analytics — online (Laptop C)
✅ finance — online (Laptop D)

Pending War Room Actions: 0
```

Check onboarding configuration:

```bash
openclaw milimo squad onboard-status
```

---

## Step 8: Launch the War Room

Any squad member can open the War Room:

```bash
openclaw milimo warroom
```

The War Room shows:
- Live action feed from all claws
- Pending actions requiring approval
- Escalation alerts
- Audit trail

---

## Step 9: Set Squad Policies

During onboarding, the squad sets shared policies:

### Approval Thresholds

| Action Type | Suggested Mode |
|---|---|
| Internal drafts | AUTO |
| Social posts | REVIEW |
| Client proposals | REVIEW |
| Brand voice changes | HOLD |
| Invoices >$500 | VETO |

### Finals Mode Criteria

Decide when and how Finals Mode will be triggered:

```bash
openclaw milimo squad finals-mode --duration 2weeks --resume-date 2026-05-12
```

---

## What Happens Next

Once the mesh is live:

1. **Claws start operating** — each within its sandbox boundaries
2. **Inter-claw messages flow** — briefs from Ops to Content, queries to Analytics, etc.
3. **War Room populates** — pending actions queue up for squad review
4. **Self-evolution begins** — after 2 weeks, claws start building their first tools
5. **Blueprint versions** — your squad's intelligence is being captured and versioned

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|---|---|
| `milimo onboard` says "NemoClaw not onboarded" | Run `openclaw nemoclaw onboard` first |
| `milimo onboard` fails with "no template found" | Ensure `milimo-blueprint/templates/` is in the Docker image |
| Mesh shows claw as "offline" | Check Docker container is running: `docker ps` |
| War Room shows no pending actions | Normal for fresh installs — actions appear as claws operate |
| Privacy router error | Verify `privacy_policy.yaml` exists in blueprint directory |
| "Invalid mesh secret" | Ensure all members use the exact same secret |

### Getting Help

1. Check the [Architecture Guide](../ARCHITECTURE.md) for how components interact
2. Check the [CLI Reference](../CLI_REFERENCE.md) for exact command syntax
3. Review [Privacy & Security](../PRIVACY_AND_SECURITY.md) for data routing questions

---

## Author

**Mainza Kangombe** — [LinkedIn](https://www.linkedin.com/in/mainza-kangombe-6214295)
