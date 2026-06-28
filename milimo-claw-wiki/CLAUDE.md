# MilimoClaw Wiki — AI Instructions

> This wiki is the ultimate source of truth for the MilimoClaw project.
> Based on Andrej Karpathy's LLM Wiki pattern, optimized for AI comprehension.
> **Any AI working on this codebase must read this file in full before modifying the wiki.**

---

## 1. Purpose & Philosophy

### What This Wiki Is

This Obsidian vault is a **structured, interlinked knowledge base** that serves as:

1. **The single source of truth** for MilimoClaw architecture, implementation, and operation
2. **A navigation layer** connecting all documentation, specs, and code
3. **An AI-readable reference** optimized for large language model comprehension
4. **A living document** that evolves with the codebase

### What This Wiki Is Not

- Not a replacement for code comments or inline documentation
- Not a duplicate of `milimo-claw-docs/` — it synthesizes and connects
- Not a changelog — use `wiki/log.md` for that
- Not a place for temporary notes — those go in scratch files

### Design Principles

1. **Synthesis over duplication** — Wiki pages summarize and connect, original docs are authoritative
2. **Wiki-links everywhere** — Every concept should be linked to its definition
3. **Clear hierarchy** — Ground truth precedence is explicit and enforced
4. **AI-first formatting** — Structured sections, consistent templates, explicit relationships

---

## 2. Ground Truth Hierarchy

When documents conflict, this order determines which is authoritative:

| Priority | Source | Authority | Example |
|----------|--------|-----------|---------|
| 1 | **Claw spec documents** | Internal claw behavior | `MILIMO_CLAW_CONTENT_CLAW_SPEC.md` defines Content Claw's exact behavior |
| 2 | **Solo template spec** | Cross-claw coordination | `MILIMO_CLAW_SOLO_TEMPLATE_SPEC_V2.md` defines message sequencing |
| 3 | **Template YAML files** | Configuration values | `solo-founder.yaml` defines schedule times |
| 4 | **AGENTS.md** | Quick reference summary | This file summarizes specs, doesn't override them |
| 5 | **Wiki pages** | Synthesis and navigation | Wiki explains concepts, cites specs for authority |
| 6 | **Code** | Implementation reality | Code should match specs; if not, it's a bug |

### Conflict Resolution

```
If wiki page conflicts with spec → Spec wins
If AGENTS.md conflicts with spec → Spec wins
If code conflicts with spec → Code is wrong (bug)
```

**This wiki is NEVER the tiebreaker.** Always defer to higher-priority sources.

---

## 3. Folder Structure

