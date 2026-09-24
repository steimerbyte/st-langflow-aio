# syntax=docker/dockerfile:1.7
# =============================================================================
#  st-langflow-aio
#  Langflow + MiniMax als Global Model Provider
#
#  Build:  docker build --no-cache -t st-langflow-aio .
#  Verify: docker exec -it <container> python3 /tmp/verify_inplace.py
#  Smoke:  docker exec -it <container> python3 /tmp/smoke_test.py <key>
#
#  NOTE: langflowai/langflow switched to RHEL 10.2 (microdnf, no apt-get) since
#  1.13.0.dev10. The previous Debian-era system-package list
#  (ffmpeg/chromium/libgtk-3-* etc) is no longer installable from the base
#  image's default repos. Media-stack capabilities (yt-dlp + chromium for
#  puppeteer + Node tool wrappers) are dropped from v0.3.0 until upstream
#  repos or UBI extras catch up. Core scope (Langflow + MiniMax as Global
#  Model Provider) is preserved.
# =============================================================================

FROM langflowai/langflow:base-1.13.0.dev22

USER root

ENV LANGFLOW_CONFIG_DIR=/app/langflow \
    LANGFLOW_DEV=false \
    LFX_DEV=false

# =============================================================================
# 1. System packages (RHEL-flavored: microdnf only)
#    The langflow base image (RHEL 10.2 UBI) ships with: python3.14, curl,
#    ca-certificates, tar, git, basic GNU coreutils. It does NOT include
#    ffmpeg, chromium, or puppeteer system libs (langflow's puppeteer-based
#    components will be unavailable until upstream provides an alternative).
#    drop ffmpeg/chromium from v0.3.0 install; if you need them, wire
#    in RPM Fusion / EPEL inside your fork.
# =============================================================================
RUN microdnf install -y --setopt=install_weak_deps=0 \
        ca-certificates \
        tar \
    && microdnf clean all \
    && rm -rf /var/cache/dnf /var/cache/yum

# =============================================================================
# 2. Python packages
# =============================================================================
RUN pip install --no-cache-dir --break-system-packages \
        yt-dlp \
        langchain-anthropic \
        requests

# =============================================================================
# 3. Node.js 20 (tarball install — no apt key in RHEL base)
#    Drops the puppeteer-core / yt-dlp-wrap wrappers for now; langflow
#    itself can use its own bundled JS runtime for components.
# =============================================================================
RUN set -eux; \
    curl -fsSL https://nodejs.org/dist/v20.19.5/node-v20.19.5-linux-x64.tar.xz \
        -o /tmp/node.tar.xz && \
    mkdir -p /opt/node20 && \
    tar -xJf /tmp/node.tar.xz -C /opt/node20 --strip-components=1 && \
    rm /tmp/node.tar.xz && \
    ln -sf /opt/node20/bin/node /usr/local/bin/node && \
    ln -sf /opt/node20/bin/npm  /usr/local/bin/npm  && \
    ln -sf /opt/node20/bin/npx  /usr/local/bin/npx  && \
    node --version && npm --version

# =============================================================================
# 4. Standalone MiniMaxModelComponent (LCModelComponent)
#    Optional — the registry-based registration in step 5 is the primary
#    mechanism. This keeps flows that reference MiniMaxModelComponent by class
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
