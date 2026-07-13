"""
services/ai/docking_expert.py
=============================
AI Docking Expert Service (Phase 7).

This service is responsible for generating structured, evidence-backed
explanations for geometric docking results. It enforces strict separation
of concerns: the AI interprets, but does NOT override, the deterministic
docking physics.
"""

from typing import Dict, List, Any
import json
import logging

from services.ai.provider_manager import AIProviderManager
from services.ai.models import AIResponse

logger = logging.getLogger(__name__)

# Core principle injected into all expert prompts
EXPERT_SYSTEM_PROMPT = """You are an expert computational and medicinal chemist.
CRITICAL RULES:
1. The docking results (affinities, RMSD, interactions) are absolute truth derived from rigid physical physics engines (AutoDock Vina, RDKit, OpenBabel).
2. NEVER invent interactions that are not present in the provided JSON data.
3. NEVER dispute the binding affinity scores or rank order.
4. Your role is purely to EXPLAIN the medicinal chemistry implications of the provided data.
5. Format all output in clean Markdown. Be professional, concise, and scientific.
"""

class DockingExpertService:
    def __init__(self, provider_manager: AIProviderManager = None):
        self.ai = provider_manager or AIProviderManager()
        
    def _safe_json(self, data: Any) -> str:
        try:
            return json.dumps(data, indent=2)
        except Exception:
            return str(data)

    def explain_pose(self, ligand_smiles: str, pose: Dict[str, Any], interactions: List[Dict[str, Any]]) -> AIResponse:
        """Interpret a single docking pose."""
        prompt = f"""{EXPERT_SYSTEM_PROMPT}

TASK: Interpret the following docking pose. Explain the non-covalent interactions (H-bonds, hydrophobic, metal coordination, water bridges) and their contribution to binding.

Ligand SMILES: {ligand_smiles}
Pose Affinity: {pose.get('affinity', 'N/A')} kcal/mol

DETECTED INTERACTIONS (Absolute Truth):
{self._safe_json(interactions)}

Provide a concise, evidence-backed medicinal chemistry summary of this binding mode. Group by interaction type if helpful.
"""
        return self.ai.query(prompt)

    def compare_poses(self, ligand_smiles: str, poses: List[Dict[str, Any]], interactions_dict: Dict[int, List[Dict[str, Any]]]) -> AIResponse:
        """Compare multiple binding modes."""
        
        comparison_data = []
        for p in poses:
            rank = p.get('rank')
            comparison_data.append({
                "Rank": rank,
                "Affinity": p.get('affinity'),
                "Interactions": interactions_dict.get(rank, [])
            })
            
        prompt = f"""{EXPERT_SYSTEM_PROMPT}

TASK: Compare the following {len(poses)} docking poses.

Ligand SMILES: {ligand_smiles}

POSE DATA:
{self._safe_json(comparison_data)}

Analyze the differences in binding modes. 
- Are they flipped/rotated relative to each other? (Infer from differences in interacting residues).
- Why might Pose 1 have a better affinity than the others based strictly on the provided interactions?
- Identify the most conserved interactions across all poses.
"""
        return self.ai.query(prompt)

    def suggest_improvements(self, ligand_smiles: str, pose: Dict[str, Any], interactions: List[Dict[str, Any]]) -> AIResponse:
        """Provide text-based SAR/optimization suggestions based on the best pose."""
        prompt = f"""{EXPERT_SYSTEM_PROMPT}

TASK: Act as a medicinal chemist performing hit-to-lead optimization. Based on the current binding mode, suggest structural modifications to improve affinity or drug-like properties.

Ligand SMILES: {ligand_smiles}
Current Affinity: {pose.get('affinity', 'N/A')} kcal/mol

DETECTED INTERACTIONS:
{self._safe_json(interactions)}

Focus on:
1. Substituent Modifications (e.g., adding halogens for hydrophobic pockets).
2. Bioisosteres for existing groups to improve PK/PD.
3. Optimizing current H-bonds or capturing new ones.

OUTPUT REQUIREMENT:
Provide text-only advice. Do NOT generate modified SMILES strings. Use standard IUPAC or structural descriptions.
"""
        return self.ai.query(prompt)

    def generate_report(self, job_metadata: Dict[str, Any], poses: List[Dict[str, Any]], interactions_dict: Dict[int, List[Dict[str, Any]]]) -> AIResponse:
        """Generate a comprehensive docking report."""
        prompt = f"""{EXPERT_SYSTEM_PROMPT}

TASK: Generate a formal, professional Executive Summary report for this docking run.

METADATA:
{self._safe_json(job_metadata)}

TOP POSE SUMMARY:
Affinity: {poses[0].get('affinity') if poses else 'N/A'} kcal/mol
Interactions: {self._safe_json(interactions_dict.get(poses[0].get('rank') if poses else 1, []))}

Create a Markdown report with the following sections:
# Docking Executive Summary
## 1. System Overview (Receptor & Ligand context)
## 2. Binding Energetics & Quality
## 3. Key Interactions Analysis
## 4. Optimization Outlook

Be highly professional, as if delivering this report to a Lead Investigator.
"""
        return self.ai.query(prompt)