```
milimo-claw-wiki/
├── CLAUDE.md              # This file — AI instructions
├── Welcome.md             # Vault welcome page
├── .obsidian/             # Obsidian configuration
│   ├── workspace.json     # UI layout
│   ├── graph.json         # Graph view settings
│   ├── appearance.json    # Theme settings
│   ├── app.json           # App preferences
│   └── core-plugins.json  # Enabled plugins
│
├── raw/                   # IMMUTABLE — Source documents (symlinks)
│   ├── AGENTS.md -> ../../.agents/AGENTS.md
│   ├── ARCHITECTURE.md -> ../../milimo-claw-docs/ARCHITECTURE.md
│   └── [spec symlinks]    # Key spec files, never modified
│
├── templates/             # Page templates for new wiki pages
│   ├── claw-template.md
│   ├── module-template.md
│   └── concept-template.md
│
└── wiki/                  # WIKI PAGES — AI-maintained
    ├── index.md           # Master table of contents
    ├── log.md             # Append-only operation log
    │
    ├── architecture/      # System architecture documentation
    │   ├── system-overview.md
    │   ├── sandbox-isolation.md
    │   ├── inter-claw-communication.md
    │   ├── mesh-coordinator.md
    │   └── privacy-router.md
    │
    ├── claws/             # Individual claw documentation
    │   ├── content-claw.md
    │   ├── ops-claw.md
    │   ├── analytics-claw.md
    │   ├── finance-claw.md
    │   ├── build-claw.md
    │   └── assistant-lucy.md
    │
    ├── modules/           # Code module documentation
    │   ├── content/       # Content Claw modules
    │   ├── ops/           # Ops Claw modules
    │   ├── analytics/     # Analytics Claw modules
    │   ├── finance/       # Finance Claw modules
    │   ├── build/         # Build Claw modules
 │   └── assistant/ # Assistant Claw modules
    │
    ├── coordination/      # Cross-claw coordination
    │   ├── message-contracts.md
    │   ├── sequencing-rules.md
    │   ├── approval-thresholds.md
    │   └── war-room.md
    │
    ├── templates/         # Squad templates
    │   ├── solo-founder.md
    │   └── template-overview.md
    │
    ├── policies/          # Sandbox policies
    │   ├── policy-overview.md
    │   └── network-egress.md
    │
    ├── evolution/         # Self-evolution system
    │   ├── evolution-cycle.md
    │   ├── tool-generation.md
    │   └── pattern-detection.md
    │
    ├── development/       # Development guides
    │   ├── conventions.md
    │   ├── testing.md
    │   └── debugging.md
    │
    ├── troubleshooting/   # Troubleshooting guides
    │   ├── common-issues.md
    │   ├── issues-and-fixes.md
    │   └── sandbox-sync.md
    │
    └── reference/         # Quick reference
        ├── ground-truth-hierarchy.md
        ├── message-matrix.md
        ├── file-structure.md
        └── cli-reference.md
```

### Folder Purposes

| Folder | Purpose | Who Can Modify |
|--------|---------|----------------|
| `raw/` | Immutable source documents (symlinks) | Never modified by AI |
| `templates/` | Page templates for consistency | AI creates new, rarely edits |
| `wiki/` | All wiki content | AI maintains, human curates |
| `.obsidian/` | Obsidian app configuration | Manual edits only |

---

## 4. Page Format Standards

### Required Sections

Every wiki page MUST include these sections in order:

```markdown
# Page Title

**Summary**: One to two sentences describing this page.

**Sources**: List of source files this page draws from.

**Last updated**: ISO date (YYYY-MM-DD).

**Tags**: #category #subcategory #specific-tag

---

Main content goes here. Use clear headings and short paragraphs.

Link to related concepts using [[wiki-links]] throughout the text.

## Related Pages

- [[related-concept-1]]
- [[related-concept-2]]

## See Also

- External link to source file or documentation
```

### Naming Conventions

| Content Type | Format | Example |
|--------------|--------|---------|
| Claw pages | `{claw}-claw.md` | `content-claw.md` |
| Module pages | `{module-name}.md` | `content-generator.md` |
| Concept pages | `{concept}.md` | `privacy-router.md` |
| Multi-word | `kebab-case.md` | `inter-claw-communication.md` |
| Reference | `{topic}-reference.md` | `cli-reference.md` |

### Tags Hierarchy

```
#architecture
  #architecture/sandbox
  #architecture/mesh
  #architecture/privacy

#claw
  #claw/content
  #claw/ops
  #claw/analytics
  #claw/finance
  #claw/build
  #claw/assistant

#coordination
  #coordination/contracts
  #coordination/approvals
  #coordination/warroom

#evolution
  #evolution/tools
  #evolution/patterns

#development
  #development/testing
  #development/conventions

#troubleshooting
  #troubleshooting/issues
  #troubleshooting/sync
```

---

## 5. Wiki-Link Usage

### Link Syntax

```
[[page-name]]              # Link to page
[[page-name|display text]] # Link with display text
[[page-name#section]]      # Link to specific section
[[page-name#section|text]] # Section link with display text
```

### When to Link

Link to another wiki page when:

1. **First mention** of a concept that has its own page
2. **Referencing a claw** — always link to its wiki page
3. **Referencing a module** — always link to its module page
4. **Referencing a message type** — link to message-contracts.md
5. **Cross-referencing** related concepts

### Link Examples

