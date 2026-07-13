"""
api/routes/external_tools.py
============================
Endpoints for configuring external tools (ChimeraX, etc.).
Follows the same lightweight pattern as the LLM provider switcher.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.external_tools import (
    get_chimera_executable,
    set_chimera_executable,
    clear_chimera_executable,
    get_external_tools_status,
    is_chimera_available,
)

router = APIRouter()


class ChimeraPathRequest(BaseModel):
    path: Optional[str] = None


@router.get("/status")
async def external_tools_status():
    """Return current status of external tools."""
    return get_external_tools_status()


@router.get("/chimera")
async def get_chimera_path():
    """Get the currently configured ChimeraX executable path."""
    return {
        "path": get_chimera_executable(),
        "available": is_chimera_available()
    }


@router.post("/chimera")
async def set_chimera_path(req: ChimeraPathRequest):
    """Set or clear the ChimeraX executable path at runtime."""
    try:
        if req.path is None or req.path.strip() == "":
            clear_chimera_executable()
            return {"status": "cleared", "path": None}
        else:
            set_chimera_executable(req.path)
            return {
                "status": "success",
                "path": get_chimera_executable(),
                "available": is_chimera_available()
            }
    except Exception as e:
        raise HTTPException(400, f"Failed to set ChimeraX path: {e}")
