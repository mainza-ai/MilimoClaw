> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — SOLO MODE ROLE SELECTION FIX
# ─────────────────────────────────────────────────────────────────────────────
# Targeted fix. One bug. Five files. Ship it.
#
# Attach this prompt alongside:
#   1. commands/onboard.ts      (existing wizard — UPDATE)
#   2. onboard/config.ts        (config schema — UPDATE)
#   3. solo_init.py             (Python orchestrator — UPDATE)
#   4. The screenshot           (shows the broken flow)
# ─────────────────────────────────────────────────────────────────────────────

## THE BUG

In solo mode, the Milimo Claw onboarding wizard asks the operator to pick
one of five claw roles. In solo mode ALL five claws run simultaneously on
one machine. Asking the operator to pick one is wrong — it implies only
one claw will run, contradicts the solo-founder template, and confuses
every new user who sees it.

The screenshot shows this happening:

  Operating solo (no mesh coordination)? (Y/n): Y
  Squad name [my-squad]: MQ

  Your claw role:               ← THIS ENTIRE SCREEN MUST NOT APPEAR IN SOLO MODE
   * 1. content — Creative output...
     2. ops — Client lifecycle...
     ...

## THE FIX IN ONE SENTENCE

Gate the role selection prompt on operating mode: show it in mesh mode,
skip it entirely in solo mode and confirm what will run instead.

---

## STANDARDS

- TypeScript: strict mode, full type annotations, no `any`
- Python: 3.11+, full type hints, pathlib.Path only
- No new dependencies — use what already exists in the codebase
- Tests: Jest for TypeScript changes, pytest for Python changes
- Do not refactor anything outside the five specific changes below

---

## CHANGE 1 — Gate the role prompt on operating mode

**File:** `milimo/src/commands/onboard.ts`

Find the section of the wizard that handles Step 3 (solo/mesh) and
Step 5 (role selection). Replace the unconditional role prompt with
a conditional block:

```typescript
// Step 3: Solo vs Mesh — EXISTING, do not change
const isSolo = await promptConfirm(
  "Operating solo (no mesh coordination)?",
  { default: true }
);

// Step 4: Squad name — EXISTING, do not change
const squadName = await promptInput("Squad name", { default: "my-squad" });

// Step 5: Role — REPLACE THIS ENTIRELY
let clawRole: ClawRole;

if (isSolo) {
  // Solo mode: all claws run on this machine.
  // Role selection is meaningless — skip it entirely.
  clawRole = "solo";

  const activeClaws = selectedTemplate.clawsActive.join(" · ");
  console.log(`
✓ Solo mode — all claws will run on this machine:
  ${activeClaws}
`);

} else {
  // Mesh mode: operator runs exactly one claw on this machine.
  // Role selection is correct and necessary here.
  console.log("
Mesh mode — which claw are you running on this machine?
");

  // Only offer roles that are active in the selected template
  const allRoles = [
    { value: "content",   label: "content   — Creative output — posts, copy, campaigns, brand voice" },
    { value: "ops",       label: "ops       — Client lifecycle — intake, scoping, delivery, follow-up" },
    { value: "analytics", label: "analytics — Intelligence layer — performance, trends, opportunities" },
    { value: "finance",   label: "finance   — Financial ops — invoicing, pricing, margin tracking" },
    { value: "build",     label: "build     — Engineering — code, PRs, deploys, monitoring" },
  ];

  const availableRoles = allRoles.filter(
    r => selectedTemplate.clawsActive.includes(r.value)
  );

  const selectedRole = await promptSelect(
    "Your claw role",
    availableRoles,
    { default: availableRoles[0].value }
  );

  clawRole = selectedRole as ClawRole;

  const others = selectedTemplate.clawsActive
    .filter(c => c !== clawRole)
    .join(", ");

  console.log(`
✓ You are running the ${clawRole} claw on this machine.`);
  if (others) {
    console.log(`  Other squad members will run: ${others}`);
  }
}
```

---

## CHANGE 2 — Add "solo" to the ClawRole type

**File:** `milimo/src/onboard/config.ts`

```typescript
// BEFORE:
type ClawRole = "content" | "ops" | "analytics" | "finance" | "build";

// AFTER:
type ClawRole = "content" | "ops" | "analytics" | "finance" | "build" | "solo";
```

---

## CHANGE 3 — Fix the existing config display

**File:** `milimo/src/commands/onboard.ts`

The Step 1 existing config display currently shows `Role: build` for a
solo-founder setup — actively misleading. Add a formatter and use it:

```typescript
function formatRoleDisplay(config: MilimoConfig): string {
  if (config.clawRole === "solo") {
    const claws = config.activeClaws?.join(", ") ?? "all claws";
    return `Solo (${claws})`;
  }
  return config.clawRole;
}
```

In the existing config display block, replace:
```typescript
// BEFORE:
console.log(`  Role:     ${config.clawRole}`);

// AFTER:
console.log(`  Role:     ${formatRoleDisplay(config)}`);
```

