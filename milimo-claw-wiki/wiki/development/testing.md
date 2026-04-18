# Testing

**Summary**: Test structure, coverage, and execution for MilimoClaw.

**Sources**:
- `raw/AGENTS.md`
- `milimo-blueprint/tests/`

**Last updated**: 2026-04-14

**Tags**: #development #testing

---

## Test Frameworks

| Language | Framework | Location |
|----------|-----------|----------|
| Python | pytest | `milimo-blueprint/tests/` |
| TypeScript | Jest | `milimo/src/__tests__/` |
| Integration | Custom | `test/` |

---

## Test Structure

### Phase A Tests — RUN FIRST

**Critical**: Phase A isolation tests must pass before any other tests.

```bash
pytest -m phase_a tests/test_phase_a_isolation.py
```

Tests verify:
- Each claw cannot read other claws' mounts
- Cross-mounts are read-only
- Network egress is restricted to allowed APIs
- Process isolation is enforced

### Python Tests

Location: `milimo-blueprint/tests/`

| Test File | Coverage |
|-----------|----------|
| `test_phase_a_isolation.py` | Filesystem isolation |
| `test_phase_b_warroom.py` | War Room approval |
| `test_ops_mvr_integration.py` | Ops Claw integration |
| `test_finance_mvr_integration.py` | Finance Claw integration |
| `test_build_mvr_integration.py` | Build Claw integration |
| `test_analytics_integration.py` | Analytics Claw integration |

### TypeScript Tests

Location: `milimo/src/__tests__/`

| Test File | Coverage |
|-----------|----------|
| `cli.test.ts` | CLI commands |
| `warroom.test.ts` | War Room TUI |
| `approval.test.ts` | Approval engine |
| `mesh.test.ts` | Mesh gateway |

### Integration Tests

Location: `test/`

| Test File | Coverage |
|-----------|----------|
| `integration/mesh-coordinator.test.js` | Mesh routing |
| `integration/evolution-cycle.test.js` | Evolution cycle |
| `integration/privacy-router.test.js` | Privacy routing |
| `milimo-e2e.sh` | End-to-end |

---

## Running Tests

### All Tests

```bash
# Python tests
pytest

# TypeScript tests
npm test

# Integration tests
npm run test:integration

# E2E tests
./test/milimo-e2e.sh
```

### Specific Tests

```bash
# Phase A only
pytest -m phase_a

# Specific claw
pytest tests/test_content_claw.py

# Coverage report
pytest --cov=orchestrator --cov-report=html
```

---

## Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Content Claw | 90% | ~85% |
| Ops Claw | 90% | ~82% |
| Analytics Claw | 90% | ~88% |
| Finance Claw | 90% | ~80% |
| Build Claw | 90% | ~84% |
| Mesh Coordinator | 95% | ~92% |

---

## Test Conventions

### Python

```python
# Test file naming
test_{module_name}.py

# Test class naming
class TestClassName:

# Test method naming
def test_function_name_expected_behavior(self):
    pass

# Fixtures
@pytest.fixture
def mock_claw():
    return MockClaw()
```

### TypeScript

```typescript
// Test file naming
{module}.test.ts

// Test suite
describe('ModuleName', () => {
  it('should do something', () => {
    expect(true).toBe(true);
  });
});
```

---

## Mocking

### Stripe

Test mode only (`sk_test_*`) — no live keys ever.

### GitHub

Test repository only — never a live production repo.

---

## Related Pages

- [[conventions]] — Code conventions
- [[debugging]] — Debug guide
- [[common-issues]] — Troubleshooting
