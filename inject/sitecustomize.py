"""Register MiniMax at Python startup.

This file is installed at ``<site-packages>/sitecustomize.py`` by the Dockerfile.
The Python interpreter imports ``sitecustomize`` automatically during
``site.initialize()`` at startup, before any user code (including langflow's
``lfx.base.models.provider_registry``) runs.
"""
import os

if os.environ.get("MINIMAX_DISABLE_AUTOREGISTER") == "1":
    # explicit kill-switch for debugging / image-lint
    pass
else:
    try:
        # Imported lazily — sitecustomize runs before site-packages is on sys.path
        # in some interpretations, so we add it explicitly.
        import sys

        from pathlib import Path

        site_dir = None
        for p in Path(sys.prefix).glob("lib/python*/site-packages"):
            if (p / "lfx" / "base" / "models" / "model_metadata.py").exists():
                site_dir = str(p)
                break
        if site_dir and site_dir not in sys.path:
            sys.path.insert(0, site_dir)

        from register_minimax import register

        register()
    except Exception as exc:  # noqa: BLE001 - autorun must never crash the interpreter
        import sys

        sys.stderr.write(f"[sitecustomize] MiniMax auto-register failed: {exc!r}\n")
