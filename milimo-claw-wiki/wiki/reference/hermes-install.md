# Hermes Install Reference

**Summary**: Verified end-to-end install and onboarding path for the MilimoClaw Hermes profile, including required environment variables, the supported `nemohermes onboard` command, and the confirmed dashboard/API endpoints. Use this as the companion to the OpenClaw installer docs.

**Sources**: `/Users/mck/Desktop/MilimoClaw/.env`, `/Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/Dockerfile`, `/Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/install-hermes.sh`, live verification of `nemohermes inference get --json` and `nemohermes milimo-hermes status`.

**Last updated**: 2026-06-30

> Note: After onboarding, the sandbox is already running. Use `nemohermes milimo-hermes connect` to start a chat session, not `nemoclaw start`.

**Tags**: #installation #hermes #operations #reference

---

## Prerequisites

- Docker running locally.
- Node.js 22 `nemohermes` CLI installed.
- `~/.nemohermes` credentials configured.
- `.env` file present in the project root with the correct Hermes defaults (`NEMOCLAW_MODEL=stepfun-ai/step-3.7-flash`, `CHAT_UI_URL=http://localhost:18790`, `NEMOCLAW_AUTH_MODE=api_key`, etc.).

**Important**: Do not keep stale `18790` tunnels or old `nemoclaw` installs on the same port. Destroy them (`nemohermes sandbox destroy ...` and `kill <PID>`) before creating a fresh install if you hit `[ERROR] Port 18790 is not available`.

---

## Install Path

Preferred fresh install uses the wrapper:

```bash
export NVIDIA_API_KEY=...
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export CHAT_UI_URL=http://localhost:18790
./milimo-hermes-sandbox/install-hermes.sh --non-interactive
```

The wrapper called `build_onboard_command()` which now passes both `--fresh` and `--recreate-sandbox` to `nemohermes onboard`. `--fresh` clears saved state; `--recreate-sandbox` destroys and recreates the sandbox container (required because `--fresh` alone reuses the existing container and its restored policy files). Post-onboarding, the script also applies the `nous-portal` policy preset from `milimo-blueprint/policies/presets/`.

When the wrapper fails to pass flags, fall back to the direct CLI:

```bash
nemohermes onboard \
  --name milimo-hermes \
  --from ./milimo-hermes-sandbox/Dockerfile \
  --fresh \
  --recreate-sandbox \
  --yes \
  --yes-i-accept-third-party-software \
  --control-ui-port 18790
```

After onboarding, apply the `nous-portal` policy preset for `hermes setup --portal` access:

```bash
nemohermes milimo-hermes policy-add --from-dir milimo-blueprint/policies/presets/ --yes
```

Source `.env` before running the fallback path; `nemohermes` reads the host environment, not `.env`, and will otherwise fall back to `minimaxai/minimax-m2.7`.

---

## Verified Outcome

- Dashboard: `http://localhost:18790/`
- OpenAI-compatible API: `http://localhost:8642/v1`
- Inference provider: `nvidia-nim`
- Model: `stepfun-ai/step-3.7-flash`
- Sandbox name: `milimo-hermes`
- Phase: `Ready`
- Policies: `restricted` + `nous-portal` (applied post-onboarding)
- Auth mode: `api_key` (standard NVIDIA inference), `nous_oauth` enables managed tool gateways (web search, browser automation, image generation, audio processing, managed code execution).

## Model / Inference

Change the model on a running Hermes sandbox (no rebuild needed):

```bash
nemohermes inference set --model stepfun-ai/step-3.7-flash --provider nvidia-nim --sandbox milimo-hermes
```

> `openshell inference set` is not available inside Hermes sandboxes. Always use `nemohermes inference set` from the host.

Check current inference config:

```bash
nemohermes inference get --json
```

## Recovery

```bash
nemohermes milimo-hermes recover
nemohermes milimo-hermes dashboard-url
nemohermes milimo-hermes status
```

## Related Pages

- OpenClaw install details: `wiki/scripts/installation-scripts.md`
- Hermes architecture: `wiki/architecture/hermes-profile.md`
