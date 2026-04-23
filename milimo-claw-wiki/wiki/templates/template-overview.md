# Template Overview

**Summary**: All available squad templates for MilimoClaw.

**Sources**:
- `milimo-blueprint/templates/`

**Last updated**: 2026-04-23

**Tags**: #templates #squads

---

## Available Templates

| Template | Claws | Category | Description |
|----------|-------|----------|-------------|
| [[solo-founder]] | All 6 | Founder | Full setup for solo operators |
| `content-agency` | Content + Ops + Analytics | Creative | Content-focused business |
| `design-studio` | Content + Ops + Finance | Creative | Design-focused business |
| `event-promotion` | Content + Ops + Analytics | Creative | Event-focused business |
| `freelance-collective` | Content + Ops + Analytics + Finance | Commerce | Freelance coordination |
| `ai-micro-saas` | Build + Ops + Analytics + Finance | Tech | SaaS development |
| `campus-ai-tool` | Build + Content + Ops | Tech | University-focused tools |

---

## Template Details

### Solo Founder

**Claws**: Content, Ops, Analytics, Finance, Build, Assistant

**Use Case**: Single operator running all business functions.

**Key Features**:
- All 6 claws active
- Staggered evolution schedule
- Deep Work mode support
- Full War Room access

---

### Content Agency

**Claws**: Content, Ops, Analytics

**Use Case**: Content creation agency with multiple clients.

**Key Features**:
- Focus on content production
- Client management via Ops
- Performance tracking via Analytics
- No build or finance claws

---

### Design Studio

**Claws**: Content, Ops, Finance

**Use Case**: Design-focused creative business.

**Key Features**:
- Visual content creation
- Client management
- Financial tracking
- No analytics or build claws

---

### Event Promotion

**Claws**: Content, Ops, Analytics

**Use Case**: Event planning and promotion business.

**Key Features**:
- Event content creation
- Event logistics via Ops
- Attendee analytics
- No finance or build claws

---

### Freelance Collective

**Claws**: Content, Ops, Analytics, Finance

**Use Case**: Coordinating freelance professionals.

**Key Features**:
- Portfolio and marketing materials via Content
- Project coordination via Ops
- Performance tracking
- Financial management
- No build claw

---

### AI Micro-SaaS

**Claws**: Build, Ops, Analytics, Finance

**Use Case**: Developing and operating AI-powered SaaS products.

**Key Features**:
- Full development capability
- Customer management
- Usage analytics
- Revenue tracking
- No content claw

---

### Campus AI Tool

**Claws**: Build, Content, Ops

**Use Case**: University-focused AI tools and content.

**Key Features**:
- Educational content creation
- Student/academic ops
- Development capability
- No analytics or finance claws

---

## Template Configuration

Templates are YAML files in `milimo-blueprint/templates/`:

```yaml
template_id: content-agency
name: Content Agency
description: Content-focused business setup
claws:
  - content
  - ops
  - analytics
config:
  evolution_schedule:
    content: "Sunday 02:05"
    ops: "Sunday 02:15"
    analytics: "Sunday 02:25"
```

---

## Creating Custom Templates

1. Create YAML file in `milimo-blueprint/templates/`
2. Define included claws
3. Set evolution schedule
4. Configure approval thresholds
5. Test with `milimo init --template your-template`

---

## Related Pages

- [[solo-founder]] — Primary template
- [[evolution-cycle]] — Evolution system
- [[content-claw]] — Content Claw
- [[ops-claw]] — Ops Claw
- [[analytics-claw]] — Analytics Claw
- [[finance-claw]] — Finance Claw
- [[build-claw]] — Build Claw
