# syntax=docker/dockerfile:1.7
# =============================================================================
#  st-langflow-aio
#  Langflow + ffmpeg + chromium + yt-dlp + node tools
#  + MiniMax als Global Model Provider (Registry-basiert)
#
# Build:  docker build --no-cache -t st-langflow-aio .
# Verify: docker exec -it <container> python3 /tmp/verify_inplace.py
# Smoke:  docker exec -it <container> python3 /tmp/smoke_test.py <key>
# =============================================================================

FROM langflowai/langflow:base-1.13.0.dev22

USER root

ENV DEBIAN_FRONTEND=noninteractive \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium \
    LANGFLOW_CONFIG_DIR=/app/langflow \
    LANGFLOW_DEV=false \
    LFX_DEV=false

# =============================================================================
# 1. System packages
# =============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        chromium \
        fonts-liberation \
        libasound2t64 \
        libatk-bridge2.0-0t64 \
        libatk1.0-0t64 \
        libcups2t64 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0t64 \
        libnspr4 \
        libnss3 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libxkbcommon0 \
        libxext6 \
        xdg-utils \
        ca-certificates \
        curl \
        gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
       | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
       > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y --auto-remove gnupg \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# 2. Python packages
# =============================================================================
RUN pip install --no-cache-dir --break-system-packages \
        yt-dlp \
        langchain-anthropic \
        requests

# =============================================================================
# 3. Node tools
# =============================================================================
WORKDIR /opt/tools
RUN npm init -y >/dev/null \
 && npm install --no-audit --no-fund puppeteer-core yt-dlp-wrap \
 && npm cache clean --force \
 && rm -rf /tmp/*

ENV PATH="/opt/tools/node_modules/.bin:${PATH}"

# =============================================================================
# 4. Standalone MiniMaxModelComponent (LCModelComponent)
#    Optional standalone component for users who want MiniMax in the
#    Custom Components sidebar. The Global Provider registration in step 5
#    is the primary mechanism — this is the "Custom Component" path.
# =============================================================================
RUN python3 -c "import site; d=site.getsitepackages()[0]; \
    import os; os.makedirs(f'{d}/lfx/components/minimax', exist_ok=True); \
    open(f'{d}/lfx/components/minimax/__init__.py','w').write('''from __future__ import annotations\nfrom typing import TYPE_CHECKING, Any\nfrom lfx.components._importing import import_mod\nif TYPE_CHECKING:\n    from lfx.components.minimax.minimax import MiniMaxModelComponent\n_dynamic_imports = {\"MiniMaxModelComponent\": \"minimax\"}\n__all__ = [\"MiniMaxModelComponent\"]\ndef __getattr__(attr_name: str) -> Any:\n    if attr_name not in _dynamic_imports:\n        raise AttributeError(attr_name)\n    try:\n        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)\n    except (ModuleNotFoundError, ImportError, AttributeError) as e:\n        raise AttributeError(str(e)) from e\n    globals()[attr_name] = result\n    return result\n'''); print('init.py OK')"

COPY inject/lfx_components/lfx/components/minimax/minimax.py /tmp/minimax_component.py
RUN SITE=$(python3 -c "import site; print(site.getsitepackages()[0])") && \
    cp /tmp/minimax_component.py "$SITE/lfx/components/minimax/minimax.py" && \
    rm /tmp/minimax_component.py && \
    echo "minimax.py installed"

# =============================================================================
# 5. MiniMax as Global Model Provider (provider_registry)
#    Single source of truth: ProviderDescriptor with metadata + catalog_loader.
#    Survives upstream langflow refactors; no file patching.
# =============================================================================
COPY inject/register_minimax.py /tmp/register_minimax.py
COPY inject/sitecustomize.py   /tmp/sitecustomize.py
COPY inject/verify_inplace.py  /tmp/verify_inplace.py
COPY inject/smoke_test.py      /tmp/smoke_test.py

RUN SITE=$(python3 -c "import site; print(site.getsitepackages()[0])") && \
    cp /tmp/register_minimax.py "$SITE/register_minimax.py" && \
    cp /tmp/sitecustomize.py   "$SITE/sitecustomize.py"   && \
    chmod +x /tmp/verify_inplace.py /tmp/smoke_test.py && \
    echo "=== AUTO-VERIFY ===" && \
    python3 /tmp/verify_inplace.py && \
    echo "=== AUTO-VERIFY END ===" && \
    rm /tmp/register_minimax.py /tmp/sitecustomize.py

WORKDIR /app/langflow

EXPOSE 7860

CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
