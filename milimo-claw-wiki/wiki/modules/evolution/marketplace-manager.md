# Marketplace Manager

**Summary**: Peer-to-peer registry for publishing, discovering, and downloading squad blueprints.

**Sources**: `milimo-blueprint/orchestrator/marketplace_manager.py`

**Last updated**: 2026-04-17

**Tags**: #marketplace #blueprints #sharing

---

## Overview

`MarketplaceManager` provides a simulated peer-to-peer marketplace for sharing squad blueprints. Operators can publish their configured blueprints, search for others' blueprints, and download them to fork their own squads.

## Key Class

### MarketplaceManager

```python
from marketplace_manager import MarketplaceManager

marketplace = MarketplaceManager()

# Publish a blueprint
blueprint_id = marketplace.publish(
    snapshot=blueprint_snapshot,
    price="free",
    name="AI SaaS Starter",
    squad_id="mainza/squad-001",
)

# Search for blueprints
results = marketplace.search(query="saas", category="tech")

# Download and fork
forked = marketplace.download(blueprint_id)
```

## Storage Structure

```
~/.milimo/marketplace/
├── registry.json       # Marketplace index
└── blueprints/         # Blueprint artifacts
    └── @squad_id_name-v1.0.0.json
```

## Methods

### publish()

List a blueprint on the marketplace.

```python
blueprint_id = marketplace.publish(
    snapshot=BlueprintSnapshot,
    price="free",           # or "$29", "$99", etc.
    name="My Blueprint",
    squad_id="author/squad-name",
)
```

**Returns**: Marketplace blueprint ID in format `@{squad_id}/{name}-v{version}`

**Registry entry**:
| Field | Description |
|-------|-------------|
| `id` | Marketplace blueprint ID |
| `name` | Blueprint display name |
| `business_type` | From blueprint metadata |
| `version` | Blueprint version |
| `author` | Squad ID of publisher |
| `price` | Price string |
| `tags` | Niche tags |
| `tool_count` | Number of tools |
| `fork_count` | Times downloaded |
| `published_at` | ISO timestamp |
| `verified` | Has integrity digest |

### search()

Discover blueprints by query and category.

```python
results = marketplace.search(
    query="saas",           # Matched against name, author, tags
    category="tech",        # Filter by business_type
)
```

**Returns**: `list[dict]` sorted by verified status and fork count.

**Search behavior**:
- Case-insensitive matching
- Partial match on name, author, or any tag
- Sort: verified first, then by fork_count descending

### get_listing()

Retrieve metadata for a single blueprint.

```python
listing = marketplace.get_listing("@author/squad-v1.0.0")
```

**Returns**: `dict` with listing metadata or `None` if not found.

### download()

Download a blueprint and increment its fork count.

```python
snapshot = marketplace.download("@author/squad-v1.0.0")
```

**Returns**: `BlueprintSnapshot` or `None` if not found.

**Side effect**: Increments `fork_count` in registry.

## Blueprint ID Format

```
@{squad_id}/{safe-name}-v{version}
```

Where `safe-name` is lowercased, alphanumerics only, with non-alnum converted to `-`.

**Examples**:
- `@mainza/squad-001/ai-saas-starter-v1.0.0`
- `@alice/ecommerce-store-v2.1.0`

## Marketplace Directory

Default: `~/.milimo/marketplace/`

Override via constructor:
```python
marketplace = MarketplaceManager(marketplace_dir="/custom/path")
```

## BlueprintSnapshot

Imported from `blueprint_manager`:

```python
from blueprint_manager import BlueprintSnapshot

snapshot = BlueprintSnapshot(
    meta=BlueprintMeta(...),
    tools_inventory={...},
    integrity={"digest": "..."},
)
```

## Related Pages

- [[claw-launcher]] — Claw startup and blueprint loading
- `blueprint_manager.py` — BlueprintSnapshot definition (see Also below)

## See Also

- `milimo-blueprint/orchestrator/marketplace_manager.py` — Source file
- `milimo-blueprint/orchestrator/blueprint_manager.py` — BlueprintSnapshot definition
