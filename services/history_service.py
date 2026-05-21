"""
services/history_service.py
===========================
Persist and retrieve analysis history via SQLite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from database.models import AnalysisResult as DBAnalysisResult
from api.serializers import serialize_analysis_result
from core.models import AnalysisResult


class HistoryService:
    """CRUD operations for analysis history."""

    def save_analysis(self, db: Session, result: AnalysisResult) -> dict[str, Any]:
        payload = serialize_analysis_result(result)
        mol = payload.get("molecule", {})
        record_id = str(uuid.uuid4())[:12]

        entry = DBAnalysisResult(
            id=record_id,
            name=mol.get("name"),
            smiles=mol.get("smiles"),
            inchi=mol.get("inchi"),
            iupac=None,
            descriptors=payload.get("descriptors"),
            functional_groups=payload.get("functional_group_report"),
            ir_prediction=payload.get("ir_prediction"),
            proton_nmr_prediction=payload.get("proton_nmr_prediction"),
            carbon_nmr_prediction=payload.get("carbon_nmr_prediction"),
            structure_image_path=payload.get("visualization_path"),
            export_paths=payload.get("export_paths"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry.to_dict()

    def list_analyses(
        self,
        db: Session,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        q = db.query(DBAnalysisResult).order_by(DBAnalysisResult.created_at.desc())
        if query:
            term = f"%{query.strip()}%"
            q = q.filter(
                (DBAnalysisResult.name.ilike(term))
                | (DBAnalysisResult.smiles.ilike(term))
            )
        rows = q.offset(offset).limit(limit).all()
        return [row.to_dict() for row in rows]

    def get_analysis(self, db: Session, record_id: str) -> dict[str, Any] | None:
        row = db.query(DBAnalysisResult).filter(DBAnalysisResult.id == record_id).first()
        return row.to_dict() if row else None

    def delete_analysis(self, db: Session, record_id: str) -> bool:
        row = db.query(DBAnalysisResult).filter(DBAnalysisResult.id == record_id).first()
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True
