"""
services/campaign_service.py
============================
Manages Optimization Campaigns, Portfolios, Decision Tracking, and the Multi-Parameter Optimization (MPO) Engine.
"""

import uuid
import math
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Portfolio, OptimizationCampaign, CampaignSeriesLink, OptimizationDecision, SeriesCompound, ResearchProject, ChemicalSeries

logger = logging.getLogger(__name__)

class MpoEngine:
    """
    Calculates Multi-Parameter Optimization (MPO) scores based on desirability functions.
    """
    @staticmethod
    def pfizer_cns_mpo(props: Dict[str, Any]) -> float:
        """
        Implementation of the standard Pfizer CNS MPO score.
        Calculates a score from 0-6 based on 6 parameters: LogP, LogD, MW, TPSA, HBD, pKa.
        (We approximate LogD with LogP, and omit pKa if unavailable).
        """
        score = 0.0
        
        # LogP (Desired: <=3 is 1.0, >5 is 0.0)
        logp = props.get("logp")
        if logp is not None:
            if logp <= 3: score += 1.0
            elif logp >= 5: score += 0.0
            else: score += (5 - logp) / 2.0
            
        # MW (Desired: <=360 is 1.0, >500 is 0.0)
        mw = props.get("mw")
        if mw is not None:
            if mw <= 360: score += 1.0
            elif mw >= 500: score += 0.0
            else: score += (500 - mw) / 140.0
            
        # TPSA (Desired: 40-90 is 1.0, <20 or >120 is 0.0)
        tpsa = props.get("tpsa")
        if tpsa is not None:
            if 40 <= tpsa <= 90: score += 1.0
            elif tpsa < 20: score += (tpsa) / 20.0
            elif tpsa > 120: score += 0.0
            else: score += (120 - tpsa) / 30.0 # roughly
            
        # HBD (Desired: <=0 is 1.0, >3 is 0.0, 1-2 is intermediate)
        # Actually standard Pfizer MPO: HBD=0 -> 1, HBD=1 -> 0.5, HBD>1 -> 0, but often HBD<=0.5 is 1.
        hbd = props.get("hbd")
        if hbd is not None:
            if hbd == 0: score += 1.0
            elif hbd == 1: score += 0.5
            else: score += 0.0
            
        # Basic pKa is standard in Pfizer MPO, but we lack basic pKa calculation via basic RDKit.
        # We will assume a score of 4 max for these 4 parameters for simplicity in this implementation,
        # normalized back to a 10-point scale for consistency with our generic score.
        
        # Normalize to 10
        return round((score / 4.0) * 10.0, 1)

    @staticmethod
    def generic_mpo(props: Dict[str, Any], weights: Dict[str, float]) -> float:
        """
        Calculates a generic weighted MPO score (0-10 scale).
        Expected weights: {"potency": 1.0, "lipophilicity": 1.0, "polar_surface": 0.5, "safety": 1.0}
        """
        score = 0.0
        total_weight = sum(weights.values()) if weights else 1.0
        if total_weight == 0: total_weight = 1.0
        
        # Potency (pIC50) - Linear desirability (e.g., pIC50 5=0.2, pIC50 9=1.0)
        potency_w = weights.get("potency", 1.0)
        pic50 = props.get("normalized_value") # Note: we pass compound data here later
        if pic50:
            pot = min(1.0, max(0.0, (pic50 - 4.0) / 5.0))
            score += pot * potency_w
            
        # Lipophilicity (LogP) - Parabolic desirability centered around 3.0
        lip_w = weights.get("lipophilicity", 1.0)
        logp = props.get("logp", 0)
        lip = max(0.0, 1.0 - (abs(logp - 3.0) / 3.0))
        score += lip * lip_w
        
        # Safety (ADMET penalties)
        safe_w = weights.get("safety", 1.0)
        admet = props.get("admet", {})
        developability = admet.get("developability_score", 5.0) / 10.0
        score += developability * safe_w
        
        return round((score / total_weight) * 10.0, 1)