After this fix, the screenshot scenario re-run will show:
```
Existing Milimo configuration found:
  Squad:    milimoquantum
  Role:     Solo (content, ops, analytics, finance, build)  ← correct
  Template: solo-founder
  Mode:     Solo
```
Instead of the current misleading `Role: build`.

---

## CHANGE 4 — Add activeClaws to MilimoConfig and persist it

**File:** `milimo/src/onboard/config.ts`

```typescript
interface MilimoConfig {
  // ... existing fields unchanged ...

  // ADD THESE TWO:
  clawRole: ClawRole;           // "solo" for solo mode, specific role for mesh
  activeClaws: string[];        // claws active on this squad from the template
}
```

In the wizard's config assembly (wherever the config object is built before
saving), set `activeClaws` from the selected template:

```typescript
const config: MilimoConfig = {
  // ... existing fields ...
  clawRole,
  activeClaws: selectedTemplate.clawsActive,  // ADD THIS
};
```

In `ConfigManager.getDefaults()`, add:
```typescript
activeClaws: ["content", "ops", "analytics", "finance", "build"],
```

In `ConfigManager.migrate()`, add a migration for existing configs
that lack `activeClaws` — derive it from the template field:

```typescript
if (!config.activeClaws) {
  // Derive from template if missing (legacy config migration)
  const TEMPLATE_CLAW_MAP: Record<string, string[]> = {
    "solo-founder":         ["content", "ops", "analytics", "finance", "build"],
    "content-agency":       ["content", "ops", "analytics"],
    "design-studio":        ["content", "ops", "finance"],
    "event-promotion":      ["content", "ops", "analytics"],
    "freelance-collective":  ["ops", "analytics", "finance"],
    "ai-micro-saas":        ["build", "ops", "analytics", "finance"],
    "campus-ai-tool":       ["build", "content", "ops"],
  };
  config.activeClaws = TEMPLATE_CLAW_MAP[config.template] ??
    ["content", "ops", "analytics", "finance", "build"];
}
```

---

## CHANGE 5 — Fix solo_init.py to initialize all sandboxes in solo mode

**File:** `milimo-blueprint/orchestrator/solo_init.py`

Find or add a function that determines which claw sandboxes to initialize.
When `clawRole` is `"solo"`, initialize ALL sandboxes in `activeClaws`.
When `clawRole` is a specific claw name (mesh mode), initialize only that one.

```python
def get_claws_to_initialize(config: dict) -> list[str]:
    """
    Returns the list of claw roles whose sandboxes should be initialized.

    Solo mode (clawRole == "solo"):
        Returns all active claws from the template.
        All five sandboxes are created on this machine.

    Mesh mode (clawRole is a specific claw name):
        Returns only the one claw this operator runs.
        Other sandboxes are on other machines.
    """
    claw_role: str = config.get("clawRole", "solo")
    active_claws: list[str] = config.get(
        "activeClaws",
        ["content", "ops", "analytics", "finance", "build"]
    )

    if claw_role == "solo":
        return active_claws
    else:
        # Mesh mode — verify the role is actually in the active claws list
        if claw_role not in active_claws:
            raise ValueError(
                f"clawRole '{claw_role}' is not in activeClaws {active_claws}. "
                f"Check config.json."
            )
        return [claw_role]
```

Find wherever `solo_init.py` currently initializes sandbox directories
and replace any hardcoded or single-role logic with a call to
`get_claws_to_initialize(config)`.

---

## WHAT THE WIZARD LOOKS LIKE AFTER THE FIX

Solo flow — role screen gone:
```
🦀 MILIMO CLAW — Onboarding Wizard 🦀

Template:
 * 1. Solo Founder — solo
   ...

Select [1-5] (default: 1): 1

Operating solo (no mesh coordination)? (Y/n): Y

Squad name [my-squad]: MQ

✓ Solo mode — all claws will run on this machine:
  content · ops · analytics · finance · build

Operator name [mainza]:
```

Mesh flow — role screen shown, filtered to template claws:
```
Operating solo (no mesh coordination)? (Y/n): N

Mesh mode — which claw are you running on this machine?

  1. content   — Creative output — posts, copy, campaigns, brand voice
  2. ops       — Client lifecycle — intake, scoping, delivery, follow-up
  3. analytics — Intelligence layer — performance, trends, opportunities
  4. finance   — Financial ops — invoicing, pricing, margin tracking
  5. build     — Engineering — code, PRs, deploys, monitoring

Select [1-5] (default: 1): 3

✓ You are running the analytics claw on this machine.
  Other squad members will run: content, ops, finance, build
```

---

## TESTS

**Jest — `milimo/src/__tests__/onboard-role-selection.test.ts`**

