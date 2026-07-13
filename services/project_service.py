"""
services/project_service.py
===========================
Service for managing Research Projects, Notebooks, Literature, and Experiments.
Includes caching and CrossRef API integration for DOIs.
"""

import uuid
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import (
    ResearchProject, ProjectPortfolioLink, NotebookEntry, 
    LiteratureReference, ExperimentRegistry
)

logger = logging.getLogger(__name__)

# Very simple memory cache for DOIs during the session
DOI_CACHE = {}

class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    # ===============================
    # Projects & Portfolios
    # ===============================
    def create_project(self, name: str, target: str, objectives: str) -> ResearchProject:
        p = ResearchProject(
            id=f"proj_{uuid.uuid4().hex[:10]}",
            name=name,
            target=target,
            objectives=objectives
        )
        self.db.add(p)
        self.db.commit()
        return p

    def link_portfolio(self, project_id: str, portfolio_id: str):
        link = ProjectPortfolioLink(project_id=project_id, portfolio_id=portfolio_id)
        self.db.add(link)
        self.db.commit()

    # ===============================
    # Scientific Notebook
    # ===============================
    def add_notebook_entry(self, project_id: str, entity_type: str, entity_id: str, entry_type: str, content: str) -> NotebookEntry:
        entry = NotebookEntry(
            id=f"note_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entry_type=entry_type,
            content=content
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    # ===============================
    # Experiment Registry
    # ===============================
    def log_experiment(self, project_id: str, exp_type: str, target_id: str, params: dict, summary: str) -> ExperimentRegistry:
        exp = ExperimentRegistry(
            id=f"exp_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            experiment_type=exp_type,
            target_entity_id=target_id,
            parameters=params,
            results_summary=summary
        )
        self.db.add(exp)
        self.db.commit()
        return exp

    # ===============================
    # Literature Manager & Crossref
    # ===============================
    def add_literature(self, project_id: str, doi: str, notes: str = "") -> LiteratureReference:
        # Fetch metadata
        meta = self._fetch_doi_metadata(doi)
        
        lit = LiteratureReference(
            id=f"lit_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            doi=doi,
            title=meta.get("title", "Unknown Title"),
            authors=meta.get("authors", ""),
            journal=meta.get("journal", ""),
            year=meta.get("year", 0),
            notes=notes
        )
        self.db.add(lit)
        self.db.commit()
        return lit

    def _fetch_doi_metadata(self, doi: str) -> Dict[str, Any]:
        """Fetches metadata from Crossref API with caching."""
        if not doi:
            return {}
            
        # Clean DOI if it's a URL
        clean_doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "").strip()
        
        if clean_doi in DOI_CACHE:
            return DOI_CACHE[clean_doi]
            
        try:
            # Crossref polite pool etiquette
            headers = {"User-Agent": "ChemistryCompanion/1.0 (mailto:admin@local)"}
            resp = requests.get(f"https://api.crossref.org/works/{clean_doi}", headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("message", {})
                
                title = data.get("title", [""])[0] if data.get("title") else "Unknown Title"
                journal = data.get("container-title", [""])[0] if data.get("container-title") else ""
                
                # Parse authors
                author_list = data.get("author", [])
                authors_str = ", ".join([f"{a.get('given', '')} {a.get('family', '')}".strip() for a in author_list])
                
                # Parse year
                year = 0
                if data.get("published-print", {}).get("date-parts"):
                    year = data["published-print"]["date-parts"][0][0]
                elif data.get("published-online", {}).get("date-parts"):
                    year = data["published-online"]["date-parts"][0][0]

                meta = {
                    "title": title,
                    "authors": authors_str,
                    "journal": journal,
                    "year": year
                }
                DOI_CACHE[clean_doi] = meta
                return meta
        except Exception as e:
            logger.warning(f"Failed to fetch DOI metadata for {clean_doi}: {e}")
            
        return {"title": "Metadata fetch failed"}
