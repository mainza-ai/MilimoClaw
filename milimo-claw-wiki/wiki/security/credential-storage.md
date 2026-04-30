# Credential Storage

> **NemoClaw Compliance Notice**: This page documents security controls as implemented by NVIDIA NemoClaw and OpenShell. MilimoClaw operates within the NemoClaw sandbox and inherits all controls described here. Any discrepancy between this page and the [official NemoClaw documentation](https://docs.nvidia.com/nemoclaw/latest/security/credential-storage.html) should be reported and resolved in favor of the official docs.

## Core Principle

NemoClaw does **not** persist provider credentials to host disk. The OpenShell gateway is the **only** system of record for stored credentials.

When you provide a credential -- whether during `nemoclaw onboard` or via an environment variable -- NemoClaw holds the value in process memory only long enough to register it with the OpenShell gateway via `openshell provider create` or `openshell provider update`. Once registered:

- The gateway stores the credential
- The OpenShell L7 proxy substitutes it into outbound requests at egress
- Sandboxed agents see placeholders, never the actual credential values

### Token Rotation Is Separate

`nemoclaw config rotate-token` rotates the **sandbox-side OpenClaw auth token**. It does **not** rotate provider credentials. Provider credential rotation requires re-onboarding with the new value.

---

## Where Credentials Live

### Listing Registered Providers

```bash
openshell provider list
nemoclaw credentials list
```

Both commands display registered provider names and metadata. Credential **values** cannot be read back from the CLI. This is a deliberate OpenShell security property: once stored, values are only accessible to the gateway's L7 proxy at egress time.

### The `~/.nemoclaw/` Directory

The `~/.nemoclaw/` directory exists (mode `0700`) but contains only non-secret operational state, such as `sandboxes.json`. Provider credentials are **never** written to this directory.

---

## Environment Variables Take Precedence

Environment variables are read first, before any stored credentials. This enables short-lived and rotated credentials in CI pipelines.

```bash
NVIDIA_API_KEY=nvapi-... nemoclaw onboard
```

You can prefix any command with credential environment variables. The value is held in process memory for the duration of the onboard operation and then registered with the gateway. It is not written to disk.

---

## Deploy Reads from Environment Only

`nemoclaw deploy` **cannot** read secrets back from the gateway. Every required credential must be present in the host environment at invocation time. If a credential is missing from the environment, deploy will fail with a clear error indicating which provider credential is required.

This design ensures that deployment is fully declarative and reproducible: the environment defines the credentials, and the gateway never acts as a credential source for new deployments.

---

## GitHub Tokens

NemoClaw never persists `GITHUB_TOKEN` itself. When a GitHub token is needed:

1. NemoClaw runs `gh auth token`, which returns whatever the GitHub CLI has stored
2. The `gh` CLI prefers the OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
3. If no keychain is reachable, `gh` falls back to `~/.config/gh/` with mode `0600`
4. If `gh` is not installed or not logged in, NemoClaw prompts for a Personal Access Token (PAT), which is held in process memory only for the duration of the onboard

---

## Migration From Earlier Releases

Earlier NemoClaw releases used `~/.nemoclaw/credentials.json` -- a plaintext JSON file with mode `0600`.

On the first `nemoclaw onboard` after upgrading, NemoClaw:

1. Auto-reads the legacy `credentials.json` file
2. Stages each credential
3. Re-registers all credentials with the OpenShell gateway
4. Securely overwrites the file contents
5. Deletes the file

If the file remains after a rebuild (e.g., due to a failed migration), run `nemoclaw onboard` to complete the migration.

---

## Rotate or Remove Credentials

### Rotate

Rerun onboard with the new value:

```bash
NVIDIA_API_KEY=nvapi-new-value nemoclaw onboard
```

The gateway updates the stored credential. The old value is immediately invalidated.

### Remove

```bash
nemoclaw credentials reset <PROVIDER_NAME>
```

This removes the credential from the gateway. Any subsequent inference requests to that provider will fail until a new credential is registered.

---

## Security Recommendations

1. **Use environment variables in CI**: Pass credentials via environment variables rather than relying on stored values. This ensures short-lived, rotation-friendly credentials and full declarative control.

2. **Never commit credentials to source control**: NemoClaw will not write credentials to disk on your behalf, but you must also ensure that CI secrets, `.env` files, and PATs are excluded from version control.

3. **Rotate credentials regularly**: Use `nemoclaw credentials reset` to remove stale credentials and re-onboard with fresh values. Follow your provider's recommended rotation schedule.

4. **Verify with `nemoclaw credentials list`**: Periodically audit which providers are registered. Remove any that are no longer needed.

5. **Use OS keychain for GitHub tokens**: Ensure `gh` is configured to use the OS keychain rather than the plaintext fallback at `~/.config/gh/`. On macOS, this is the default. On Linux, install `libsecret` and verify with `gh auth status`.
