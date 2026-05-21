"""
api/routes/history.py
=====================
Analysis history CRUD endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.orm import Session

from database.models import get_db
from services.history_service import HistoryService

logger = logging.getLogger(__name__)
router = APIRouter()
history_service = HistoryService()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/history")
async def list_history(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    items = history_service.list_analyses(db, query=q, limit=limit, offset=offset)
    return {"items": items, "count": len(items)}


@router.get("/history/{record_id}")
async def get_history_item(record_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    item = history_service.get_analysis(db, record_id)
    if not item:
        raise HTTPException(status_code=404, detail="Record not found")
    return item


@router.delete("/history/{record_id}")
async def delete_history_item(record_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not history_service.delete_analysis(db, record_id):
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "deleted", "id": record_id}


@router.get("/history/table", response_class=HTMLResponse, include_in_schema=False)
async def history_table_partial(
    request: Request,
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """HTMX partial for history table rows."""
    items = history_service.list_analyses(db, query=q, limit=100)
    return templates.TemplateResponse(
        "components/history_table.html",
        {"request": request, "items": items},
    )


@router.delete("/history/{record_id}/row", response_class=HTMLResponse, include_in_schema=False)
async def delete_history_row(
    request: Request,
    record_id: str,
    db: Session = Depends(get_db),
):
    """HTMX: delete row and return empty (removes element)."""
    history_service.delete_analysis(db, record_id)
    return HTMLResponse("")
