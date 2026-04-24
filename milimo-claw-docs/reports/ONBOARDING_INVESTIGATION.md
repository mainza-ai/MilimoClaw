> ⚠️ **DEPRECATED** — Historical status report. All phases complete. See [README.md](../../README.md) for current state.

---
# NemoClaw Onboarding Investigation

**Date:** 2026-03-19
**Purpose:** Understand NemoClaw's onboarding flow to design MilimoClaw's onboarding process

---

## Executive Summary

NemoClaw implements a comprehensive 9-step onboarding wizard that handles inference endpoint configuration, API key validation, provider registration, and state persistence. MilimoClaw can leverage this foundation while adding squad-specific configuration (templates, roles, mesh formation).

---

## NemoClaw Onboarding Architecture

### Entry Points

| Entry Point | Command | Description |
|-------------|---------|-------------|
| CLI | `openclaw nemoclaw onboard` | Full interactive wizard |
| CLI (non-interactive) | `openclaw nemoclaw onboard --api-key nvapi-xxx --endpoint build --model xxx` | Scriptable setup |
| Slash Command | `/nemoclaw onboard` | Chat-based status check |

### Core Files

```
nemoclaw/src/
├── commands/
│   └── onboard.ts      # Main onboarding logic (429 lines)
├── onboard/
│   ├── config.ts       # State persistence (54 lines)
│   ├── prompt.ts       # Interactive prompts (72 lines)
│   └── validate.ts     # API key validation (58 lines)
└── index.ts            # Plugin registration (uses onboarding config)
```

---

## Onboarding Flow (9 Steps)

### Step 0: Check Existing Configuration

```typescript
const existing = loadOnboardConfig();
if (existing) {
  showConfig(existing, logger);
  if (!nonInteractive) {
    const reconfigure = await promptConfirm("Reconfigure?", false);
    if (!reconfigure) return;
  }
}
```

- Loads from `~/.nemoclaw/config.json`
- Shows current configuration if exists
- Prompts to reconfigure or exit

### Step 1: Endpoint Selection

```typescript
const ENDPOINT_TYPES = ["build", "ncp", "nim-local", "vllm", "ollama", "custom"];
```

**Endpoint Options:**

| Type | Description | Default URL |
|------|-------------|-------------|
| `build` | NVIDIA Build (build.nvidia.com) | `https://integrate.api.nvidia.com/v1` |
| `ncp` | NVIDIA Cloud Partner | Custom (prompted) |
| `nim-local` | Self-hosted NIM | `http://nim-service.local:8000/v1` |
| `vllm` | Local vLLM | `http://host.openshell.internal:8000/v1` |
| `ollama` | Local Ollama | `http://host.openshell.internal:11434/v1` |
| `custom` | Custom endpoint | Prompted |

**Auto-detection:**
```typescript
function detectOllama(): { installed: boolean; running: boolean } {
  const installed = testCommand("command -v ollama >/dev/null 2>&1");
  const running = testCommand("curl -sf http://localhost:11434/api/tags >/dev/null 2>&1");
  return { installed, running };
}
```

If Ollama is detected running on localhost:11434, it's auto-selected.

### Step 2: Endpoint URL Resolution

Each endpoint type has URL resolution logic:
- `build`: Fixed URL
- `ncp`: Prompts for partner name + URL
- `nim-local`: Prompts for URL (default provided)
- `vllm`: Uses host gateway URL
- `ollama`: Uses host gateway URL
- `custom`: Prompts for URL

### Step 3: Credential Collection

```typescript
function resolveCredentialEnv(endpointType: EndpointType): string {
  switch (endpointType) {
    case "build":
    case "ncp":
    case "custom":
      return "NVIDIA_API_KEY";
    case "nim-local":
      return "NIM_API_KEY";
    case "vllm":
    case "ollama":
      return "OPENAI_API_KEY";
  }
}
```

**API Key Sources (in order):**
1. Command-line argument (`--api-key`)
2. Environment variable (e.g., `NVIDIA_API_KEY`)
3. Interactive prompt

**For local endpoints:**
```typescript
function defaultCredentialForEndpoint(endpointType: EndpointType): string {
  switch (endpointType) {
    case "vllm": return "dummy";
    case "ollama": return "ollama";
    default: return "";
  }
}
```

### Step 4: API Key Validation

```typescript
export async function validateApiKey(
  apiKey: string,
  endpointUrl: string,
): Promise<ValidationResult> {
  const url = `${endpointUrl.replace(/\/+$/, "")}/models`;
  // 10 second timeout
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
    signal: controller.signal,
  });
  // Returns: { valid: boolean; models: string[]; error: string | null }
}
```

**Validation behavior:**
- Calls `/models` endpoint
- 10-second timeout
- For local endpoints: continues on failure (service may not be running)
- For cloud endpoints: fails on validation error

### Step 5: Model Selection

