> ⚠️ **DEPRECATED** — Historical status report. All phases complete. See [README.md](../../README.md) for current state.

---
# MilimoClaw Onboarding Implementation

**Date:** 2026-03-19
**Status:** Implemented

---

## Summary

Implemented a comprehensive onboarding wizard for MilimoClaw based on NemoClaw's architecture. The onboarding system provides a 12-step interactive wizard for squad configuration, template selection, and role assignment.

---

## Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `milimo/src/onboard/config.ts` | State persistence, NemoClaw integration | 92 |
| `milimo/src/onboard/prompt.ts` | Interactive prompts (input, confirm, select) | 113 |
| `milimo/src/onboard/validate.ts` | Template validation, name validation | 121 |
| `milimo/src/onboard/template.ts` | Template discovery and loading | 176 |
| `milimo/src/commands/onboard.ts` | Main onboarding wizard | 337 |

---

## Files Modified

| File | Changes |
|------|---------|
| `milimo/src/cli.ts` | Added `onboard` command and `squad onboard-status` |
| `milimo/src/index.ts` | Uses onboarding config for banner display |
| `milimo/package.json` | Added `yaml` dependency |

---

## Onboarding Flow

### 12 Steps

1. **NemoClaw Check** — Verifies inference is configured
2. **Existing Config Check** — Shows current config if exists
3. **Template Selection** — Choose from built-in or discovered templates
4. **Solo/Mesh Mode** — Single operator vs. team mesh
5. **Squad Name** — Unique identifier with validation
6. **Role Assignment** — Primary claw role selection
7. **Operator Name** — Human operator identifier
8. **War Room Mode** — Dashboard complexity (full/minimal/disabled)
9. **Mesh Secret** — Generate or enter existing (for mesh mode)
10. **Template Validation** — Python validation via `solo_init.py`
11. **Confirmation** — Review before applying
12. **Apply** — Create directories, save config, show next steps

---

## CLI Commands

### `openclaw milimo onboard`

```bash
# Interactive wizard
openclaw milimo onboard

# Non-interactive setup
openclaw milimo onboard \
  --squad my-squad \
  --role content \
  --template solo-founder \
  --solo \
  --war-room-mode full
```

### `openclaw milimo squad onboard-status`

Shows current onboarding configuration.

---

## Built-in Templates

| Template | Category | Squad Size | Description |
|----------|----------|------------|-------------|
| `solo-founder` | solo | 1 | One-person operation with all claws |
| `content-agency` | agency | 3 | Content-first squad for agencies |
| `design-studio` | studio | 4 | Visual creative squad for designers |
| `tech-consultancy` | consultancy | 5 | Full-stack tech squad with build focus |
| `custom` | custom | — | Manual configuration from scratch |

---

## Configuration Schema

Saved to `~/.milimo/config.json`:

```typescript
interface MilimoOnboardConfig {
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;
  meshMembers: string[];
  meshSecret: string | null;
  operatorName: string;
  warRoomMode: "full" | "minimal" | "disabled";
  onboardedAt: string;
  initializedAt: string;
  blueprintVersion: string;
}
```

---

## NemoClaw Integration

The onboarding checks for NemoClaw configuration:

```typescript
function loadNemoClawConfig(): { model: string; endpointUrl: string } | null
```

If NemoClaw is not onboarded, the wizard:
1. Warns the user
2. Shows instructions: `openclaw nemoclaw onboard`
3. Prompts to continue anyway or exit

---

## Template Validation

Templates are validated by calling Python:

```typescript
function validateTemplateFile(templatePath: string): TemplateValidationResult
```

This executes:
```python
from orchestrator.solo_init import load_solo_founder_template
config = load_solo_founder_template(templatePath)
```

---

## Directory Structure

Created by onboarding:

```
~/.milimo/
├── config.json          # Onboarding configuration
├── blueprints/          # Local blueprint versions
├── audit/               # Audit logs
├── mesh/                # Mesh state
├── evolution/           # Evolution history
└── sandbox/             # Sandbox data
```

---

## Documentation Updated

| File | Changes |
|------|---------|
| `CLI_REFERENCE.md` | Added `onboard` and `squad onboard-status` commands |
| `QUICK_START_MACOS.md` | Updated step 6 for onboarding wizard |
| `SQUAD_SETUP_GUIDE.md` | Complete rewrite with onboarding flow |

---

## Next Steps

1. Test onboarding in Docker container
2. Add more templates to `milimo-blueprint/templates/`
3. Implement mesh secret verification for multi-member squads
4. Add War Room mode configuration UI
