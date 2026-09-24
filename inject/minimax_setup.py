#!/usr/bin/env python3
"""MiniMax Setup-Dispatcher.

Picks the right integration path based on the installed langflow version:

- langflow >= 1.11  -> provider_registry.register_provider() (preferred,
  upgrade-tolerant). Implemented in inject/register_minimax.py.
- langflow <= 1.10  -> 5-file string-replace patches against
  model_metadata.py, provider_queries.py, model_input_constants.py and
  instantiation.py. Implemented in inject/patch_full_provider.py.

Either way, the same `MiniMaxModelComponent` is also installed into
`lfx/components/minimax/` so flows that reference it by class keep working.

Designed to be safe to call repeatedly: each branch is idempotent.
"""
import sys
from pathlib import Path

# Locate site-packages (handles lib/ and lib64/ venv layouts)
import site as _site

SITE = None
for p in _site.getsitepackages():
    pp = Path(p)
    if (pp / "lfx" / "base" / "models" / "model_metadata.py").exists():
        SITE = pp
        break

if SITE is None:
    print("[minimax-setup] ERROR: site-packages not found")
    sys.exit(1)


def has_provider_registry() -> bool:
    """True if installed langflow exposes the provider_registry extension API."""
    try:
        import lfx.base.models.provider_registry  # noqa: F401

        return True
    except ImportError:
        return False


def install_lcmodelcomponent() -> None:
    """Drop MiniMaxModelComponent into <site-packages>/lfx/components/minimax/.

    Source lives in inject/lfx_components/lfx/components/minimax/minimax.py
    in the repo; the Dockerfile copies it to /tmp before calling this.
    """
    src = Path("/tmp/minimax_component.py")
    if not src.exists():
        print("[minimax-setup] no /tmp/minimax_component.py — skipping LCModelComponent")
        return

    target_dir = SITE / "lfx" / "components" / "minimax"
    target_dir.mkdir(parents=True, exist_ok=True)

    init_file = target_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            "from __future__ import annotations\n"
            "from typing import TYPE_CHECKING, Any\n"
            "from lfx.components._importing import import_mod\n"
            "if TYPE_CHECKING:\n"
            "    from lfx.components.minimax.minimax import MiniMaxModelComponent\n"
            "_dynamic_imports = {\"MiniMaxModelComponent\": \"minimax\"}\n"
            "__all__ = [\"MiniMaxModelComponent\"]\n"
            "def __getattr__(attr_name: str) -> Any:\n"
            "    if attr_name not in _dynamic_imports:\n"
            "        raise AttributeError(attr_name)\n"
            "    try:\n"
            "        result = import_mod(attr_name, _dynamic_imports[attr_name], __spec__.parent)\n"
            "    except (ModuleNotFoundError, ImportError, AttributeError) as e:\n"
            "        raise AttributeError(str(e)) from e\n"
            "    globals()[attr_name] = result\n"
            "    return result\n"
        )
        print(f"[minimax-setup] wrote {init_file}")

    target = target_dir / "minimax.py"
    target.write_text(src.read_text())
    print(f"[minimax-setup] wrote {target}")


def run_registry_path() -> bool:
    """Returns True on success."""
    try:
        # register_minimax.py installs itself next to the venv's site-packages
        sys.path.insert(0, str(SITE))
        from register_minimax import register  # noqa: F401

        ok = register()
        print(f"[minimax-setup] provider_registry path: register()={ok}")
        return True
    except Exception as exc:  # noqa: BLE001 - dispatcher must not crash the build
        print(f"[minimax-setup] provider_registry path failed: {exc!r}")
        return False


def run_patch_path() -> bool:
    """Returns True on success."""
    try:
        # patch_full_provider.py runs as a script — it uses sys.argv-less
        # top-level code, so just exec it.
        import runpy

        runpy.run_path(
            "/tmp/patch_full_provider.py",
            run_name="__main__",
        )
        print("[minimax-setup] patch path completed")
        return True
    except SystemExit as exc:
        ok = exc.code in (None, 0)
        print(f"[minimax-setup] patch path exit={exc.code}")
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[minimax-setup] patch path failed: {exc!r}")
        return False


def main() -> int:
    print(f"[minimax-setup] site-packages: {SITE}")

    # 1. Always install the standalone LCModelComponent (optional)
    install_lcmodelcomponent()

    # 2. Pick the integration path
    if has_provider_registry():
        print("[minimax-setup] detected provider_registry API -> using register_minimax")
        ok = run_registry_path()
    else:
        print("[minimax-setup] provider_registry not available -> using patch_full_provider")
        ok = run_patch_path()

    if not ok:
        print("[minimax-setup] FAILED")
        return 1

    print("[minimax-setup] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
