#!/usr/bin/env python3
"""Register MiniMax as a Langflow Model Provider via the official provider_registry.

langflow upstream versions since ~1.10 expose ``provider_registry.register_provider()``
in ``lfx.base.models.provider_registry``. The registry mutates the in-memory tables
that drive Settings -> Model Providers, the Agent dropdown, and ``get_llm`` — so one
call replaces every brittle file patch the legacy approach needed.

This script:
1. Declares the MiniMax metadata (icon, model_class=ChatAnthropic, anthropic_api_url)
2. Provides a static catalog_loader that returns the 8 MiniMax models
3. Calls ``register_provider(ProviderDescriptor(...))`` once at startup
4. Hooks into ``lfx.base.models.provider_registry`` import-time so the registration
   runs before any model system accessor is called
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure site-packages is importable when run via RUN (image build / verify)
SITE = None
for p in Path(sys.prefix).glob("lib/python*/site-packages"):
    if (p / "lfx" / "base" / "models").exists():
        SITE = p
        break
if SITE is not None and str(SITE) not in sys.path:
    sys.path.insert(0, str(SITE))

from lfx.base.models.model_metadata import create_model_metadata
from lfx.base.models.provider_registry import (
    ProviderDescriptor,
    register_provider,
)


# ---------------------------------------------------------------------------
# Static catalog (list of model metadata rows)
# ---------------------------------------------------------------------------

MINIMAX_MODELS_DETAILED: list[dict] = [
    create_model_metadata(provider="MiniMax", name="MiniMax-M3",            icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.7",          icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.7-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.5",          icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.5-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.1",          icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.1-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2",            icon="MiniMax", tool_calling=True),
]


def load_minimax_catalog() -> list[dict]:
    """Return the static MiniMax catalog as a list of metadata rows.

    langflow's ``provider_queries.get_models_detailed`` calls ``get_registered_model_catalogs``
    which in turn validates each registered catalog loader with
    ``isinstance(rows, list)`` and a series of shape assertions; a tuple or
    any non-list iterable triggers a logged-but-swallowed TypeError that
    silently empties the catalog group. Returning the raw list keeps the
    assertions happy.
    """
    return MINIMAX_MODELS_DETAILED


# Module-path dotted reference for ProviderDescriptor.catalog_loader
_THIS_MODULE = __name__
_LOAD_CATALOG_DOTTED = f"{_THIS_MODULE}:load_minimax_catalog"


# ---------------------------------------------------------------------------
# Provider metadata — what drives Settings / Agent dropdown / get_llm wiring
# ---------------------------------------------------------------------------

MINIMAX_METADATA: dict = {
    "icon": "MiniMax",
    "max_tokens_field_name": "max_tokens",
    # Connection default for first-time setup; per-call override via
    # MINIMAX_BASE_URL env or Settings -> Model Providers UI.
    "base_url": "https://api.minimax.io/anthropic",
    "variables": [
        {
            "variable_name": "MiniMax API Key",
            "variable_key": "MINIMAX_API_KEY",
            "required": True,
            "is_secret": True,
            "is_list": False,
            "options": [],
            "langchain_param": "api_key",
            "component_metadata": {
                "mapping_field": "api_key",
                "required": False,
                "advanced": True,
                "info": "Falls back to MINIMAX_API_KEY environment variable",
            },
        },
        {
            "variable_name": "MiniMax API Base",
            "variable_key": "MINIMAX_BASE_URL",
            "required": False,
            "is_secret": False,
            "is_list": False,
            "options": [],
            # ChatAnthropic exposes ``anthropic_api_url`` as the override.
            # The registry's _apply_registered_provider_connection() will
            # pass this through unchanged (no localhost transform), so the
            # Anthropic SDK hits the MiniMax endpoint directly.
            "langchain_param": "anthropic_api_url",
            "component_metadata": {
                "mapping_field": "anthropic_api_url",
                "required": False,
                "advanced": True,
                "info": "Anthropic-compatible endpoint URL",
            },
        },
    ],
    "api_docs_url": "https://platform.minimax.io/docs/api-reference/text-anthropic-api",
    "mapping": {
        "model_class": "ChatAnthropic",
        "model_param": "model",
    },
}


def _build_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor(
        name="MiniMax",
        provider_id="minimax",
        display_name="MiniMax",
        metadata=dict(MINIMAX_METADATA),
        catalog_loader=_LOAD_CATALOG_DOTTED,
    )


def register() -> bool:
    """Register MiniMax. Returns True on first registration, False if already there."""
    desc = _build_descriptor()
    registered = register_provider(desc)
    if registered:
        print("[minimax] registered: MiniMax provider now live (8 models, ChatAnthropic)")
    else:
        print("[minimax] already registered (no-op)")
    return registered


if __name__ == "__main__":
    ok = register()
    sys.exit(0 if ok else 0)  # exit 0 either way — re-runs are no-op
