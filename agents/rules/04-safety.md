# Rule 04: Security, Secrets Hygiene, and Degraded State Refusal

## Secrets Hygiene
- Never place personal access tokens (PATs), private keys, or API credentials in source files, git commits, terminal logs, or agent conversation context.
- Load secrets strictly via environment variables (`GITHUB_PAT`, `TRACEAI_PRIVATE_KEY_PATH`, etc.).
- The `tests/fixtures/` directory must never contain production private keys.

## Workspace Containment
- Agents are restricted to write operations strictly within the repository tree root (`${TRACEAI_REPO_ROOT}`).
- Do not attempt filesystem operations outside the designated project boundaries.

## Degraded Infrastructure Refusal
- TraceAI must never silently mark an asset as `PASSED` when any dependent infrastructure is offline, unreachable, or degraded.
- If the copyright index, Redis cache, or cross-encoder service is unavailable:
  - The asset must be moved to the retry queue or marked degraded.
  - An asset must never acquire a clean clearance certificate without completing full inspection.
