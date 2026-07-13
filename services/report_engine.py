"""
services/report_engine.py
=========================
Generates tabular Markdown/HTML reports specifically designed for academic Thesis/Publication support.
"""

from sqlalchemy.orm import Session
from database.models import CampaignSeriesLink, SeriesCompound

class ReportEngineService:
    def __init__(self, db: Session):
        self.db = db

    def generate_thesis_tables(self, campaign_id: str, format_type: str = "html") -> str:
        """
        Extracts SAR and Physchem data for a Campaign and formats it into a publication-ready table.
        """
        links = self.db.query(CampaignSeriesLink).filter_by(campaign_id=campaign_id).all()
        series_ids = [l.series_id for l in links]
        compounds = self.db.query(SeriesCompound).filter(SeriesCompound.series_id.in_(series_ids)).all()
        
        if not compounds:
            return "<p>No compounds found for this campaign.</p>"

        # We will generate a generic SAR/Physchem table
        # Sort by pIC50 descending
        compounds.sort(key=lambda x: x.normalized_value or 0, reverse=True)

        if format_type == "markdown":
            return self._to_markdown(compounds)
        return self._to_html(compounds)

    def _to_html(self, compounds: list) -> str:
        html = """
        <table class="min-w-full divide-y divide-gray-200 text-sm text-left border">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-3 py-2 border font-bold text-gray-700">ID</th>
                    <th class="px-3 py-2 border font-bold text-gray-700">pIC50</th>
                    <th class="px-3 py-2 border font-bold text-gray-700">MW</th>
                    <th class="px-3 py-2 border font-bold text-gray-700">LogP</th>
                    <th class="px-3 py-2 border font-bold text-gray-700">TPSA</th>
                    <th class="px-3 py-2 border font-bold text-gray-700">Lead Status</th>
                </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
        """
        
        for c in compounds:
            props = c.properties or {}
            status = props.get("candidate_status", "Hit")
            pic50 = f"{c.normalized_value:.2f}" if c.normalized_value else "N/A"
            mw = f"{props.get('mw', 0):.1f}"
            logp = f"{props.get('logp', 0):.2f}"
            tpsa = f"{props.get('tpsa', 0):.1f}"
            
            html += f"""
                <tr>
                    <td class="px-3 py-2 border font-mono">{c.name}</td>
                    <td class="px-3 py-2 border font-bold">{pic50}</td>
                    <td class="px-3 py-2 border">{mw}</td>
                    <td class="px-3 py-2 border">{logp}</td>
                    <td class="px-3 py-2 border">{tpsa}</td>
                    <td class="px-3 py-2 border text-xs">{status}</td>
                </tr>
            """
        html += "</tbody></table>"
        return html

    def _to_markdown(self, compounds: list) -> str:
        md = "| ID | pIC50 | MW | LogP | TPSA | Status |\n"
        md += "|---|---|---|---|---|---|\n"
        
        for c in compounds:
            props = c.properties or {}
            status = props.get("candidate_status", "Hit")
            pic50 = f"{c.normalized_value:.2f}" if c.normalized_value else "N/A"
            mw = f"{props.get('mw', 0):.1f}"
            logp = f"{props.get('logp', 0):.2f}"
            tpsa = f"{props.get('tpsa', 0):.1f}"
            
            md += f"| {c.name} | **{pic50}** | {mw} | {logp} | {tpsa} | {status} |\n"
            
        return md
