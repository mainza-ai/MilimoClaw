# Hermes Install Reference

**Summary**: Verified end-to-end install and onboarding path for the MilimoClaw Hermes profile, including required environment variables, the supported `nemohermes onboard` command, and the confirmed dashboard/API endpoints. Use this as the companion to the OpenClaw installer docs.

**Sources**: `/Users/mck/Desktop/MilimoClaw/.env`, `/Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/Dockerfile`, `/Users/mck/Desktop/MilimoClaw/milimo-hermes-sandbox/install-hermes.sh`, live verification of `nemohermes inference get --json` and `nemohermes milimo-hermes status`.

**Last updated**: 2026-06-30

**Tags**: #installation #hermes #operations #reference

---

## Prerequisites

- Docker running locally.
- Node.js 22 `nemohermes` CLI installed.
- `~/.nemohermes` credentials configured.
- `.env` file present in the project root with the correct Hermes defaults (`NEMOCLAW_MODEL=nvidia/nemotron-3-super-120b-a12b`, `CHAT_UI_URL=http://localhost:18790`, `NEMOCLAW_AUTH_MODE=api_key`, etc.).

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

When the wrapper fails to pass flags, fall back to the direct CLI:

```bash
nemohermes onboard \
  --name milimo-hermes \
  --from ./milimo-hermes-sandbox/Dockerfile \
  --fresh \
  --yes \
  --yes-i-accept-third-party-software \
  --control-ui-port 18790
```

Source `.env` before running the fallback path; `nemohermes` reads the host environment, not `.env`, and will otherwise fall back to `minimaxai/minimax-m2.7`.

---

## Verified Outcome

- Dashboard: `http://localhost:18790/`
- OpenAI-compatible API: `http://localhost:8642/v1`
- Inference provider: `nvidia-prod`
- Model: `nvidia/nemotron-3-super-120b-a12b`
- Sandbox name: `milimo-hermes`
- Phase: `Ready`
- Policies: `restricted`
- Auth mode: `api_key` (standard NVIDIA inference), `nous_oauth` enables managed tool gateways (web search, browser automation, image generation, audio processing, managed code execution).

## Recovery

```bash
nemohermes milimo-hermes recover
nemohermes milimo-hermes dashboard-url
nemohermes milimo-hermes status
```

## Related Pages

- OpenClaw install details: `wiki/scripts/installation-scripts.md`
- Hermes architecture: `wiki/architecture/hermes-profile.md`
