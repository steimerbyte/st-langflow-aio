# syntax=docker/dockerfile:1.7
# =============================================================================
#  st-langflow-aio
#  Langflow + MiniMax als Global Model Provider
#  Fedora 46 OS + Python 3.14 venv via uv
#
#  Build:  docker build --no-cache -t st-langflow-aio .
#  Verify: docker exec -it <container> /app/.venv/bin/python /tmp/verify_inplace.py
#  Smoke:  docker exec -it <container> /app/.venv/bin/python /tmp/smoke_test.py <key>
# =============================================================================

FROM fedora:46

ENV LANGFLOW_CONFIG_DIR=/app/langflow \
    LANGFLOW_DEV=false \
    LFX_DEV=false \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# =============================================================================
# 1. System packages (Fedora 46 native: dnf, ffmpeg + chromium in main repos)
# =============================================================================
RUN dnf install -y --setopt=install_weak_deps=0 \
        python3.14 \
        python3.14-devel \
        uv \
        gcc \
        gcc-c++ \
        make \
        libxml2-devel \
        libxslt-devel \
        nodejs \
        npm \
        ffmpeg \
        chromium \
        chromium-headless \
        liberation-fonts \
        liberation-sans-fonts \
        liberation-mono-fonts \
        liberation-serif-fonts \
        nss \
        alsa-lib \
        at-spi2-atk \
        libdrm \
        libgbm \
        libXcomposite \
        libXdamage \
        libXext \
        libXfixes \
        libXrandr \
        libxkbcommon \
        mesa-libgbm \
        glib2 \
        gtk3 \
        git \
        ca-certificates \
        tar \
        gzip \
        findutils \
        which \
    && dnf clean all \
    && rm -rf /var/cache/dnf \
    && ln -sf /usr/bin/chromium-browser /usr/local/bin/chromium

# =============================================================================
# 2. Python venv (Python 3.14, uv-managed) + langflow + deps
#    Fedora 46's default python3 is 3.15, too new for langflow's wheels.
#    We install python3.14 + uv and create an isolated venv.
# =============================================================================
RUN uv venv --python 3.14 /app/.venv --seed \
    && uv pip install --python /app/.venv/bin/python \
        'setuptools<81' \
        wheel \
        'langflow==1.10.3' \
        langchain-anthropic \
        'psycopg[binary]' \
        psycopg2-binary \
        yt-dlp \
        requests

ENV PATH="/app/.venv/bin:${PATH}"

# =============================================================================
# 3. Standalone MiniMaxModelComponent (LCModelComponent)
#    Optional — the registry-based registration in step 4 is the primary
#    mechanism. Keeps flows that reference MiniMaxModelComponent by class
#    working.
# =============================================================================
COPY inject/lfx_components/lfx/components/minimax/minimax.py /tmp/minimax_component.py
RUN SITE=$(/app/.venv/bin/python -c 'import site; print(site.getsitepackages()[0])') && \
    mkdir -p "$SITE/lfx/components/minimax" && \
    printf 'from __future__ import annotations\nfrom typing import TYPE_CHECKING, Any\nfrom lfx.components._importing import import_mod\nif TYPE_CHECKING:\n    from lfx.components.minimax.minimax import MiniMaxModelComponent\n_dynamic_imports = {"MiniMaxModelComponent": "minimax"}\n__all__ = ["MiniMaxModelComponent"]\ndef __getattr__(attr_name: str) -> Any:\n    if attr_name not in _dynamic_imports:\n        raise AttributeError(attr_name)\n    try:\n        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)\n    except (ModuleNotFoundError, ImportError, AttributeError) as e:\n        raise AttributeError(str(e)) from e\n    globals()[attr_name] = result\n    return result\n' > "$SITE/lfx/components/minimax/__init__.py" && \
    cp /tmp/minimax_component.py "$SITE/lfx/components/minimax/minimax.py" && \
    rm /tmp/minimax_component.py && \
    echo "minimax.py installed"

# =============================================================================
# 4. MiniMax as Global Model Provider (provider_registry)
# =============================================================================
COPY inject/register_minimax.py /tmp/register_minimax.py
COPY inject/sitecustomize.py   /tmp/sitecustomize.py
COPY inject/verify_inplace.py  /tmp/verify_inplace.py
COPY inject/smoke_test.py      /tmp/smoke_test.py

# Install sitecustomize.py + register_minimax.py into EVERY site-packages dir
# =============================================================================
# 4. MiniMax as Global Model Provider (registry OR patch path)
#    minimax_setup.py dispatches based on the langflow version installed.
#    registry_minimax.py + sitecustomize.py cover the registry path;
#    patch_full_provider.py covers the 5-file patch path (langflow <= 1.10).
# =============================================================================
COPY inject/register_minimax.py       /tmp/register_minimax.py
COPY inject/sitecustomize.py         /tmp/sitecustomize.py
COPY inject/minimax_setup.py         /tmp/minimax_setup.py
COPY inject/patch_full_provider.py   /tmp/patch_full_provider.py
COPY inject/verify_inplace.py        /tmp/verify_inplace.py
COPY inject/smoke_test.py            /tmp/smoke_test.py

RUN SITES=$(/app/.venv/bin/python -c 'import site; import sys; [print(p) for p in site.getsitepackages()]') && \
    for SITE in $SITES; do \
        cp /tmp/register_minimax.py "$SITE/register_minimax.py" && \
        cp /tmp/sitecustomize.py   "$SITE/sitecustomize.py"   && \
        echo "installed in $SITE"; \
    done && \
    chmod +x /tmp/verify_inplace.py /tmp/smoke_test.py /tmp/minimax_setup.py && \
    echo "=== MINIMAX SETUP ===" && \
    /app/.venv/bin/python /tmp/minimax_setup.py && \
    echo "=== AUTO-VERIFY ===" && \
    /app/.venv/bin/python /tmp/verify_inplace.py && \
    echo "=== AUTO-VERIFY END ===" && \
    rm /tmp/register_minimax.py /tmp/sitecustomize.py /tmp/minimax_setup.py /tmp/patch_full_provider.py

WORKDIR /app/langflow

EXPOSE 7860

CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
