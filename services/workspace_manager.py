"""
services/workspace_manager.py
=============================
Handles project-level workspace persistence using a hybrid storage model:
- Lightweight metadata and state (step, toggles) are stored in SQLite.
- Heavy blobs (PDB strings) are saved directly to the file system.
"""

import os
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from database.models import Workspace

WORKSPACE_DATA_DIR = os.path.join(os.getcwd(), "outputs", "workspaces")

def _get_workspace_dir(workspace_id: str) -> str:
    """Get the file system directory for a workspace's heavy blobs."""
    path = os.path.join(WORKSPACE_DATA_DIR, workspace_id)
    os.makedirs(path, exist_ok=True)
    return path


def get_workspace(db: Session, workspace_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a workspace by ID, combining lightweight DB state
    with heavy blob data from the file system.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return None

    result = workspace.to_dict()
    heavy_data = {}

    if workspace.file_path and os.path.exists(workspace.file_path):
        try:
            with open(workspace.file_path, "r", encoding="utf-8") as f:
                heavy_data = json.load(f)
        except Exception as e:
            print(f"Failed to read heavy workspace data for {workspace_id}: {e}")

    result["heavy_data"] = heavy_data
    return result


def list_workspaces(db: Session, module: Optional[str] = None) -> list[Dict[str, Any]]:
    """List all workspaces, optionally filtered by module."""
    query = db.query(Workspace)
    if module:
        query = query.filter(Workspace.module == module)
    
    workspaces = query.order_by(Workspace.updated_at.desc()).all()
    return [w.to_dict() for w in workspaces]


def create_workspace(db: Session, name: str, module: str, state: Dict[str, Any] = None, heavy_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a new workspace."""
    workspace_id = f"wksp_{uuid.uuid4().hex[:12]}"
    file_path = os.path.join(_get_workspace_dir(workspace_id), "heavy_data.json")

    # Save heavy data to filesystem if provided
    if heavy_data:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(heavy_data, f)
    else:
        file_path = None

    workspace = Workspace(
        id=workspace_id,
        name=name,
        module=module,
        version=1,
        state=state or {},
        file_path=file_path
    )

    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    result = workspace.to_dict()
    result["heavy_data"] = heavy_data or {}
    return result


def update_workspace(db: Session, workspace_id: str, state: Dict[str, Any] = None, heavy_data: Dict[str, Any] = None, name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Update an existing workspace, bumping the version number and persisting data.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        return None

    if name:
        workspace.name = name

    if state is not None:
        workspace.state = state

    if heavy_data is not None:
        file_path = os.path.join(_get_workspace_dir(workspace_id), "heavy_data.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(heavy_data, f)
            workspace.file_path = file_path
        except Exception as e:
            print(f"Failed to write heavy workspace data for {workspace_id}: {e}")

    workspace.version += 1
    workspace.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(workspace)

    result = workspace.to_dict()
    result["heavy_data"] = heavy_data if heavy_data is not None else {}
    
    # If heavy_data wasn't explicitly passed but we need it for the full response:
    if heavy_data is None and workspace.file_path and os.path.exists(workspace.file_path):
        try:
            with open(workspace.file_path, "r", encoding="utf-8") as f:
                result["heavy_data"] = json.load(f)
        except:
            pass

    return result
