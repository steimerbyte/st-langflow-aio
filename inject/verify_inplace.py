#!/usr/bin/env python3
"""In-place verification of MiniMax provider integration.

This script is injected into the image and run during the Docker build's
AUTO-VERIFY step. It verifies whichever integration path was applied
(registry-based for langflow >= 1.11, 5-file patches for langflow <= 1.10).

Registry path checks:
1. MiniMax appears in MODEL_PROVIDER_METADATA
2. is_registered("MiniMax") returns True
3. All 8 MiniMax models present in the unified model catalog

Patch path checks:
1. minimax_constants.py exists with model rows
2. model_metadata.py contains a "MiniMax" entry
3. provider_queries.py imports MINIMAX_MODELS_DETAILED
4. model_input_constants.py exposes the MiniMax provider dict entry
5. instantiation.py has the MiniMax base_url branch in get_llm()
"""
import importlib
import sys
from pathlib import Path

print("=" * 60)
print("MiniMax Integration Verification")
print("=" * 60)

# Locate site-packages (handles lib/ and lib64/ venv layouts)
import site as _site

SITE = None
for p in _site.getsitepackages():
    pp = Path(p)
    if (pp / "lfx" / "base" / "models" / "model_metadata.py").exists():
        SITE = pp
        break

if SITE is None:
    print("ERROR: site-packages not found")
    print(f"sys.prefix = {sys.prefix}")
    print(f"sys.path = {sys.path}")
    print(f"site.getsitepackages() = {_site.getsitepackages()}")
    sys.exit(1)

print(f"site-packages: {SITE}\n")

errors: list[str] = []
MODELS = SITE / "lfx" / "base" / "models"
UM = MODELS / "unified_models"


def has_provider_registry() -> bool:
    try:
        import lfx.base.models.provider_registry  # noqa: F401

        return True
    except ImportError:
        return False


def safe(name):
    try:
        return importlib.import_module(name)
    except Exception as exc:  # noqa: BLE001
        print(f"    FAIL - cannot import {name}: {exc!r}")
        errors.append(f"import {name}")
        return None


# ---------------------------------------------------------------------------
# REGISTRY PATH
# ---------------------------------------------------------------------------

def check_registry() -> bool:
    provider_metadata = safe("lfx.base.models.model_metadata")
    registry = safe("lfx.base.models.provider_registry")
    provider_queries = safe("lfx.base.models.unified_models.provider_queries")

    if registry and registry.is_registered("MiniMax"):
        print("[registry] OK - MiniMax is_registered() returns True")
    else:
        errors.append("MiniMax not in provider_registry")
        print("[registry] FAIL - MiniMax is_registered() is False")

    if provider_metadata and "MiniMax" in provider_metadata.MODEL_PROVIDER_METADATA:
        mm = provider_metadata.MODEL_PROVIDER_METADATA["MiniMax"]
        print(
            f"[registry] OK - MiniMax in MODEL_PROVIDER_METADATA"
            f" (provider_id={mm.get('provider_id')!r}, model_class={mm.get('mapping',{}).get('model_class')!r})"
        )
    else:
        errors.append("MiniMax missing from MODEL_PROVIDER_METADATA")
        print("[registry] FAIL - MiniMax missing from MODEL_PROVIDER_METADATA")

    if provider_queries:
        try:
            providers = provider_queries.get_model_providers()
            if "MiniMax" in providers:
                print(f"[registry] OK - MiniMax in get_model_providers() ({len(providers)} providers total)")
            else:
                errors.append("MiniMax missing from get_model_providers()")
                print("[registry] FAIL - MiniMax not in get_model_providers()")

            catalog = provider_queries.get_models_detailed()
            names = {row.get("name") for grp in catalog for row in grp if row.get("provider") == "MiniMax"}
            expected = {
                "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
                "MiniMax-M2.5", "MiniMax-M2.5-highspeed",
                "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2",
            }
            missing = expected - names
            if not missing:
                print(f"[registry] OK - all 8 MiniMax models present in unified catalog ({len(names)} found)")
            else:
                errors.append(f"missing MiniMax models: {sorted(missing)}")
                print(f"[registry] FAIL - missing MiniMax models in catalog: {sorted(missing)}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"registry catalog probe: {exc!r}")
            print(f"[registry] FAIL - catalog probe failed: {exc!r}")

    return not errors


# ---------------------------------------------------------------------------
# PATCH PATH (langflow <= 1.10)
# ---------------------------------------------------------------------------

def check_patches() -> bool:
    print("\n[patch] checking 5-file patches in langflow core")

    # 1. minimax_constants.py
    f = MODELS / "minimax_constants.py"
    if f.exists() and "MINIMAX_MODELS_DETAILED" in f.read_text() and "MiniMax-M3" in f.read_text():
        print("    OK   minimax_constants.py exists with models")
    else:
        errors.append("minimax_constants.py missing or incomplete")
        print("    FAIL minimax_constants.py missing or incomplete")

    # 2. model_metadata.py
    f = MODELS / "model_metadata.py"
    if f.exists() and '"MiniMax":' in f.read_text():
        print("    OK   model_metadata.py has MODEL_PROVIDER_METADATA['MiniMax']")
    else:
        errors.append("model_metadata.py missing MiniMax entry")
        print("    FAIL model_metadata.py missing MiniMax entry")

    # 3. provider_queries.py
    f = UM / "provider_queries.py"
    if f.exists() and "minimax_constants" in f.read_text() and "MINIMAX_MODELS_DETAILED" in f.read_text():
        print("    OK   provider_queries.py imports MINIMAX_MODELS_DETAILED")
    else:
        errors.append("provider_queries.py missing minimax integration")
        print("    FAIL provider_queries.py missing minimax integration")

    # 4. model_input_constants.py
    f = MODELS / "model_input_constants.py"
    content = f.read_text() if f.exists() else ""
    ok = '"MiniMax"' in content and ("_get_minimax_inputs_and_fields" in content or "_get_MiniMax" in content.lower())
    if f.exists() and ok:
        print("    OK   model_input_constants.py exposes MiniMax provider")
    else:
        errors.append("model_input_constants.py missing MiniMax integration")
        print("    FAIL model_input_constants.py missing MiniMax integration")

    # 5. instantiation.py — MiniMax base_url branch in get_llm()
    f = UM / "instantiation.py"
    if f.exists() and 'provider == "MiniMax"' in f.read_text():
        print("    OK   instantiation.py has MiniMax base_url branch")
    else:
        errors.append("instantiation.py missing MiniMax branch")
        print("    FAIL instantiation.py missing MiniMax branch")

    # 6. Standalone LCModelComponent
    comp = SITE / "lfx" / "components" / "minimax" / "minimax.py"
    if comp.exists() and "MiniMaxModelComponent" in comp.read_text():
        print("    OK   MiniMaxModelComponent at lfx/components/minimax/")
    else:
        errors.append("MiniMaxModelComponent missing")
        print("    FAIL MiniMaxModelComponent missing")

    return not errors


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if has_provider_registry():
    print("Path: registry-based (langflow >= 1.11)\n")
    check_registry()
else:
    print("Path: 5-file patch (langflow <= 1.10)\n")
    check_patches()

print()
print("=" * 60)
if errors:
    print(f"RESULT: FAILED ({len(errors)} error{'s' if len(errors) != 1 else ''})")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("RESULT: ALL CHECKS PASSED")
    sys.exit(0)
