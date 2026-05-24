---
title: NemoClaw Reference
tags: [reference, nemoclaw, architecture]
created: 2026-05-11
updated: 2026-05-11
---

# NemoClaw Reference

> NemoClaw v0.0.38 — Alpha (March 2026+). Interfaces may change without notice.

## What Is NemoClaw?

An open-source reference stack for running [[OpenClaw]] always-on assistants inside [[OpenShell]] sandboxes. It provides:

1. **CLI tooling** — `nemoclaw` command with 15+ subcommands
2. **OpenClaw plugin** — TypeScript plugin that registers hooks + providers
3. **Blueprint system** — YAML-defined sandbox orchestration
4. **Security hardening** — SSRF validation, secret scanning, network policies

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  nemoclaw CLI  (TypeScript → dist/)                   │
│  ├── onboard / credentials / deploy / policies        │
│  └── status / logs / connect / destroy / doctor        │
├──────────────────────────────────────────────────────┤
│  nemoclaw plugin  (OpenClaw extension)                │
│  ├── /nemoclaw slash command                          │
│  ├── before_agent_start hook (runtime context)        │
│  ├── before_tool_call hook (secret scanner)           │
│  └── registerProvider (inference routing)             │
├──────────────────────────────────────────────────────┤
│  nemoclaw-blueprint  (YAML)                           │
│  ├── blueprint.yaml (version, profiles, components)   │
│  ├── policies/ (network presets)                      │
│  └── model-specific-setup/ (agent compatibility)      │
├──────────────────────────────────────────────────────┤
│  OpenShell  (NVIDIA sandbox runtime)                  │
│  ├── L7 Proxy (inference routing, TLS termination)    │
│  ├── Landlock (filesystem isolation)                  │
│  └── Network policies (deny-by-default egress)        │
└──────────────────────────────────────────────────────┘
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `nemoclaw onboard` | Interactive setup wizard (sandbox + inference + policy) |
| `nemoclaw list` | List all sandboxes |
| `nemoclaw <name> status` | Show sandbox status |
| `nemoclaw <name> connect` | Open interactive terminal |
| `nemoclaw <name> logs` | Stream sandbox logs |
| `nemoclaw <name> destroy` | Remove sandbox |
| `nemoclaw <name> policy-add <preset>` | Add a network policy preset |
| `nemoclaw <name> policy-remove <preset>` | Remove a network policy preset |
| `nemoclaw <name> policy-list` | List active policies |
| `nemoclaw <name> channels add <type>` | Add messaging bridge (Telegram/Discord/Slack) |
| `nemoclaw <name> channels stop` | Stop messaging bridges |
| `nemoclaw credentials list` | List staged credentials |
| `nemoclaw credentials reset` | Clear staged credentials |
| `nemoclaw deploy` | Deploy to remote GPU (Brev) |
| `nemoclaw doctor` | Run diagnostic checks |
| `nemoclaw gc` | Garbage collect unused resources |
| `nemoclaw update` | Update NemoClaw |

## Plugin API

The OpenClaw plugin API available to Milimo:

| Method | Signature | Purpose |
|--------|-----------|---------|
| `registerCommand` | `(def: PluginCommandDefinition) => void` | Register `/slash` commands |
| `registerProvider` | `(provider: ProviderPlugin) => void` | Register inference provider |
| `registerService` | `(service: PluginService) => void` | Register background service |
| `resolvePath` | `(input: string) => string` | Resolve sandbox-relative paths (SSRF-safe) |
| `on` | `(hookName, handler) => void` | Attach to lifecycle hooks |
| `logger` | `PluginLogger` | Structured logging |
| `config` | `OpenClawConfig` | Global OpenClaw config |
| `pluginConfig` | `OpenClawConfig` | Plugin-specific config |

### Lifecycle Hooks

| Hook | Payload | Return | When |
|------|---------|--------|------|
| `before_agent_start` | `(event, hookContext)` | `{ prependContext: string }` | Before each agent turn |
| `before_tool_call` | `(event: { toolName, params })` | `{ block, blockReason }` or `{ params }` | Before tool execution |

## Inference Profiles

Defined in `blueprint.yaml`:

| Profile | Provider | Model | Endpoint |
|---------|----------|-------|----------|
| `default` | NVIDIA NIM | `nvidia/nemotron-3-super-120b-a12b` | `integrate.api.nvidia.com` |
| `ncp` | NVIDIA NCP | Same | Dynamic endpoint |
| `nim-local` | OpenAI-compat | Same | `nim-service.local:8000` |
| `vllm` | OpenAI-compat | `Nemotron-3-Nano-30B-A3B-FP8` | `localhost:8000` |
| `routed` | OpenAI-compat | `nvidia-routed` | `localhost:4000` (router) |

## Network Policy Presets

Built-in presets available via `policy-add`:

| Preset | Endpoints |
|--------|-----------|
| `npm` | registry.npmjs.org |
| `pypi` | pypi.org, files.pythonhosted.org |
| `github` | api.github.com, github.com |
| `huggingface` | huggingface.co |
| `docker` | Docker registries |
| `telegram` | api.telegram.org |
| `discord` | discord.com |
| `slack` | slack.com |
| `brave` | api.search.brave.com |
| `jira` | atlassian.net |
| `outlook` | graph.microsoft.com |
| `brew` | brew.sh |

## Credential Store

NemoClaw manages credentials in-memory (never persisted to disk). Known keys:

```
NVIDIA_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY,
COMPATIBLE_API_KEY, BRAVE_API_KEY, GITHUB_TOKEN, HF_TOKEN,
TELEGRAM_BOT_TOKEN, DISCORD_BOT_TOKEN, SLACK_BOT_TOKEN, SLACK_APP_TOKEN
```

## Key Paths

| Path | Purpose |
|------|---------|
| `~/.nemoclaw/source/` | NemoClaw source installation |
| `~/.nemoclaw/credentials.json` | Legacy credentials (deprecated) |
| `/sandbox/.openclaw-data/` | Sandbox data directory |
| `/sandbox/.nemoclaw/` | NemoClaw state inside sandbox |

## See Also

- [[NemoClaw × Milimo Integration Map]]
- [[Milimo Claw Architecture]]
- [[Claw Audit — 2026-05-11]]
