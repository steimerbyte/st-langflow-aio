# Release v0.3.0

MiniMax integration moved to the official `provider_registry.register_provider()` API.

## What changed

- **Architecture shift**: file patching of `lfx/base/models/*.py` replaced by
  a single `ProviderDescriptor` registration in
  `lfx/base.models.provider_registry.register_provider()`. Eliminates brittle
  string-replace patches that break whenever upstream langflow refactors.
- **Auto-registration at startup**: `sitecustomize.py` invokes
  `register_minimax.register()` on every Python interpreter boot — no
  explicit ordering with langflow startup required.
- **New verification surface**: `verify_inplace.py` now checks the live
  registry state (`is_registered("MiniMax")`, `MODEL_PROVIDER_METADATA["MiniMax"]`,
  `get_model_providers()`, `get_models_detailed()` for all 8 models) instead of
  file content.

## Verified Working

- MiniMax as Global Model Provider in Settings → Model Providers
- MiniMax selectable in Agent Model Provider Dropdown
- All 8 MiniMax models (M3, M2.7, M2.5, M2.1, M2) including highspeed variants
- Tool Calling, Vision, Video, Thinking support via Anthropic-compatible endpoint
- Compatible with `langflowai/langflow:latest` (1.13+)

## Pre-installed

- Langflow latest (currently 1.13.0.dev22)
- ffmpeg, Chromium (puppeteer)
- Node.js 20, yt-dlp, langchain-anthropic

## Migration from v0.2.x

No data migration required. Existing flows and the global variable for the
MiniMax API key continue to work.

```bash
git pull
docker compose down -v
docker compose build --no-cache
docker compose up -d
docker exec -it $(docker ps -qf name=langflow) python3 /tmp/verify_inplace.py
```
