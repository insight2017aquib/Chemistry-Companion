"""
services/ai/medchem_expert.py
=============================
AI Medicinal Chemist for SAR analysis and Lead Optimization.
Strictly instructed not to hallucinate binding affinities or make speculative claims.
"""

from typing import List, Dict, Any
import json
from .provider_manager import AIProviderManager

MEDCHEM_SYSTEM_PROMPT = """You are an expert Medicinal Chemist specializing in Lead Optimization and Structure-Activity Relationships (SAR).
Your role is to act as a decision-support system.

CRITICAL RULES:
1. NEVER invent or guarantee experimental activities (e.g. "This will have 10nM IC50").
2. Explain the physical chemistry rationale behind substitutions (e.g. LogP changes, TPSA changes, steric bulk).
3. Base your analysis strictly on the provided data.
4. Distinguish clearly between OBSERVED DATA (what is in the dataset) and HYPOTHESES (what you suggest might happen).
5. If asked to suggest analogs, provide logical bioisosteres or scaffold hops, explaining *why* they might improve the target profile (e.g. "Adding a fluorine may block metabolism at this position").
6. Format your output in clean Markdown.
"""

class MedChemExpertService:
    def __init__(self):
        self.ai = AIProviderManager()

    def analyze_sar_trends(self, series_name: str, compounds: List[Dict[str, Any]]) -> str:
        """
        Generates a markdown report explaining SAR trends across a series.
        """
        # Filter down to essential fields to save tokens
        clean_compounds = []
        for c in compounds:
            props = c.get("properties", {})
            pic50 = c.get("pic50", {}).get("value")
            affinity = c.get("docking_affinity")
            
            clean_compounds.append({
                "Name": c.get("name"),
                "SMILES": c.get("smiles"),
                "pIC50": pic50 if pic50 else "Unknown",
                "Docking_Affinity": affinity if affinity else "Unknown",
                "MW": props.get("mw"),
                "LogP": props.get("logp"),
                "TPSA": props.get("tpsa")
            })

        prompt = f"""Analyze the following Chemical Series: {series_name}

COMPOUNDS DATA:
{json.dumps(clean_compounds, indent=2)}

Please provide:
1. An overview of the series properties.
2. Any observable trends between the physicochemical properties (MW, LogP) and the activity (pIC50 or Docking Affinity).
3. Identification of potential "activity cliffs" if any small structural changes caused large activity shifts.
4. Recommendations for which physicochemical parameter to optimize next.
"""
        full_prompt = f"{MEDCHEM_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def suggest_analogs(self, base_compound: Dict[str, Any], target_profile: str) -> str:
        """
        Suggests analogs based on a desired optimization profile.
        """
        prompt = f"""Suggest analogs for the following compound to achieve this target profile: "{target_profile}"

BASE COMPOUND:
Name: {base_compound.get('name')}
SMILES: {base_compound.get('smiles')}
MW: {base_compound.get('properties', {}).get('mw')}
LogP: {base_compound.get('properties', {}).get('logp')}

Please provide 3-5 specific analog ideas. For each:
- Describe the structural modification (e.g., "Replace the phenyl ring with a pyridine").
- Explain the physicochemical rationale (e.g., "This lowers LogP and reduces potential hERG liabilities").
- Estimate the synthetic feasibility (High, Moderate, Low).

DO NOT guarantee binding affinity. Focus on physical properties and known medchem principles.
"""
        full_prompt = f"{MEDCHEM_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
