"""
services/knowledge_graph.py
===========================
Simulates a Knowledge Graph by recursively traversing relational SQLite schemas.
Connects Projects -> Portfolios -> Campaigns -> Series -> Compounds -> Decisions/Notebooks.
"""

from sqlalchemy.orm import Session
from database.models import (
    ResearchProject, Portfolio, OptimizationCampaign,
    CampaignSeriesLink, ChemicalSeries, SeriesCompound,
    OptimizationDecision, NotebookEntry, LiteratureReference
)

class KnowledgeGraphService:
    def __init__(self, db: Session):
        self.db = db

    def build_project_graph(self, project_id: str) -> dict:
        """
        Recursively builds a tree representing the knowledge graph of a project.
        """
        project = self.db.query(ResearchProject).filter_by(id=project_id).first()
        if not project:
            return {}

        graph = {
            "id": project.id,
            "type": "Project",
            "name": project.name,
            "objectives": project.objectives,
            "literature": [],
            "notebooks": [],
            "portfolios": []
        }

        # Fetch Literature
        lits = self.db.query(LiteratureReference).filter_by(project_id=project_id).all()
        graph["literature"] = [{"doi": l.doi, "title": l.title} for l in lits]

        # Fetch Project-level notebooks
        notes = self.db.query(NotebookEntry).filter_by(project_id=project_id, entity_type="Project").all()
        graph["notebooks"] = [{"type": n.entry_type, "content": n.content, "date": n.date.isoformat()} for n in notes]

        # Traverse Portfolios -> Campaigns (Project owns Portfolio via project_id)
        portfolios = self.db.query(Portfolio).filter_by(project_id=project_id).all()
        for portfolio in portfolios:
            port_node = {"id": portfolio.id, "type": "Portfolio", "name": portfolio.name, "campaigns": []}

            campaigns = self.db.query(OptimizationCampaign).filter_by(portfolio_id=portfolio.id).all()
            for camp in campaigns:
                camp_node = {
                    "id": camp.id,
                    "type": "Campaign",
                    "name": camp.name,
                    "series": [],
                    "decisions": []
                }
                
                # Fetch Decisions for Campaign
                decs = self.db.query(OptimizationDecision).filter_by(campaign_id=camp.id).all()
                camp_node["decisions"] = [
                    {"type": d.decision_type, "compounds": d.compound_ids, "rationale": d.rationale} for d in decs
                ]
                
                # Traverse Series -> Compounds
                c_links = self.db.query(CampaignSeriesLink).filter_by(campaign_id=camp.id).all()
                for clink in c_links:
                    series = self.db.query(ChemicalSeries).filter_by(id=clink.series_id).first()
                    if series:
                        series_node = {
                            "id": series.id,
                            "type": "Series",
                            "name": series.name,
                            "compounds_count": self.db.query(SeriesCompound).filter_by(series_id=series.id).count()
                        }
                        camp_node["series"].append(series_node)
                        
                port_node["campaigns"].append(camp_node)
                
            graph["portfolios"].append(port_node)

        return graph

    def get_timeline(self, project_id: str) -> list:
        """
        Returns a flat, chronologically sorted list of all events (Decisions, Notebook Entries).
        """
        events = []
        
        # Notebooks
        notes = self.db.query(NotebookEntry).filter_by(project_id=project_id).all()
        for n in notes:
            events.append({
                "date": n.date,
                "type": f"Notebook: {n.entry_type}",
                "content": n.content,
                "entity": f"{n.entity_type} ({n.entity_id})"
            })
            
        # To get decisions, we need campaigns attached to this project
        port_ids = [p.id for p in self.db.query(Portfolio).filter_by(project_id=project_id).all()]
        camp_ids = []
        if port_ids:
            campaigns = self.db.query(OptimizationCampaign).filter(OptimizationCampaign.portfolio_id.in_(port_ids)).all()
            camp_ids = [c.id for c in campaigns]

        decs = []
        if camp_ids:
            decs = self.db.query(OptimizationDecision).filter(OptimizationDecision.campaign_id.in_(camp_ids)).all()
        for d in decs:
            events.append({
                "date": d.date,
                "type": f"Decision: {d.decision_type}",
                "content": d.rationale,
                "entity": f"Campaign ({d.campaign_id})"
            })
            
        # Sort by date descending
        events.sort(key=lambda x: x["date"], reverse=True)
        return events