```typescript
const DEFAULT_MODELS = [
  { id: "${NEMOCLAW_MODEL}", label: "Nemotron 3 Super 120B (default)" },
  { id: "nvidia/llama-3.1-nemotron-ultra-253b-v1", label: "Nemotron Ultra 253B" },
  { id: "nvidia/llama-3.3-nemotron-super-49b-v1.5", label: "Nemotron Super 49B v1.5" },
  { id: "nvidia/nemotron-3-nano-30b-a3b", label: "Nemotron 3 Nano 30B" },
];
```

**Selection logic:**
1. If model provided via CLI arg, use it
2. Otherwise, filter models from validation response (Nemotron models)
3. Fall back to DEFAULT_MODELS if no models returned

### Step 6: Profile & Provider Resolution

```typescript
function resolveProfile(endpointType: EndpointType): string {
  switch (endpointType) {
    case "build": return "default";
    case "ncp":
    case "custom": return "ncp";
    case "nim-local": return "nim-local";
    case "vllm": return "vllm";
    case "ollama": return "ollama";
  }
}

function resolveProviderName(endpointType: EndpointType): string {
  switch (endpointType) {
    case "build": return "nvidia-nim";
    case "ncp":
    case "custom": return "nvidia-ncp";
    case "nim-local": return "nim-local";
    case "vllm": return "vllm-local";
    case "ollama": return "ollama-local";
  }
}
```

### Step 7: Confirmation

Shows configuration summary and prompts for confirmation:
- Endpoint type and URL
- NCP partner (if applicable)
- Model
- API Key (masked)
- Credential env var
- Profile
- Provider

### Step 8: Apply Configuration

**8a: Create/Update Provider**
```typescript
execOpenShell([
  "provider", "create",
  "--name", providerName,
  "--type", "openai",
  "--credential", `${credentialEnv}=${apiKey}`,
  "--config", `OPENAI_BASE_URL=${endpointUrl}`,
]);
```

Handles `AlreadyExists` error by updating instead.

**8b: Set Inference Route**
```typescript
execOpenShell(["inference", "set", "--provider", providerName, "--model", model]);
```

**8c: Save Config**
```typescript
saveOnboardConfig({
  endpointType,
  endpointUrl,
  ncpPartner,
  model,
  profile,
  credentialEnv,
  onboardedAt: new Date().toISOString(),
});
```

### Step 9: Success & Next Steps

```
Onboarding complete!

 Endpoint: https://integrate.api.nvidia.com/v1
 Model: ${NEMOCLAW_MODEL}
 Credential: $NVIDIA_API_KEY

Next steps:
 openclaw nemoclaw launch   # Bootstrap sandbox
 openclaw nemoclaw status   # Check configuration
```

---

## State Persistence

### Config Location

```
~/.nemoclaw/config.json
```

### Config Schema

```typescript
interface NemoClawOnboardConfig {
  endpointType: EndpointType;
  endpointUrl: string;
  ncpPartner: string | null;
  model: string;
  profile: string;
  credentialEnv: string;
  onboardedAt: string;
}
```

### Config Functions

```typescript
// Load config (returns null if not exists)
function loadOnboardConfig(): NemoClawOnboardConfig | null;

// Save config
function saveOnboardConfig(config: NemoClawOnboardConfig): void;

// Clear config
function clearOnboardConfig(): void;
```

---

## Interactive Prompt Utilities

### Input Prompt

```typescript
async function promptInput(question: string, defaultValue?: string): Promise<string>
```

- Shows question with optional default
- Returns trimmed input or default value

### Confirm Prompt

```typescript
async function promptConfirm(question: string, defaultYes = true): Promise<boolean>
```

- Shows `(Y/n)` or `(y/N)` hint
- Returns boolean

### Select Prompt

```typescript
async function promptSelect(
  question: string,
  options: SelectOption[],
  defaultIndex = 0,
): Promise<string>

interface SelectOption {
  label: string;
  value: string;
  hint?: string;
}
```

- Displays numbered list with hints
- Supports default selection (marked with `*`)

---

## Plugin Registration Usage

The onboarding config is used during plugin registration:

```typescript
// In index.ts
const onboardCfg = loadOnboardConfig();
const providerCredentialEnv = onboardCfg?.credentialEnv ?? "NVIDIA_API_KEY";
const providerLabel = onboardCfg
  ? `NVIDIA NIM (${onboardCfg.endpointType}${onboardCfg.ncpPartner ? ` - ${onboardCfg.ncpPartner}` : ""})`
  : "NVIDIA NIM (build.nvidia.com)";

api.registerProvider({
  id: "nvidia-nim",
  label: providerLabel,
  envVars: [providerCredentialEnv],
  // ...
});
```

---

## Key Patterns for MilimoClaw

### 1. Modular Onboarding Structure

```
milimo/src/
├── commands/
│   └── onboard.ts          # Main onboarding logic
├── onboard/
│   ├── config.ts           # State persistence
│   ├── prompt.ts           # Reuse from NemoClaw or extend
│   ├── validate.ts         # Milimo-specific validation
│   └── template.ts         # Template loading
```