```markdown
The [[content-claw]] generates all creative content autonomously.

When a [[project-brief]] message arrives, the [[brief-manager]] validates it.

The [[privacy-router]] intercepts all inference calls (see [[sandbox-isolation]]).

For approval rules, see [[approval-thresholds]].
```

### What NOT to Link

Don't link:

- Common English words
- File paths (unless they have wiki pages)
- External URLs (use markdown links)
- Code symbols that don't have wiki pages

---

## 6. Ingest Workflow

When the user adds a new source or asks you to ingest documentation:

### Step 1: Read and Understand

```
1. Read the full source document completely
2. Identify key concepts, entities, and relationships
3. Note any contradictions with existing wiki pages
```

### Step 2: Discuss Before Writing

```
4. Summarize key takeaways for the user
5. Ask clarifying questions about ambiguous sections
6. Confirm which pages should be created/updated
```

### Step 3: Create Wiki Pages

```
7. Create summary page in wiki/ named after the source
8. Create concept pages for each major idea or entity
9. Update existing pages that reference new concepts
```

### Step 4: Link and Index

```
10. Add wiki-links to connect related pages
11. Update wiki/index.md with new pages
12. Append entry to wiki/log.md
```

### Ingest Example

User adds `MILIMO_CLAW_CONTENT_CLAW_SPEC.md`:

