"""
api/routes/first_run.py
=======================
First Run Experience API — setup wizard backend.

Friendly errors only; never return stack traces or raw API keys.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services import first_run_service as fre

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/setup", tags=["setup"])


class PathsPayload(BaseModel):
    database_path: str = ""
    output_path: str = ""
    log_path: str = ""
    workspace_path: str = ""


class AiTestPayload(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434


class FinishPayload(BaseModel):
    paths: PathsPayload
    provider: str = "disabled"
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    ollama_host: str = "127.0.0.1"
    ollama_port: int = 11434
    confirm_overwrite: bool = False
    download_samples: bool = False
    skip: bool = False


@router.get("/status")
async def setup_status() -> Dict[str, Any]:
    try:
        return fre.current_config_public()
    except Exception:
        logger.exception("setup status failed")
        raise HTTPException(
            status_code=500,
            detail="Could not load setup status. Try restarting Chemistry Companion.",
        )


@router.get("/needs-setup")
async def needs_setup() -> Dict[str, Any]:
    try:
        return {"needs_setup": fre.needs_first_run()}
    except Exception:
        logger.exception("needs_setup failed")
        return {"needs_setup": False}


@router.post("/ensure-dirs")
async def ensure_dirs(paths: PathsPayload) -> Dict[str, Any]:
    try:
        created = fre.ensure_dirs(paths.model_dump())
        return {"ok": True, "created": created, "message": "Directories are ready."}
    except Exception:
        logger.exception("ensure_dirs failed")
        return {
            "ok": False,
            "created": [],
            "message": "Could not create one or more folders. Check the paths and permissions.",
        }


@router.post("/validate-paths")
async def validate_paths(paths: PathsPayload) -> Dict[str, Any]:
    try:
        return fre.validate_paths(paths.model_dump())
    except Exception:
        logger.exception("validate_paths failed")
        return {
            "ok": False,
            "checks": [],
            "message": "Path validation failed. Choose different folders.",
        }


@router.get("/tools")
async def detect_tools() -> Dict[str, Any]:
    try:
        tools = fre.detect_scientific_tools()
        return {"ok": True, "tools": tools}
    except Exception:
        logger.exception("tool detection failed")
        return {
            "ok": False,
            "tools": [],
            "message": "Could not complete tool detection. You can continue setup anyway.",
        }


@router.post("/test-ai")
async def test_ai(body: AiTestPayload) -> Dict[str, Any]:
    try:
        return fre.test_ai_connection(
            provider=body.provider,
            api_key=body.api_key,
            model=body.model,
            base_url=body.base_url,
            ollama_host=body.ollama_host,
            ollama_port=body.ollama_port,
        )
    except Exception:
        logger.exception("test_ai failed")
        return {
            "ok": False,
            "message": "Connection test failed. Check your settings and try again.",
        }


@router.post("/samples")
async def download_samples() -> Dict[str, Any]:
    try:
        return fre.copy_sample_datasets()
    except Exception:
        logger.exception("sample copy failed")
        return {
            "ok": False,
            "copied": [],
            "message": "Could not copy sample datasets. You can skip this step.",
        }


@router.post("/finish")
async def finish_setup(body: FinishPayload) -> Dict[str, Any]:
    try:
        paths = body.paths.model_dump()
        fre.ensure_dirs(paths)

        provider = "disabled" if body.skip else (body.provider or "disabled")
        result = fre.write_env_config(
            paths=paths,
            provider=provider,
            api_key="" if body.skip else body.api_key,
            model="" if body.skip else body.model,
            base_url="" if body.skip else body.base_url,
            ollama_host=body.ollama_host,
            ollama_port=body.ollama_port,
            confirm_overwrite=body.confirm_overwrite or body.skip,
            force=body.skip,
        )
        if result.get("needs_confirmation"):
            return result

        samples: Dict[str, Any] = {}
        if body.download_samples and not body.skip:
            samples = fre.copy_sample_datasets()

        validation = fre.final_validation(paths, provider)
        return {
            "ok": bool(result.get("ok")) and bool(validation.get("ok")),
            "message": result.get("message", "Configuration saved."),
            "path": result.get("path"),
            "validation": validation,
            "samples": samples,
            "redirect": "/",
        }
    except Exception:
        logger.exception("finish_setup failed")
        return {
            "ok": False,
            "message": "Could not save configuration. Check folder permissions and try again.",
        }


@router.post("/validate")
async def validate_setup(body: FinishPayload) -> Dict[str, Any]:
    try:
        paths = body.paths.model_dump()
        return fre.final_validation(paths, body.provider)
    except Exception:
        logger.exception("validate_setup failed")
        return {
            "ok": False,
            "ready_message": "Validation could not complete",
            "checks": [],
        }