class CampaignService:
    def __init__(self, db: Session):
        self.db = db

    # ==========================
    # Portfolios & Campaigns
    # ==========================
    
    def create_portfolio(self, name: str, description: str = "", project_id: Optional[str] = None) -> Portfolio:
        """
        Creates a Portfolio owned by a ResearchProject (Project -> Portfolio is 1:N).
        project_id is validated when supplied; it stays optional only until the
        project-scoped routes make it mandatory.
        """
        if project_id and not self.db.query(ResearchProject).filter_by(id=project_id).first():
            raise ValueError(f"Research project not found: {project_id}")

        p = Portfolio(
            id=f"port_{uuid.uuid4().hex[:10]}",
            project_id=project_id,
            name=name,
            description=description,
        )
        self.db.add(p)
        self.db.commit()
        return p

    def create_campaign(self, portfolio_id: str, name: str, goal_type: str, weights: Dict[str, float]) -> OptimizationCampaign:
        """Creates a Campaign owned by a Portfolio (Portfolio -> Campaign is 1:N)."""
        if not self.db.query(Portfolio).filter_by(id=portfolio_id).first():
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        c = OptimizationCampaign(
            id=f"camp_{uuid.uuid4().hex[:10]}",
            portfolio_id=portfolio_id,
            name=name,
            goal_type=goal_type,
            mpo_weights=weights
        )
        self.db.add(c)
        self.db.commit()
        return c

    def link_series_to_campaign(self, campaign_id: str, series_id: str):
        """
        Associates a ChemicalSeries with a Campaign (Campaign <-> Series is M:N,
        so a series may legitimately be reused across campaigns). Idempotent.
        """
        if not self.db.query(OptimizationCampaign).filter_by(id=campaign_id).first():
            raise ValueError(f"Campaign not found: {campaign_id}")
        if not self.db.query(ChemicalSeries).filter_by(id=series_id).first():
            raise ValueError(f"Chemical series not found: {series_id}")

        existing = self.db.query(CampaignSeriesLink).filter_by(
            campaign_id=campaign_id, series_id=series_id
        ).first()
        if existing:
            return

        link = CampaignSeriesLink(campaign_id=campaign_id, series_id=series_id)
        self.db.add(link)
        self.db.commit()

    # ==========================
    # Project-scoped reads (context propagation)
    # ==========================

    def portfolios_for_project(self, project_id: str) -> List[Portfolio]:
        """Portfolios owned by a project (1:N)."""
        return (
            self.db.query(Portfolio)
            .filter(Portfolio.project_id == project_id)
            .order_by(Portfolio.created_at.desc())
            .all()
        )

    def campaigns_for_project(self, project_id: str) -> List[OptimizationCampaign]:
        """Campaigns reachable as Project -> Portfolio -> Campaign."""
        return (
            self.db.query(OptimizationCampaign)
            .join(Portfolio, OptimizationCampaign.portfolio_id == Portfolio.id)
            .filter(Portfolio.project_id == project_id)
            .order_by(OptimizationCampaign.created_at.desc())
            .all()
        )

    def series_ids_for_project(self, project_id: str) -> List[str]:
        """
        The project's *reachable* series set: Project -> Portfolio -> Campaign
        -> CampaignSeriesLink -> Series. A series may be reused across campaigns
        (M:N), so it can legitimately appear under more than one project.
        """
        rows = (
            self.db.query(CampaignSeriesLink.series_id)
            .join(OptimizationCampaign, CampaignSeriesLink.campaign_id == OptimizationCampaign.id)
            .join(Portfolio, OptimizationCampaign.portfolio_id == Portfolio.id)
            .filter(Portfolio.project_id == project_id)
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    def series_for_project(self, project_id: str) -> List[ChemicalSeries]:
        ids = self.series_ids_for_project(project_id)
        if not ids:
            return []
        return (
            self.db.query(ChemicalSeries)
            .filter(ChemicalSeries.id.in_(ids))
            .order_by(ChemicalSeries.updated_at.desc())
            .all()
        )

    # ==========================
    # Decisions & Status
    # ==========================

    def record_decision(self, campaign_id: str, compound_ids: List[str], decision_type: str, rationale: str) -> OptimizationDecision:
        # Snapshot evidence
        compounds = self.db.query(SeriesCompound).filter(SeriesCompound.id.in_(compound_ids)).all()
        evidence = {c.id: {"mpo": self.calculate_compound_mpo(c, campaign_id)} for c in compounds}
        
        dec = OptimizationDecision(
            id=f"dec_{uuid.uuid4().hex[:10]}",
            campaign_id=campaign_id,
            compound_ids=compound_ids,
            decision_type=decision_type,
            rationale=rationale,
            evidence_data=evidence
        )
        self.db.add(dec)
        
        # Update compound status inside properties to respect DB evolution constraints
        for c in compounds:
            props = c.properties or {}
            props["candidate_status"] = decision_type
            c.properties = props
            
        self.db.commit()
        return dec

    def calculate_compound_mpo(self, compound: SeriesCompound, campaign_id: str) -> Dict[str, float]:
        """Calculates Pfizer and Generic MPO scores for a compound in the context of a campaign."""
        campaign = self.db.query(OptimizationCampaign).filter_by(id=campaign_id).first()
        weights = campaign.mpo_weights if campaign and campaign.mpo_weights else {"potency": 1.0, "lipophilicity": 1.0, "safety": 1.0}
        
        props = compound.properties or {}
        # Merge normalized_value into props for generic scoring
        eval_props = {**props, "normalized_value": compound.normalized_value}
        
        return {
            "pfizer_cns": MpoEngine.pfizer_cns_mpo(eval_props),
            "generic": MpoEngine.generic_mpo(eval_props, weights)
        }
