"""
services/report_service.py
==========================
Generates formatted Markdown reports for MedChem projects.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from database.models import ChemicalSeries, SeriesCompound
from datetime import datetime

class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_series_report(self, series_id: str) -> str:
        """
        Generates a markdown report summarizing the entire Chemical Series.
        """
        series = self.db.query(ChemicalSeries).filter_by(id=series_id).first()
        if not series:
            return "# Error: Series Not Found"
            
        compounds = self.db.query(SeriesCompound).filter_by(series_id=series_id).all()
        
        md = f"# Chemical Series Report: {series.name}\n\n"
        md += f"**Target**: {series.target_name}\n"
        md += f"**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
        md += f"**Compound Count**: {len(compounds)}\n\n"
        
        if series.notes:
            md += f"## Notes\n{series.notes}\n\n"
            
        md += "## Lead Compounds Summary\n\n"
        md += "| Name | SMILES | Activity | MW | LogP | SA Score |\n"
        md += "|---|---|---|---|---|---|\n"
        
        # Sort by best activity (assuming higher pIC50 or lower IC50 is better, we sort by normalized_value desc)
        sorted_compounds = sorted(
            [c for c in compounds if c.normalized_value is not None], 
            key=lambda x: x.normalized_value, 
            reverse=True
        )
        
        # Add the top 10
        for c in sorted_compounds[:10]:
            props = c.properties or {}
            act_str = f"{c.activity_value} {c.activity_unit}" if c.activity_value else "--"
            sa = props.get('sa_score', '--')
            md += f"| {c.name} | `{c.smiles}` | {act_str} | {props.get('mw', '--')} | {props.get('logp', '--')} | {sa} |\n"
            
        md += "\n## Physicochemical Profile\n"
        md += "Overview of drug-likeness metrics across the top compounds.\n"
        
        # Add some aggregate metrics
        if sorted_compounds:
            avg_mw = sum(c.properties.get('mw', 0) for c in sorted_compounds[:10] if c.properties.get('mw')) / min(10, len(sorted_compounds))
            md += f"- **Average Top-10 MW**: {avg_mw:.2f}\n"
            
        return md