### 2. State Location

```
~/.milimo/
├── state.json              # Main state (squad, role, template)
├── blueprints/             # Local blueprint versions
├── audit/                  # Audit logs
├── mesh/                   # Mesh state
└── evolution/              # Evolution history
```

### 3. Configuration Schema

```typescript
interface MilimoOnboardConfig {
  // Squad basics
  squadName: string;
  clawRole: ClawRole;
  template: string;
  solo: boolean;

  // Mesh configuration
  meshMembers: string[];
  meshSecret?: string;

  // Inference (inherits from NemoClaw)
  inferenceProfile: string;

  // Timestamps
  initializedAt: string;
  onboardedAt: string;
}
```

### 4. Onboarding Steps for MilimoClaw

| Step | NemoClaw | MilimoClaw |
|------|----------|------------|
| 0 | Check existing | Check existing + check NemoClaw onboarding |
| 1 | Endpoint selection | Template selection (solo-founder, content-agency, etc.) |
| 2 | URL resolution | Role assignment (content, ops, analytics, finance, build) |
| 3 | Credential | Operator policy configuration |
| 4 | Validation | Template validation (solo_init.py) |
| 5 | Model selection | Inheritance from NemoClaw (or override per-claw) |
| 6 | Profile/Provider | War Room mode selection |
| 7 | Confirmation | Confirmation |
| 8 | Apply | Apply (state + directories + validate template) |
| 9 | Next steps | Next steps (launch War Room, verify squad) |

---

## Recommendations for MilimoClaw Onboarding

### 1. Extend NemoClaw Onboarding

- Check for `~/.nemoclaw/config.json` first
- If missing, prompt to run `openclaw nemoclaw onboard` first
- Reuse `loadOnboardConfig()` for inference settings

### 2. Template-Driven Setup

```typescript
// Available templates
const TEMPLATES = [
  { id: "solo-founder", label: "Solo Founder", hint: "One-person operation" },
  { id: "content-agency", label: "Content Agency", hint: "Content-first squad" },
  { id: "design-studio", label: "Design Studio", hint: "Visual creative squad" },
  { id: "custom", label: "Custom", hint: "Manual configuration" },
];
```

### 3. Role-Specific Prompts

After role selection, show role-specific hints:

```typescript
const ROLE_DESCRIPTIONS = {
  content: "Creative output — posts, copy, campaigns, brand voice",
  ops: "Client lifecycle — intake, scoping, delivery, follow-up",
  analytics: "Intelligence layer — performance, trends, opportunities",
  finance: "Financial ops — invoicing, pricing, margin tracking",
  build: "Engineering — code, PRs, deploys, monitoring (tech squads)",
};
```

### 4. Validation Integration

Use `solo_init.py` validation during onboarding:

```typescript
// In onboard.ts
const templateValidation = await execBlueprint({
  action: "validate",
  template: selectedTemplate,
});
if (!templateValidation.valid) {
  logger.error(`Template validation failed: ${templateValidation.errors}`);
  return;
}
```

### 5. Solo vs Mesh Mode

```typescript
const solo = await promptConfirm("Operating solo (no mesh coordination)?", true);
if (!solo) {
  logger.info("Mesh mode selected. Each squad member will need to:");
  logger.info("1. Run: openclaw milimo init --squad <name> --role <role>");
  logger.info("2. Share mesh secret for authentication");
  const meshSecret = await promptInput("Enter mesh secret (or generate new)");
}
```

---

## Integration Points

### NemoClaw Dependency

```typescript
// Check NemoClaw onboarding first
const nemoclawConfig = loadNemoClawConfig();
if (!nemoclawConfig) {
  logger.error("NemoClaw must be onboarded first.");
  logger.info("Run: openclaw nemoclaw onboard");
  return;
}
```

### OpenShell Commands

MilimoClaw should use OpenShell CLI for:
- Provider creation/update (same as NemoClaw)
- Inference route setting
- Sandbox management

### Blueprint Validation

Call Python validation from TypeScript:

```typescript
import { execFileSync } from "node:child_process";

function validateTemplate(templatePath: string): ValidationResult {
  const output = execFileSync("python3", [
    "-c",
    `from orchestrator.solo_init import load_solo_founder_template; import json; print(json.dumps(load_solo_founder_template("${templatePath}")))`
  ], { encoding: "utf-8" });
  return JSON.parse(output);
}
```

---

## Summary

NemoClaw's onboarding provides a solid foundation:

1. **Modular architecture** - Separate concerns (config, prompts, validation)
2. **State persistence** - JSON in home directory
3. **Interactive + non-interactive modes** - Scriptable for automation
4. **Validation** - Real-time API key validation
5. **Auto-detection** - Detects Ollama automatically

MilimoClaw should:
1. Extend NemoClaw's config loading
2. Add template/role selection steps
3. Validate templates using Python modules
4. Create Milimo-specific state structure
5. Support both solo and mesh modes