```typescript
describe("Role selection conditional logic", () => {

  it("solo mode: clawRole is set to 'solo'", async () => {
    const result = await simulateOnboarding({ isSolo: true, template: "solo-founder" });
    expect(result.config.clawRole).toBe("solo");
  });

  it("solo mode: role prompt function is never called", async () => {
    const promptSelectSpy = jest.fn();
    await simulateOnboarding({ isSolo: true, template: "solo-founder", promptSelect: promptSelectSpy });
    expect(promptSelectSpy).not.toHaveBeenCalled();
  });

  it("solo mode: activeClaws contains all template claws", async () => {
    const result = await simulateOnboarding({ isSolo: true, template: "solo-founder" });
    expect(result.config.activeClaws).toEqual(
      ["content", "ops", "analytics", "finance", "build"]
    );
  });

  it("mesh mode: role prompt is shown", async () => {
    const promptSelectSpy = jest.fn().mockResolvedValue("analytics");
    await simulateOnboarding({ isSolo: false, template: "solo-founder", promptSelect: promptSelectSpy });
    expect(promptSelectSpy).toHaveBeenCalledTimes(1);
  });

  it("mesh mode: only template-active claws are offered", async () => {
    const promptSelectSpy = jest.fn().mockResolvedValue("content");
    await simulateOnboarding({
      isSolo: false,
      template: "content-agency",   // only content, ops, analytics
      promptSelect: promptSelectSpy
    });
    const offeredRoles = promptSelectSpy.mock.calls[0][1].map((r: any) => r.value);
    expect(offeredRoles).toEqual(["content", "ops", "analytics"]);
    expect(offeredRoles).not.toContain("finance");
    expect(offeredRoles).not.toContain("build");
  });

  it("mesh mode: clawRole set to selected role", async () => {
    const result = await simulateOnboarding({
      isSolo: false,
      template: "solo-founder",
      selectedRole: "finance"
    });
    expect(result.config.clawRole).toBe("finance");
  });

});

describe("formatRoleDisplay", () => {

  it("returns readable string for solo mode", () => {
    const config = { clawRole: "solo", activeClaws: ["content", "ops", "analytics", "finance", "build"] };
    expect(formatRoleDisplay(config)).toBe("Solo (content, ops, analytics, finance, build)");
  });

  it("returns role name unchanged for mesh mode", () => {
    const config = { clawRole: "content", activeClaws: ["content"] };
    expect(formatRoleDisplay(config)).toBe("content");
  });

  it("handles missing activeClaws gracefully", () => {
    const config = { clawRole: "solo" };
    expect(formatRoleDisplay(config)).toBe("Solo (all claws)");
  });

});
```

**pytest — `milimo-blueprint/tests/test_solo_init_role.py`**

```python
import pytest
from milimo_blueprint.orchestrator.solo_init import get_claws_to_initialize


def test_solo_mode_returns_all_active_claws():
    config = {
        "clawRole": "solo",
        "activeClaws": ["content", "ops", "analytics", "finance", "build"]
    }
    result = get_claws_to_initialize(config)
    assert result == ["content", "ops", "analytics", "finance", "build"]


def test_solo_mode_respects_template_active_claws():
    """content-agency only has 3 claws — solo mode should init only those 3."""
    config = {
        "clawRole": "solo",
        "activeClaws": ["content", "ops", "analytics"]
    }
    result = get_claws_to_initialize(config)
    assert result == ["content", "ops", "analytics"]
    assert "finance" not in result
    assert "build" not in result


def test_mesh_mode_returns_single_claw():
    config = {
        "clawRole": "analytics",
        "activeClaws": ["content", "ops", "analytics", "finance", "build"]
    }
    result = get_claws_to_initialize(config)
    assert result == ["analytics"]


def test_mesh_mode_role_not_in_active_claws_raises():
    config = {
        "clawRole": "build",
        "activeClaws": ["content", "ops", "analytics"]   # build not in template
    }
    with pytest.raises(ValueError, match="not in activeClaws"):
        get_claws_to_initialize(config)


def test_defaults_to_all_claws_when_role_missing():
    config = {}   # no clawRole key
    result = get_claws_to_initialize(config)
    assert len(result) == 5


def test_defaults_to_all_claws_when_role_is_solo_and_activeClaws_missing():
    config = {"clawRole": "solo"}   # no activeClaws key
    result = get_claws_to_initialize(config)
    assert len(result) == 5
```

---

## VERIFICATION

After applying all five changes, run through this manually:

```
1. Run: openclaw milimo onboard
2. Select template: Solo Founder (option 1)
3. Confirm: Operating solo? Y
4. Enter squad name
5. VERIFY: Role selection screen does NOT appear
6. VERIFY: Confirmation shows all active claws
7. Complete onboarding
8. Run: openclaw milimo squad status
9. VERIFY: Role shows "Solo (content, ops, analytics, finance, build)"
   not "build" or any single claw name
```

Then for mesh:
```
1. Run: openclaw milimo onboard
2. Select template: Content Agency (option 2) — 3 claws only
3. Confirm: Operating solo? N
4. VERIFY: Role prompt appears with exactly 3 options (not 5)
   — content, ops, analytics only
5. Select a role
6. VERIFY: clawRole in config.json matches selection
```

All Jest and pytest tests must pass before the fix is considered complete.
