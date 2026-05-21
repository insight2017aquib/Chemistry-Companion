from __future__ import annotations

from datetime import datetime

from database.models import AnalysisResult


def test_history_model_to_dict_preserves_datetime_fields() -> None:
    now = datetime.utcnow()
    record = AnalysisResult(id="test", created_at=now, updated_at=now)

    result = record.to_dict()

    assert result["created_at"] == now
    assert result["updated_at"] == now