1. Read the spec (it's comprehensive, ~500 lines)
2. Identify: Content Claw role, modules, messages, evolution tools
3. Discuss: "This spec defines Content Claw in detail. I'll create:
   - content-claw.md (summary)
   - Module pages for content_generator, brief_manager, etc.
   - Update message-contracts.md with Content Claw's messages"
4. After user confirms, create all pages
5. Update index.md
6. Log the operation

---

## 7. Question Answering Protocol

When the user asks a question about MilimoClaw:

### Step 1: Find Relevant Pages

```
1. Read wiki/index.md first to understand structure
2. Identify pages that might contain the answer
3. Read those pages in full
```

### Step 2: Synthesize Answer

```
4. Combine information from multiple pages if needed
5. Cite specific wiki pages in your response
6. Include relevant wiki-links for further reading
```

### Step 3: Handle Missing Information

```
7. If answer is not in wiki, say so clearly
8. Check if source documents in raw/ have the answer
9. Offer to create a new wiki page if the answer is valuable
```

### Response Format

```markdown
Based on [[page-name]], the answer is...

Key points:
- Point 1 (source: [[page-1]])
- Point 2 (source: [[page-2]])

See also:
- [[related-page-1]]
- [[related-page-2]]
```

---

## 8. Lint & Audit Rules

When asked to lint or audit the wiki:

### Checks to Perform

| Check | Description | Action |
|-------|-------------|--------|
| **Orphan pages** | Pages with no inbound links | Add links from related pages |
| **Broken links** | Links to non-existent pages | Create missing pages or fix links |
| **Missing concept pages** | Concepts mentioned but not defined | Create concept pages |
| **Outdated claims** | Claims that conflict with newer sources | Flag for review |
| **Format violations** | Pages not following template | Reformat to standard |
| **Missing tags** | Pages without proper tags | Add appropriate tags |

### Audit Output Format

```markdown
## Wiki Audit Report — YYYY-MM-DD

### Orphan Pages
- [[orphan-page]] — no inbound links
  - Fix: Add link from [[related-page]]

### Broken Links
- [[page-with-broken-link]] links to [[non-existent]]
  - Fix: Create [[non-existent]] or correct the link

### Missing Concept Pages
- "some-concept" mentioned in [[page-1]], [[page-2]] but not defined
  - Fix: Create [[some-concept]] page

### Format Violations
- [[page]] missing "Sources" section
  - Fix: Add sources and reformat

### Summary
- Total pages: XX
- Orphans: X
- Broken links: X
- Missing concepts: X
```

---

## 9. MilimoClaw-Specific Rules

### Terminology

| Term | Meaning | Wiki Page |
|------|---------|-----------|
| **Claw** | An autonomous agent in the mesh | [[content-claw]], etc. |
| **Claw Handler** | The main entry point for a claw's logic (replaces "skills") | [[content-claw]], etc. |
| **Mesh** | The inter-claw communication network | [[mesh-coordinator]] |
| **Sandbox** | Isolated execution environment for each claw | [[sandbox-isolation]] |
| **War Room** | TUI for viewing all pending actions | [[war-room]] |
| **Brief** | Project requirements sent to a claw | [[message-contracts]] |
| **Evolution Cycle** | Sunday process that generates new tools | [[evolution-cycle]] |
| **Privacy Router** | Routes inference calls based on data sensitivity | [[privacy-router]] |
| **Profile** | NemoClaw agent profile (OpenClaw vs Hermes) | [[hermes-profile]] |

### Message Contract Notation

When documenting messages:

```markdown
`message_type` — **From:** sender-claw → **To:** recipient-claw

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | UUID | Yes | Unique identifier |
| payload.field | type | Yes/No | Description |

**Trigger:** When this message is sent
**SLA:** Response requirements
**Approval:** REVIEW/HOLD/AUTO
```

### Approval Threshold Notation

```markdown
| Action | Mode | Notes |
|--------|------|-------|
| Action name | REVIEW/HOLD/AUTO | Special conditions |

**REVIEW** — Requires operator approval before execution
**HOLD** — Requires explicit operator release (blocks until released)
**AUTO** — Executed automatically, logged for morning digest
```

### Filesystem Mount Notation

```markdown
**Mount:** `/sandbox/{claw-name}`

| Path | Purpose | Access |
|------|---------|--------|
| /sandbox/.openclaw/milimo/claws/content/drafts/ | Draft content | Read-write |
| /sandbox/.openclaw/milimo/claws/analytics/reports/ | Intelligence reports | Read-only |
```

---

## 10. Navigation Instructions

### Quick Navigation

1. **Start at** `wiki/index.md` — Master table of contents
2. **Use tags** — Click any tag to see related pages
3. **Follow links** — Every concept is linked
4. **Check backlinks** — Use Obsidian's backlinks panel

### Graph View

The graph view shows page relationships:

- **Blue nodes** — Architecture pages
- **Green nodes** — Claw pages
- **Orange nodes** — Coordination pages
- **Purple nodes** — Evolution pages
- **Red nodes** — Troubleshooting pages

### Finding Specific Information

| Looking For | Start At |
|-------------|----------|
| How a claw works | `wiki/claws/{claw}-claw.md` |
| Message schemas | `wiki/coordination/message-contracts.md` |
| Approval rules | `wiki/coordination/approval-thresholds.md` |
| Debugging a problem | `wiki/troubleshooting/common-issues.md` |
| Code module details | `wiki/modules/{claw}/{module}.md` |
| Ground truth order | `wiki/reference/ground-truth-hierarchy.md` |

---

## 11. Rules Summary

1. **Never modify** anything in the `raw/` folder
2. **Always update** `wiki/index.md` after creating new pages
3. **Always append** to `wiki/log.md` after changes
4. **Keep page names** lowercase with hyphens (`kebab-case.md`)
5. **Write clearly** — plain language, short paragraphs
6. **Link liberally** — every concept should be linked
7. **Cite sources** — every factual claim needs a source reference
8. **Follow templates** — use the appropriate template for each page type
9. **Defer to specs** — wiki summarizes, specs are authoritative
10. **When uncertain** — ask the user for guidance

---

## 12. AI Behavior Checklist

Before making any wiki changes, verify:

- [ ] I have read this CLAUDE.md in full
- [ ] I understand the ground truth hierarchy
- [ ] I am not modifying `raw/` folder contents
- [ ] I am following the correct page template
- [ ] I am adding appropriate wiki-links
- [ ] I will update `index.md` after creating pages
- [ ] I will append to `log.md` after changes

---

*MilimoClaw Wiki — The ultimate source of truth for autonomous hustle.*
*"The milimo never stops. Work. Without working."*
