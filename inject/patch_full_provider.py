#!/usr/bin/env python3
"""Patch all necessary Langflow files to register MiniMax as a Global Model Provider.

Files patched:
1. lfx/base/models/minimax_constants.py (NEW)
2. lfx/base/models/model_metadata.py (add MODEL_PROVIDER_METADATA["MiniMax"])
3. lfx/base/models/unified_models/provider_queries.py (add MINIMAX_MODELS_DETAILED)
4. lfx/base/models/model_input_constants.py (add to MODEL_PROVIDERS_DICT + MODEL_PROVIDERS_LIST)
"""
import re
import sys
from pathlib import Path

VENV_LIB = Path(sys.prefix) / "lib"
SITE_PACKAGES = None
for p in VENV_LIB.glob("python*/site-packages"):
    if (p / "lfx" / "base" / "models" / "model_input_constants.py").exists():
        SITE_PACKAGES = p
        break
if not SITE_PACKAGES:
    print("ERROR: site-packages not found")
    sys.exit(1)

MODELS_DIR = SITE_PACKAGES / "lfx" / "base" / "models"
print(f"Patching in: {MODELS_DIR}")

# ============================================================================
# 1. minimax_constants.py
# ============================================================================
minimax_constants = '''from .model_metadata import create_model_metadata

MINIMAX_MODELS_DETAILED = [
    create_model_metadata(provider="MiniMax", name="MiniMax-M3", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.7", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.7-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.5", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.5-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.1", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2.1-highspeed", icon="MiniMax", tool_calling=True),
    create_model_metadata(provider="MiniMax", name="MiniMax-M2", icon="MiniMax", tool_calling=True),
]

MINIMAX_MODELS = [m["name"] for m in MINIMAX_MODELS_DETAILED]

TOOL_CALLING_SUPPORTED_MINIMAX_MODELS = [
    m["name"] for m in MINIMAX_MODELS_DETAILED if m.get("tool_calling", False)
]

DEFAULT_MINIMAX_API_URL = "https://api.minimax.io/anthropic"
'''

(MODELS_DIR / "minimax_constants.py").write_text(minimax_constants)
print("OK: minimax_constants.py created")

# ============================================================================
# 2. model_metadata.py — add MiniMax entry to MODEL_PROVIDER_METADATA
# ============================================================================
mm_file = MODELS_DIR / "model_metadata.py"
mm_content = mm_file.read_text()

minimax_entry = '''
    "MiniMax": {
        "icon": "MiniMax",
        "max_tokens_field_name": "max_tokens",
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
            }
        ],
        "api_docs_url": "https://platform.minimax.io/docs/api-reference/text-anthropic-api",
        "mapping": {
            "model_class": "ChatAnthropic",
            "model_param": "model",
        },
    },
'''

if '"MiniMax"' not in mm_content:
    # Insert before the closing brace of MODEL_PROVIDER_METADATA
    mm_content = mm_content.replace(
        '    "OpenRouter": {',
        minimax_entry + '    "OpenRouter": {',
        1
    )
    mm_file.write_text(mm_content)
    print("OK: model_metadata.py patched")
else:
    print("SKIP: model_metadata.py already has MiniMax")

# ============================================================================
# 3. provider_queries.py — add MINIMAX_MODELS_DETAILED import + static list
# ============================================================================
pq_file = MODELS_DIR / "unified_models" / "provider_queries.py"
if pq_file.exists():
    pq_content = pq_file.read_text()

    if 'minimax_constants' not in pq_content:
        # Add import
        old_import = "from lfx.base.models.openrouter_constants import OPENROUTER_MODELS_DETAILED"
        new_import = old_import + "\nfrom lfx.base.models.minimax_constants import MINIMAX_MODELS_DETAILED"
        pq_content = pq_content.replace(old_import, new_import, 1)

        # Add to _STATIC_MODELS_DETAILED
        old_list = "    WATSONX_MODELS_DETAILED,\n]"
        new_list = "    WATSONX_MODELS_DETAILED,\n    MINIMAX_MODELS_DETAILED,\n]"
        pq_content = pq_content.replace(old_list, new_list, 1)

        pq_file.write_text(pq_content)
        print("OK: provider_queries.py patched")
    else:
        print("SKIP: provider_queries.py already has minimax")

# ============================================================================
# 4. model_input_constants.py — add MiniMax to MODEL_PROVIDERS_DICT + LIST
# ============================================================================
mic_file = MODELS_DIR / "model_input_constants.py"
mic_content = mic_file.read_text()

if '_get_minimax_inputs_and_fields' not in mic_content:
    # Add helper function
    minimax_func = '''

def _get_minimax_inputs_and_fields():
    try:
        from lfx.components.minimax.minimax import MiniMaxModelComponent
        minimax_inputs = get_filtered_inputs(MiniMaxModelComponent)
    except ImportError:
        minimax_inputs = []
    return minimax_inputs, create_input_fields_dict(minimax_inputs, "")

'''
    mic_content = mic_content.replace(
        "MODEL_PROVIDERS_DICT: dict[str, ModelProvidersDict] = {}",
        minimax_func + "MODEL_PROVIDERS_DICT: dict[str, ModelProvidersDict] = {}",
        1
    )

    # Add to MODEL_PROVIDERS_DICT
    minimax_block = '''
try:
    from lfx.components.minimax.minimax import MiniMaxModelComponent
    minimax_inputs, minimax_fields = _get_minimax_inputs_and_fields()
    if minimax_inputs:
        MODEL_PROVIDERS_DICT["MiniMax"] = {
            "fields": minimax_fields,
            "inputs": minimax_inputs,
            "prefix": "",
            "component_class": MiniMaxModelComponent(),
            "icon": MiniMaxModelComponent.icon,
            "is_active": True,
        }
except Exception:
    pass

'''
    mic_content = mic_content.replace(
        "# Expose only active providers",
        minimax_block + "# Expose only active providers",
        1
    )

    # Add MiniMax to MODEL_PROVIDERS_LIST
    old_list = 'MODEL_PROVIDERS_LIST = ["Anthropic", "Google Generative AI", "OpenAI", "IBM watsonx.ai", "Ollama"]'
    new_list = 'MODEL_PROVIDERS_LIST = ["Anthropic", "Google Generative AI", "MiniMax", "OpenAI", "IBM watsonx.ai", "Ollama"]'
    mic_content = mic_content.replace(old_list, new_list, 1)

    mic_file.write_text(mic_content)
    print("OK: model_input_constants.py patched")
else:
    print("SKIP: model_input_constants.py already has MiniMax")

print("\nDone! MiniMax is now registered as a global model provider.")
