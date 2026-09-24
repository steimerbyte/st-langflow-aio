# syntax=docker/dockerfile:1.7
# =============================================================================
#  st-langflow-aio
#  Langflow + MiniMax als Global Model Provider — Fedora 46 base
#
#  Architekturwechsel v0.4.0:
#    - Downstream langflowai/langflow-Image weggeworfen (RHEL UBI 10.2,
#      keine ffmpeg/chromium ohne Entitlements)
#    - Stattdessen: Fedora 46 (dnf) + pip-install langflow from PyPI
#    - ffmpeg und chromium direkt aus Fedora-Repos (kein RPM Fusion nötig)
#
#  Build:  docker build --no-cache -t st-langflow-aio .
#  Verify: docker exec -it <container> python3 /tmp/verify_inplace.py
#  Smoke:  docker exec -it <container> python3 /tmp/smoke_test.py <key>
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
        python3 \
        python3-devel \
        python3-pip \
        libxml2-devel \
        libxslt-devel \
        gcc \
        gcc-c++ \
        make \
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
# 2. Python packages (langflow + ecosystem + MiniMax deps)
#    Fedora 46 ships Python 3.15 with newer setuptools that drops
#    pkg_resources by default. We pin setuptools<81 which still ships it,
#    so pandas/lxml source builds don't crash.
# =============================================================================
RUN pip install --upgrade --break-system-packages 'pip<25' 'setuptools<81' wheel \
    && pip install --break-system-packages --no-build-isolation \
        langflow \
        langchain-anthropic \
        psycopg2-binary \
        yt-dlp \
        requests

# =============================================================================
# 3. Standalone MiniMaxModelComponent (LCModelComponent)
#    Optional — the registry-based registration in step 4 is the primary
#    mechanism. Keeps flows that reference MiniMaxModelComponent by class
#    working.
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
# 4. MiniMax as Global Model Provider (provider_registry)
#    Single source of truth: ProviderDescriptor with metadata + catalog_loader.
#    Survives upstream langflow refactors; no file patching.
# =============================================================================
COPY inject/register_minimax.py /tmp/register_minimax.py
COPY inject/sitecustomize.py   /tmp/sitecustomize.py
COPY inject/verify_inplace.py  /tmp/verify_inplace.py
COPY inject/smoke_test.py      /tmp/smoke_test.py

# Install into every site-packages directory Python reports — handles
# both `lib/` and `lib64/` venv layouts and any future symlink scheme.
RUN SITES=$(python3 -c 'import site; import sys; [print(p) for p in site.getsitepackages()]') && \
    for SITE in $SITES; do \
        cp /tmp/register_minimax.py "$SITE/register_minimax.py" && \
        cp /tmp/sitecustomize.py   "$SITE/sitecustomize.py"   && \
        echo "installed in $SITE"; \
    done && \
    chmod +x /tmp/verify_inplace.py /tmp/smoke_test.py && \
    echo "=== AUTO-VERIFY ===" && \
    python3 /tmp/verify_inplace.py && \
    echo "=== AUTO-VERIFY END ===" && \
    rm /tmp/register_minimax.py /tmp/sitecustomize.py

WORKDIR /app/langflow

EXPOSE 7860

CMD ["langflow", "run", "--host", "0.0.0.0", "--port", "7860"]
