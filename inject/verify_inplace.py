#!/usr/bin/env python3
"""In-place verification of MiniMax provider registration.

This script is injected into the image and run during the Docker build's
AUTO-PATCH step. It verifies the registry-based MiniMax integration rather
than patching source files (which would be brittle across upstream versions).

Checks performed:
1. sitecustomize.py installed at <site-packages>/sitecustomize.py
2. register_minimax.py importable
3. Calling register() succeeds without raising
4. MiniMax appears in MODEL_PROVIDER_METADATA
5. MiniMax registered with provider_registry
6. All 8 MiniMax models present in the unified model catalog
7. MiniMax selectable in get_model_providers()
"""
import importlib
import sys
from pathlib import Path

print("=" * 60)
print("MiniMax Registry Verification")
print("=" * 60)

# Locate site-packages
import site as _site

SITE = None
# 1. Trust Python's own resolution (handles both `lib/` and `lib64/` venv layouts)
for p in _site.getsitepackages():
    pp = Path(p)
    if (pp / "lfx" / "base" / "models" / "model_metadata.py").exists():
        SITE = pp
        break

# 2. Fallback: scan sys.prefix for any lib*/python*/site-packages containing lfx
if SITE is None:
    for pattern in ("lib/python*/site-packages", "lib64/python*/site-packages"):
        for p in Path(sys.prefix).glob(pattern):
            if (p / "lfx" / "base" / "models" / "model_metadata.py").exists():
                SITE = p
                break
        if SITE is not None:
            break

if SITE is None:
    print("ERROR: site-packages not found")
    print(f"sys.prefix = {sys.prefix}")
    print(f"sys.path = {sys.path}")
    print(f"site.getsitepackages() = {_site.getsitepackages()}")
    sys.exit(1)

print(f"site-packages: {SITE}\n")

SITE_STR = str(SITE)
if SITE_STR not in sys.path:
    sys.path.insert(0, SITE_STR)

errors: list[str] = []

# Check 1: sitecustomize.py
print("[1] sitecustomize.py installed")
sc = SITE / "sitecustomize.py"
if sc.exists():
    content = sc.read_text()
    if "register_minimax" in content and "register()" in content:
        print("    OK - references register_minimax + register()")
    else:
        msg = "sitecustomize.py exists but does not call register_minimax.register()"
        print(f"    FAIL - {msg}")
        errors.append(msg)
else:
    msg = "sitecustomize.py is missing"
    print(f"    FAIL - {msg}")
    errors.append(msg)

# Check 2: register_minimax.py importable
print("\n[2] register_minimax.py importable")
try:
    rm = importlib.import_module("register_minimax")
    print("    OK - module loaded")
except Exception as e:
    msg = f"register_minimax import failed: {e!r}"
    print(f"    FAIL - {msg}")
    errors.append(msg)
    sys.exit(1)


# Check 3: register() runs cleanly
print("\n[3] register() callable + idempotent")
try:
    ok_first = rm.register()
    print(f"    first call returned: {ok_first}")
    ok_second = rm.register()
    print(f"    second call returned: {ok_second} (False = already registered, OK)")
except Exception as e:
    msg = f"register() raised: {e!r}"
    print(f"    FAIL - {msg}")
    errors.append(msg)


# Check 4-7: provider catalog state
print("\n[4-7] Catalog state after registration")


def safe(name):
    try:
        mod = importlib.import_module(name)
    except Exception as e:
        print(f"    FAIL - cannot import {name}: {e!r}")
        errors.append(f"import {name}")
        return None
    return mod


# Check 4: MiniMax in MODEL_PROVIDER_METADATA
provider_metadata = safe("lfx.base.models.model_metadata")
if provider_metadata is not None:
    metadata = provider_metadata.MODEL_PROVIDER_METADATA
    if "MiniMax" in metadata:
        mm = metadata["MiniMax"]
        mapping = mm.get("mapping", {})
        provider_id = mm.get("provider_id", "")
        print(f"    [4] OK - MiniMax in MODEL_PROVIDER_METADATA (provider_id={provider_id!r}, model_class={mapping.get('model_class')!r})")
        if provider_id != "minimax":
            msg = f"MiniMax provider_id is {provider_id!r}, expected 'minimax'"
            print(f"    FAIL - {msg}")
            errors.append(msg)
    else:
        msg = "MiniMax missing from MODEL_PROVIDER_METADATA"
        print(f"    FAIL - {msg}")
        errors.append(msg)


# Check 5: registry state
registry = safe("lfx.base.models.provider_registry")
if registry is not None:
    if registry.is_registered("MiniMax"):
        print("    [5] OK - MiniMax is_registered() returns True")
    else:
        msg = "MiniMax is_registered() returned False"
        print(f"    FAIL - {msg}")
        errors.append(msg)


# Check 6+7: get_model_providers() includes MiniMax; catalog has all 8 models
provider_queries = safe("lfx.base.models.unified_models.provider_queries")
if provider_queries is not None:
    try:
        providers = provider_queries.get_model_providers()
        print(f"    [7] providers returned by get_model_providers(): {len(providers)} items")
        if "MiniMax" in providers:
            print("         OK - MiniMax in provider list")
        else:
            msg = "MiniMax missing from get_model_providers()"
            print(f"         FAIL - {msg}")
            errors.append(msg)
    except Exception as e:
        msg = f"get_model_providers() failed: {e!r}"
        print(f"         FAIL - {msg}")
        errors.append(msg)


# Check 6: all 8 MiniMax models in unified catalog (via get_models_detailed)
if provider_queries is not None:
    try:
        all_models = provider_queries.get_models_detailed()
        catalog_names: set[str] = set()
        for group in all_models:
            for row in group:
                if row.get("provider") == "MiniMax":
                    catalog_names.add(row.get("name", ""))
        expected = {
            "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
            "MiniMax-M2.5", "MiniMax-M2.5-highspeed",
            "MiniMax-M2.1", "MiniMax-M2.1-highspeed", "MiniMax-M2",
        }
        missing = expected - catalog_names
        if not missing:
            print(f"    [6] OK - all 8 MiniMax models present in catalog ({len(catalog_names)} found)")
        else:
            msg = f"missing MiniMax models in catalog: {sorted(missing)}"
            print(f"         FAIL - {msg}")
            errors.append(msg)
    except Exception as e:
        msg = f"get_models_detailed() failed: {e!r}"
        print(f"         FAIL - {msg}")
        errors.append(msg)


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
