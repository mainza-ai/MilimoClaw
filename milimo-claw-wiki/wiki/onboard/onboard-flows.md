# Onboard Flows

**Summary**: User onboarding and template validation flows.

**Sources**:
- `milimo/src/onboard/validate.ts`
- `milimo/src/onboard/config.ts`
- `milimo/src/onboard/template.ts`
- `milimo/src/commands/onboard.ts`

**Last updated**: 2026-04-15

**Tags**: #typescript #onboard #flows

---

## Overview

Onboard flows handle:
- Template validation
- Configuration setup
- Role selection
- Squad initialization

---

## Flow Steps

```
1. Validate template file
2. Load template configuration
3. Prompt for role selection
4. Configure assistant
5. Initialize sandbox
6. Write configuration
7. Start claw processes
```

---

## Key Functions

### Template Validation

```typescript
function validateTemplateFile(templatePath: string): TemplateValidationResult {
  // Calls Python validation module
  // Returns valid/config/errors
}
```

### Template Info

```typescript
interface TemplateInfo {
  name: string;
  displayName: string;
  category: string;
  description: string;
  squadSize: number;
  clawsActive: string[];
}

function getTemplateInfo(templatePath: string): TemplateInfo | null
```

### Configuration

```typescript
interface OnboardConfig {
  squadId: string;
  operatorId: string;
  template: string;
  role: string;
  solo: boolean;
  warRoomMode: "full" | "minimal" | "disabled";
  assistant: {
    name: string;
    creature: string;
    vibe: string;
    emoji: string;
  };
}
```

---

## CLI Integration

### `milimo onboard`

```bash
openclaw milimo onboard \
  --squad my-squad \
  --role content \
  --template solo-founder \
  --solo \
  --war-room-mode full
```

### `milimo init`

```bash
openclaw milimo init \
  --squad my-squad \
  --role ops \
  --assistant-name Nova
```

---

## Source Files

| File | Purpose |
|------|---------|
| `onboard/validate.ts` | Template validation |
| `onboard/config.ts` | Configuration management |
| `onboard/template.ts` | Template loading |
| `onboard/prompt.ts` | Interactive prompts |
| `commands/onboard.ts` | CLI handler |
| `commands/init.ts` | Init handler |

---

## Python Integration

Template validation calls Python:

```python
from orchestrator.solo_init import load_solo_founder_template

config = load_solo_founder_template(template_path)
```

---

## Related Pages

- [[cli-commands]] — CLI reference
- [[solo-init]] — Python solo init
- [[template-overview]] — Template overview
