# Testing MilimoClaw

## Test Environment

- **Platform**: macOS Apple Silicon (M1/M2/M3)
- **Sandbox**: my-assistant
- **Model**: nvidia/nemotron-3-super-120b-a12b
- **Provider**: nvidia-nim (cloud)

---

## Prerequisites

Before testing, ensure:

1. Native NemoClaw onboarding completed
2. Sandbox in Ready phase
3. Port forward active
4. MilimoClaw plugin installed

```bash
# Verify prerequisites
nemoclaw my-assistant status
openshell forward start --background 18789 my-assistant
```

---

## Test 1: Sandbox Health

```bash
nemoclaw my-assistant status
```

**Expected output:**
```
Sandbox: my-assistant
Phase: Ready
Model: nvidia/nemotron-3-super-120b-a12b
Provider: nvidia-nim
Policies: pypi, npm
```

---

## Test 2: Inference Connectivity

```bash
openshell sandbox connect my-assistant
```

Inside sandbox:
```bash
openclaw agent --agent main --local -m "Respond with: BUILD_CLAW_ONLINE" --session-id test
```

**Expected**: Response containing "BUILD_CLAW_ONLINE"

---

## Test 3: Session Memory

Inside sandbox:
```bash
openclaw agent --agent main --local -m "My favorite color is quantum blue. Remember this." --session-id memory-test
openclaw agent --agent main --local -m "What is my favorite color?" --session-id memory-test
```

**Expected**: Response containing "quantum blue"

---

## Test 4: Code Generation

Inside sandbox:
```bash
openclaw agent --agent main --local -m "Write a Python function fibonacci(n) with type hints and docstring. Output only code." --session-id code-test
```

**Expected**: Clean Python function with proper formatting

---

## Test 5: MilimoClaw Plugin

```bash
openshell sandbox connect my-assistant
```

Inside sandbox:
```bash
# Check plugin
openclaw plugins list

# Run MilimoClaw onboarding
openclaw milimo onboard
# Select: Solo Founder → milimoquantum → Build Claw

# Check squad status
openclaw milimo squad status
```

---

## Test 6: Build Claw Code Review

Inside sandbox:
```bash
openclaw agent --agent main --local -m "
Review this code and list all issues:
def calc(x):
    return x/0
Provide: Issue, Severity, Fix
" --session-id build-review
```

**Expected**: Identifies division by zero

---

## Test 7: TUI Interface

```bash
openshell sandbox connect my-assistant
```

Inside sandbox:
```bash
openclaw tui
```

In TUI, type: "Hello, I am testing Build Claw. What can you help me build?"

---

## Quick Reference Commands

### Host Machine

```bash
nemoclaw list                      # List sandboxes
nemoclaw my-assistant status       # Check sandbox
openshell gateway info             # Check gateway
openshell forward start --background 18789 my-assistant  # Port forward
openshell sandbox connect my-assistant  # Connect
```

### Inside Sandbox

```bash
openclaw --version                 # Version check
openclaw plugins list              # List plugins
openclaw tui                       # Launch TUI
openclaw agent --agent main --local -m "Hello" --session-id test  # Test inference
openclaw milimo squad status       # MilimoClaw status
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Sandbox not ready | Run `nemoclaw onboard` on host |
| Inference timeout | Check API key: `openshell inference get` |
| Plugin not found | Install: `openclaw plugins install /tmp/milimo` |
| Port forward fails | Stop existing: `openshell forward stop 18789` |

---

## Related Documentation

- [Quick Start Guide](../QUICK_START.md)
- [Troubleshooting](../troubleshooting/TROUBLESHOOTING.md)
