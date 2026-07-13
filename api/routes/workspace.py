"""
api/routes/workspace.py
=======================
API endpoints for Workspace state persistence, auto-save, and recovery.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict

from database.models import get_db
from sqlalchemy.orm import Session
from services import workspace_manager

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str = "Untitled Workspace"
    module: str = "docking"
    state: Dict[str, Any] = {}
    heavy_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(protected_namespaces=())


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    heavy_data: Optional[Dict[str, Any]] = None


@router.post("")
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)):
    """Create a new workspace."""
    workspace = workspace_manager.create_workspace(
        db=db,
        name=payload.name,
        module=payload.module,
        state=payload.state,
        heavy_data=payload.heavy_data
    )
    return workspace


@router.get("")
def list_workspaces(module: Optional[str] = None, db: Session = Depends(get_db)):
    """List all workspaces, optionally filtered by module."""
    return workspace_manager.list_workspaces(db=db, module=module)


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, db: Session = Depends(get_db)):
    """Retrieve workspace state and heavy data for auto-recovery."""
    workspace = workspace_manager.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.put("/{workspace_id}")
def update_workspace(workspace_id: str, payload: WorkspaceUpdate, db: Session = Depends(get_db)):
    """Auto-save an existing workspace."""
    workspace = workspace_manager.update_workspace(
        db=db,
        workspace_id=workspace_id,
        state=payload.state,
        heavy_data=payload.heavy_data,
        name=payload.name
    )
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace
