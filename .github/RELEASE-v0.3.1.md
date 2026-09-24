# Release v0.3.1

Build-system compatibility fix for langflowai/langflow 1.13+ on RHEL 10.2.

## What changed since v0.3.0

The `langflowai/langflow` Docker image switched from Debian to **RHEL UBI 10.2**
starting in 1.13.0.dev10. v0.3.0's `Dockerfile` was written for Debian —
`apt-get` no longer exists in the base image, so the system-packages layer
failed and the image could not be built.

v0.3.1 replaces the Debian layer with `microdnf` and replaces the apt-key
Node install with a tarball install:

- `apt-get` → `microdnf` (ca-certificates, tar only — the rest is already
  bundled in the base image or only available via RPM Fusion / EPEL)
- `nodejs` via NodeSource apt repo → direct tarball from nodejs.org
- Dropped in this release: `ffmpeg`, `chromium`, `libgtk-*` (only available
  via RPM Fusion / EPEL in RHEL; will return when those packages are added
  by upstream or when a follow-up release wires them in)

The core scope — **Langflow + MiniMax as Global Model Provider** — is
preserved. The Auto-Verify step inside `Dockerfile` step 5 runs
`verify_inplace.py` as part of the build, so a broken registration fails
the build loudly.

## Verified Working

Same as v0.3.0 (registry state, all 8 models, Settings → Model Providers).

## Migration from v0.3.0

Same as v0.3.0. No data migration.

```bash
git pull
docker compose down -v
docker compose build --no-cache
docker compose up -d
docker exec -it $(docker ps -qf name=langflow) python3 /tmp/verify_inplace.py
```
