> ⚠️ **DEPRECATED** — Obsolete. Model detection is now handled by the privacy router.

---

# Model Detection in MilimoClaw

## Problem
The TUI shows `inference/nvidia/nemotron-3-super-120b-a12b` but the user selected `z-ai/glm5` during NemoClaw onboarding.

## Root Cause Analysis

### Two Separate Configs

1. **NemoClaw Config** (`/sandbox/.nemoclaw/config.json`)
   - Contains user's actual model selection from onboarding
   - Example: `"model": "z-ai/glm5"`
   - Read by: Plugin banner display

2. **OpenClaw Config** (`/sandbox/.openclaw/openclaw.json`)
   - Contains gateway/agent model configuration
   - Has `agents.defaults.model.primary` field
   - Read by: Gateway process, TUI session

### The Disconnect

During NemoClaw onboarding:
- User selects model → saved to `.nemoclaw/config.json`
- NemoClaw creates default `.openclaw/openclaw.json` with hardcoded models
- The selected model is NOT propagated to `.openclaw/openclaw.json`

### Model Flow

```
NemoClaw Onboarding
       │
       ├─► .nemoclaw/config.json (model: z-ai/glm5)
       │
       └─► .openclaw/openclaw.json (agents.defaults.model.primary: inference/nvidia/nemotron-3-super-120b-a12b)
                    │
                    └─► Gateway reads this
                              │
                              └─► TUI session uses gateway's model
```

### Why Plugin Shows Correct Model

The MilimoClaw plugin reads from `.nemoclaw/config.json`:
```
Inference: z-ai/glm5 @ https://inference.local/v1
```

### Why TUI Shows Wrong Model

The TUI session inherits from gateway which reads `.openclaw/openclaw.json`:
```
inference/nvidia/nemotron-3-super-120b-a12b
```

## Solution

After NemoClaw onboarding, the selected model must be propagated to `.openclaw/openclaw.json`:

```python
import json

# Read NemoClaw config
with open('/sandbox/.nemoclaw/config.json') as f:
    nc_config = json.load(f)

selected_model = nc_config['model']  # e.g., "z-ai/glm5"
endpoint_url = nc_config['endpointUrl']

# Update OpenClaw config
with open('/sandbox/.openclaw/openclaw.json') as f:
    oc_config = json.load(f)

# Add the selected model as a provider
provider_key = 'inference'  # or derive from endpoint type
oc_config['models']['providers'][provider_key] = {
    'baseUrl': endpoint_url,
    'apiKey': 'openshell-managed',
    'api': 'openai-completions',
    'models': [{
        'id': selected_model,
        'name': selected_model,
        'contextWindow': 131072,
        'maxTokens': 4096
    }]
}

# Set as default agent model
oc_config['agents']['defaults']['model']['primary'] = f'inference/{selected_model}'

with open('/sandbox/.openclaw/openclaw.json', 'w') as f:
    json.dump(oc_config, f, indent=2)
```

## Current Workaround

After onboarding, manually update the config or restart gateway:

```bash
# In sandbox
openclaw gateway stop
# Update openclaw.json with correct model
openclaw gateway start --allow-unconfigured
```

Or delete session and let it use whatever model the gateway provides.
