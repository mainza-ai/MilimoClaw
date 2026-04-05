> ⚠️ **DEPRECATED** — AI generation prompt. Not user documentation.

---
# MILIMO CLAW — SOLO ROLE SELECTION BUG: ROOT CAUSE INVESTIGATION
# ─────────────────────────────────────────────────────────────────────────────
# The solo mode role selection fix has been written twice and neither
# implementation has taken effect. The role selection screen still appears
# after the user selects solo mode. This prompt is an investigation-first
# approach — find exactly why the fix isn't working before writing any code.
#
# Attach alongside:
#   1. commands/onboard.ts       (the wizard — primary suspect)
#   2. onboard/config.ts         (config schema)
#   3. onboard/template.ts       (template discovery)
#   4. onboard/prompt.ts         (prompt utilities)
#   5. cli.ts                    (command registration)
#   6. The compiled dist/ output if available
# ─────────────────────────────────────────────────────────────────────────────

## THE BUG (confirmed, reproduced)

The operator selects Solo Founder template, confirms solo mode (Y),
enters a squad name — and then sees "Your claw role:" with all five
role options. This screen must not appear in solo mode.

The fix has been attempted twice. It has not worked both times.
Before writing any more code, find out why.

---

## STEP 1 — FIND WHERE THE ROLE PROMPT IS ACTUALLY CALLED

Do not assume the fix was applied to the right place. The role prompt
may be called from multiple locations or the file that was edited may
not be the file that actually runs.

Run these searches across the entire codebase:

```bash
# Find every occurrence of the role selection prompt
grep -rn "claw role" milimo/src/ --include="*.ts"
grep -rn "clawRole" milimo/src/ --include="*.ts"
grep -rn "Your claw role" milimo/src/ --include="*.ts"
grep -rn "content.*ops.*analytics" milimo/src/ --include="*.ts"

# Find the compiled output too — this is what actually runs
grep -rn "claw role" milimo/dist/ --include="*.js" 2>/dev/null
grep -rn "Your claw role" milimo/dist/ --include="*.js" 2>/dev/null
```

Report every file and line number where the role prompt appears.
There may be more than one location. The fix may have been applied to
the wrong one.

---

## STEP 2 — VERIFY WHAT IS ACTUALLY EXECUTING

The plugin loads from:
```
/sandbox/.openclaw-data/extensions/milimo/dist/index.js
```

The logs confirm this path. This is the compiled output. Check it:

```bash
# Is the compiled output current?
ls -la /sandbox/.openclaw-data/extensions/milimo/dist/

# Does the compiled file contain the fix?
grep -n "Solo mode" /sandbox/.openclaw-data/extensions/milimo/dist/index.js
grep -n "isSolo" /sandbox/.openclaw-data/extensions/milimo/dist/index.js
grep -n "clawRole.*solo" /sandbox/.openclaw-data/extensions/milimo/dist/index.js

# What does the role selection logic look like in the compiled file?
grep -n -A 5 -B 5 "Your claw role" /sandbox/.openclaw-data/extensions/milimo/dist/index.js
```

If `Solo mode` does not appear in the compiled output, the fix was either:
  a) Written but not compiled (`npm run build` not run)
  b) Written to the wrong source file
  c) Compiled but not deployed to the extensions directory

Report exactly what the grep finds.

---

## STEP 3 — TRACE THE WIZARD EXECUTION FLOW

Read `commands/onboard.ts` in full. Map the exact execution path:

1. Where is `isSolo` set?
2. Where is the role prompt called?
3. Is there a conditional between them, or does the role prompt run unconditionally?
4. What is the current value of `isSolo` when the role prompt is reached?

Look specifically for this pattern — the role prompt running outside
any conditional:

```typescript
// BUG: role prompt runs regardless of isSolo
const isSolo = await promptConfirm(...);
const squadName = await promptInput(...);
const clawRole = await promptSelect("Your claw role", ...); // ← no if(isSolo) check
```

vs what it should be:

```typescript
// CORRECT: role prompt gated on mode
const isSolo = await promptConfirm(...);
const squadName = await promptInput(...);
let clawRole: ClawRole;
if (isSolo) {
  clawRole = "solo";
  console.log("✓ Solo mode — all claws will run on this machine:");
} else {
  clawRole = await promptSelect("Your claw role", ...);
}
```

Report which pattern is in the file right now.

---

## STEP 4 — CHECK THE WIZARD STEP SEQUENCE

The wizard may collect all inputs upfront and then process them, or
it may process each step in sequence. If inputs are collected in a
flat array before being processed, the isSolo check may run after
the role prompt has already been shown.

Look for patterns like:

```typescript
// Problematic: all prompts collected before any conditional
const answers = await inquirer.prompt([
  { name: "template", ... },
  { name: "isSolo", ... },
  { name: "squadName", ... },
  { name: "clawRole", ... },  // ← will always show, even in solo mode
]);
```

If the wizard uses a batch prompt library (inquirer, prompts, enquirer),
the `when` conditional must be used to gate the role question:

```typescript
{
  name: "clawRole",
  type: "list",
  message: "Your claw role:",
  choices: [...],
  when: (answers) => answers.isSolo === false,  // ← only show in mesh mode
}
```

Report whether the wizard uses sequential prompts or batch prompts.
This determines which fix pattern applies.

---

## STEP 5 — APPLY THE CORRECT FIX

Based on what Step 1–4 reveal, apply the fix to the right place
using the right pattern.

### Fix pattern A — Sequential prompts (async/await chain)

If the wizard uses `await promptConfirm()` / `await promptSelect()` style:

```typescript
// In commands/onboard.ts — find the role selection and wrap it:

const isSolo: boolean = await promptConfirm(
  "Operating solo (no mesh coordination)?",
  { default: true }
);

const squadName: string = await promptInput("Squad name", {
  default: "my-squad",
  validate: validateSquadName
});

// ROLE SELECTION — conditional on mode
let clawRole: ClawRole;

if (isSolo) {
  clawRole = "solo" as ClawRole;
  const activeClaws = selectedTemplate.clawsActive.join(" · ");
  console.log(`
✓ Solo mode — all claws will run on this machine:`);
  console.log(`  ${activeClaws}
`);
} else {
  const roleChoices = [
    { value: "content",   title: "content   — Creative output — posts, copy, campaigns, brand voice" },
    { value: "ops",       title: "ops       — Client lifecycle — intake, scoping, delivery, follow-up" },
    { value: "analytics", title: "analytics — Intelligence layer — performance, trends, opportunities" },
    { value: "finance",   title: "finance   — Financial ops — invoicing, pricing, margin tracking" },
    { value: "build",     title: "build     — Engineering — code, PRs, deploys, monitoring" },
  ].filter(r => selectedTemplate.clawsActive.includes(r.value));

  const selected = await promptSelect("Your claw role", roleChoices);
  clawRole = selected as ClawRole;

  const others = selectedTemplate.clawsActive
    .filter(c => c !== clawRole)
    .join(", ");
  console.log(`
✓ You are running the ${clawRole} claw on this machine.`);
  if (others) console.log(`  Other squad members will run: ${others}
`);
}
```

### Fix pattern B — Batch prompts (inquirer/prompts array)

If the wizard uses an array of prompt objects:

```typescript
const answers = await prompts([
  {
    type: "select",
    name: "template",
    message: "Template:",
    choices: templateChoices
  },
  {
    type: "confirm",
    name: "isSolo",
    message: "Operating solo (no mesh coordination)?",
    initial: true
  },
  {
    type: "text",
    name: "squadName",
    message: "Squad name",
    initial: "my-squad"
  },
  {
    // ONLY show this question when NOT solo
    type: (prev, values) => values.isSolo ? null : "select",
    name: "clawRole",
    message: "Your claw role:",
    choices: (prev, values) => {
      const template = getTemplateById(values.template);
      return roleChoices.filter(r => template.clawsActive.includes(r.value));
    }
  }
]);

// Set clawRole to "solo" if solo mode was selected
const clawRole = answers.isSolo ? "solo" : answers.clawRole;
```

The key in batch prompt libraries: `type: null` or `type: false` skips
the prompt entirely. The exact API depends on which library is used —
check `package.json` for the prompt library name.

---

## STEP 6 — UPDATE THE TYPE AND CONFIG

After applying the fix, ensure `ClawRole` accepts `"solo"`:

```typescript
// onboard/config.ts
type ClawRole =
  | "content"
  | "ops"
  | "analytics"
  | "finance"
  | "build"
  | "solo";   // ← ADD THIS if not already present
```

And ensure the config written to disk includes `activeClaws`:

```typescript
// In the config assembly — wherever MilimoConfig is built:
const config: MilimoConfig = {
  // ... other fields ...
  clawRole,
  activeClaws: selectedTemplate.clawsActive,  // e.g. ["content","ops","analytics","finance","build"]
  solo: isSolo,
};
```

---

## STEP 7 — BUILD AND DEPLOY TO THE CORRECT PATH

This is the step that has been missed. Editing source files is not enough.
The plugin loads from the compiled output. After every source change:

```bash
# 1. Build
cd milimo
npm run build

# 2. Verify the fix is in the compiled output
grep -n "Solo mode" dist/index.js
# Must return at least one match. If not, the build failed or wrote to wrong dir.

# 3. Copy compiled output to the extensions directory
cp -r dist/ /sandbox/.openclaw-data/extensions/milimo/dist/

# 4. Verify the deployed file has the fix
grep -n "Solo mode" /sandbox/.openclaw-data/extensions/milimo/dist/index.js
# Must return at least one match.

# 5. Restart openclaw to reload the plugin
# (Ctrl+C the current session, restart openclaw)

# 6. Test
openclaw milimo onboard
# Select: 1 (Solo Founder)
# Solo: Y
# Squad name: test
# VERIFY: Role selection does NOT appear
```

If Step 4 grep returns nothing after Step 3 copy, the build output
directory does not match the extensions load path. Find the correct
path and adjust.

---

## STEP 8 — VERIFY THE FIX

After the fix is deployed and openclaw is restarted, run through
both flows manually:

**Solo flow — role screen must NOT appear:**
```
Template:  Solo Founder (1)
Solo:      Y
Squad:     test-solo
Expected:  "✓ Solo mode — all claws will run on this machine: content · ops · analytics · finance · build"
NOT seen:  "Your claw role:"
```

**Mesh flow — role screen must appear with filtered options:**
```
Template:  Content Agency (2)  ← only 3 claws
Solo:      N
Squad:     test-mesh
Expected:  "Your claw role:" with exactly 3 options (content, ops, analytics)
NOT seen:  finance or build in the role list
```

Both must pass before the fix is considered complete.

---

## WHAT TO REPORT

After completing Steps 1–4 (investigation), report:

1. **Every file** where the role prompt exists (from grep)
2. **Whether the compiled dist/ has the fix** (grep result)
3. **Sequential or batch** prompt pattern in use
4. **The exact lines** where the role prompt is called currently
5. **Why the previous fix attempts failed** (wrong file, not compiled, wrong pattern)

Then apply the correct fix (Step 5), update types (Step 6),
build and deploy (Step 7), and verify (Step 8).

Do not write new code until Steps 1–4 are complete and reported.
The bug has been attempted twice. The third attempt requires knowing
exactly what went wrong before, not guessing again.
