"""
core/external_tools.py
======================
Runtime configuration and helpers for external scientific tools
(ChimeraX, etc.).

This follows a similar lightweight pattern to the LLM provider switching
in `core/llm_utils.py`.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .config import get_settings, ExternalToolsSettings

logger = logging.getLogger(__name__)


# In-memory override (takes precedence over config file / env)
_chimera_executable_override: Optional[str] = None


def get_chimera_executable() -> Optional[str]:
    """
    Return the currently configured ChimeraX / Chimera executable path.

    Resolution order:
    1. Runtime override (set via Settings page)
    2. Value from config (env var or .env)
    3. None
    """
    if _chimera_executable_override:
        return _chimera_executable_override

    settings = get_settings()
    return settings.external_tools.chimera_executable


def set_chimera_executable(path: Optional[str]) -> None:
    """
    Set the ChimeraX executable path at runtime (e.g. from the Settings UI).
    """
    global _chimera_executable_override
    if path:
        _chimera_executable_override = str(Path(path).expanduser())
        logger.info("ChimeraX executable set to: %s", _chimera_executable_override)
    else:
        _chimera_executable_override = None
        logger.info("ChimeraX executable cleared")


def clear_chimera_executable() -> None:
    """Reset to the value from configuration."""
    global _chimera_executable_override
    _chimera_executable_override = None


def is_chimera_available() -> bool:
    """Quick check whether a ChimeraX executable is currently configured."""
    exe = get_chimera_executable()
    if not exe:
        return False
    return Path(exe).exists()


def get_external_tools_status() -> dict:
    """Return status information useful for the frontend."""
    exe = get_chimera_executable()
    return {
        "chimera_executable": exe,
        "chimera_available": is_chimera_available(),
        "auto_launch": get_settings().external_tools.auto_launch,
    }
