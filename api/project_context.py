"""
api/project_context.py
======================
The single source of "which research project am I in?".

Every project-scoped page route declares:

    project: ResearchProject = Depends(get_current_project)

Because the project arrives as a *required dependency* resolved from the URL,
a scoped page route cannot be written without its project context. That is what
structurally prevents the "template renders but was passed no data" bug class
(seen previously on /admet, /publication and /knowledge-engine).
"""

from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import ResearchProject, get_db


def get_current_project(
    project_id: str,
    db: Session = Depends(get_db),
) -> ResearchProject:
    """Resolve the project named in the URL, or 404."""
    project = db.query(ResearchProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"Research project not found: {project_id}")
    return project
