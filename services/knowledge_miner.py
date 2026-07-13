"""
services/knowledge_miner.py
===========================
User-triggered Knowledge Extraction Engine.
Extracts rules, calculates confidence, and detects contradictions.
"""

import uuid
import json
import logging
from typing import List, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from database.models import KnowledgeRule, RuleContradiction, OptimizationDecision, NotebookEntry
from services.memory_search import SimpleBM25
from services.ai.provider_manager import AIProviderManager

logger = logging.getLogger(__name__)

class KnowledgeMinerService:
    def __init__(self, db: Session):
        self.db = db
        self.ai = AIProviderManager()

    def calculate_confidence(self, project_ids: List[str], compound_ids: List[str], consistency_score: float = 1.0) -> str:
        """
        Calculates confidence based on:
        - Evidence Volume (compound count)
        - Project Diversity (project count)
        - Consistency (Placeholder for now, assumes 1.0)
        """
        proj_count = len(set(project_ids))
        comp_count = len(set(compound_ids))
        
        if proj_count >= 3 and comp_count >= 20 and consistency_score > 0.8:
            return "High"
        elif proj_count >= 2 and comp_count >= 5:
            return "Moderate"
        else:
            return "Low"

    def detect_contradictions(self, new_rule_text: str) -> List[KnowledgeRule]:
        """
        Uses BM25 to find existing rules that might contradict the new rule.
        In a full NLP system, this would use NLI (Natural Language Inference).
        Here, we flag highly similar text as *potential* contradictions for manual review.
        """
        approved_rules = self.db.query(KnowledgeRule).filter(KnowledgeRule.status == "Approved").all()
        if not approved_rules:
            return []
            
        corpus = [r.description for r in approved_rules]
        bm25 = SimpleBM25()
        bm25.fit(corpus)
        
        # If a rule shares many tokens, flag it for human review to ensure it isn't contradictory
        top_indices = bm25.search(new_rule_text, top_n=3)
        return [approved_rules[i] for i in top_indices]

    def _campaign_ids_for_project(self, project_id: str) -> List[str]:
        """Campaigns reachable as Project -> Portfolio -> Campaign."""
        from database.models import Portfolio, OptimizationCampaign
        rows = (
            self.db.query(OptimizationCampaign.id)
            .join(Portfolio, OptimizationCampaign.portfolio_id == Portfolio.id)
            .filter(Portfolio.project_id == project_id)
            .all()
        )
        return [r[0] for r in rows]

    def mine_cross_project_patterns(self, project_id: Optional[str] = None) -> int:
        """
        User-triggered extraction of recurring failure modes from discarded
        compound decisions.

        Cross-project by default — seeing across projects is the whole value of
        the Knowledge Engine. Pass project_id to explicitly scope mining to one
        project; resulting rules are then tagged with that project_id (rules
        mined across all projects keep project_id = NULL).

        Degrades gracefully: if there are no discards, or the AI provider is
        unavailable / returns unparseable output, zero rules are created and 0
        is returned. The route must never 500 because of this.
        """
        # 1. Gather Negative Knowledge (discarded compounds and their rationale)
        query = self.db.query(OptimizationDecision).filter(
            OptimizationDecision.decision_type == "Discard"
        )
        if project_id:
            scoped_campaign_ids = self._campaign_ids_for_project(project_id)
            if not scoped_campaign_ids:
                return 0
            query = query.filter(OptimizationDecision.campaign_id.in_(scoped_campaign_ids))
        failed_decisions = query.all()

        # Only mine when there is a meaningful amount of signal.
        rationale_decisions = [d for d in failed_decisions if (d.rationale or "").strip()]
        if len(rationale_decisions) < 3:
            return 0

        # 2. Group rationale by campaign so the LLM can see cross-campaign themes.
        by_campaign = defaultdict(list)
        for d in rationale_decisions:
            by_campaign[d.campaign_id].append(d)

        blocks = []
        for camp_id, decisions in by_campaign.items():
            lines = [f"  - {(d.rationale or '').strip()}" for d in decisions]
            blocks.append(f"Campaign {camp_id}:\n" + "\n".join(lines))
        decisions_text = "\n\n".join(blocks)

        prompt = f"""You are a medicinal chemistry knowledge miner. Below are rationales
recorded when compounds were DISCARDED during optimization campaigns.

Identify recurring failure modes that appear across multiple discards or campaigns.
Ignore one-off, compound-specific notes. Only report themes with real repetition.

Return STRICT JSON of the form:
{{"patterns": [{{"description": "<generalized lesson learned>",
                "category": "<one of: ADMET, SAR, Potency, Selectivity, Synthesis, Other>",
                "campaign_ids": ["..."]}}]}}

If there are no clear recurring patterns, return {{"patterns": []}}.

Output ONLY the JSON object. Do not add commentary, caveats, or a second
alternative answer before or after it.

Discard rationales:
{decisions_text}
"""

        try:
            result = self.ai.query_structured(prompt, expected_keys=["patterns"])
        except Exception as e:  # provider layer should not raise, but be defensive
            logger.warning(f"Knowledge mining AI call failed: {e}")
            return 0

        if not isinstance(result, dict) or result.get("error"):
            logger.info(f"Knowledge mining produced no usable AI output: {result.get('error') if isinstance(result, dict) else result}")
            return 0

        patterns = result.get("patterns") or []
        if not isinstance(patterns, list):
            return 0

        rules_created = 0
        for pat in patterns:
            if not isinstance(pat, dict):
                continue
            rule_text = (pat.get("description") or "").strip()
            if not rule_text:
                continue

            # Dedupe against existing rules with the same lesson.
            exists = self.db.query(KnowledgeRule).filter(KnowledgeRule.description == rule_text).first()
            if exists:
                continue

            # Resolve evidence links back to the real campaigns/compounds.
            camp_ids = [cid for cid in (pat.get("campaign_ids") or []) if cid in by_campaign]
            if not camp_ids:
                camp_ids = list(by_campaign.keys())

            comp_ids = []
            for cid in camp_ids:
                for d in by_campaign.get(cid, []):
                    comp_ids.extend(d.compound_ids or [])

            conf = self.calculate_confidence(camp_ids, comp_ids)
            category = pat.get("category") or "Other"

            rule = KnowledgeRule(
                id=f"kr_{uuid.uuid4().hex[:10]}",
                project_id=project_id,  # NULL when mined across all projects
                description=rule_text,
                category=category,
                confidence=conf,
                status="Pending",
                evidence_payload={"campaigns": camp_ids, "compounds": comp_ids},
                is_negative_knowledge=True,
                provenance={
                    "source": "Automated Mining",
                    "method": "LLM Extraction",
                    "scope": "project" if project_id else "cross-project",
                },
            )
            self.db.add(rule)

            # Flag potential contradictions with existing approved rules.
            potentials = self.detect_contradictions(rule_text)
            for pr in potentials:
                cont = RuleContradiction(
                    id=f"rc_{uuid.uuid4().hex[:10]}",
                    rule_id_1=rule.id,
                    rule_id_2=pr.id,
                    description="Potential contradiction detected via semantic overlap.",
                    status="Unresolved"
                )
                self.db.add(cont)

            rules_created += 1

        if rules_created:
            self.db.commit()

        return rules_created
