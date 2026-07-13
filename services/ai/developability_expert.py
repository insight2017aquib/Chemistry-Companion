"""
services/ai/developability_expert.py
====================================
AI Expert for analyzing ADMET liabilities and suggesting developability optimizations.
"""

from services.ai.provider_manager import AIProviderManager

DEVELOPABILITY_SYSTEM_PROMPT = """You are an expert Pharmaceutical Developability Scientist.
Your role is to assess ADMET risks and drug-likeness for lead optimization.

CRITICAL RULES:
1. DISTINGUISH CONFIDENCE: Clearly separate OBSERVED experimental data from PREDICTED heuristics and HYPOTHETICAL suggestions.
2. ADVISORY ONLY: Never present predicted toxicities (e.g. hERG, PAINS) as experimental facts. Frame them as "Calculated Risks" or "Structural Alerts".
3. NO HALLUCINATION: Do not invent missing property values. If LogP is not provided, do not guess it.
4. OPTIMIZATION TARGETS: When suggesting improvements, provide specific physicochemical targets (e.g., "Reduce LogP below 3.0 to mitigate hERG liability").
5. Format your output in clean Markdown. Use bullet points for readability.
"""

class DevelopabilityExpertService:
    def __init__(self):
        self.ai = AIProviderManager()

    def analyze_series_liabilities(self, series_name: str, compounds_data: list) -> str:
        """
        Analyzes the aggregate liabilities of a chemical series.
        """
        prompt = f"""Analyze the developability profile for the Chemical Series '{series_name}'.
        
Here is a summary of the compounds and their ADMET alerts:
{compounds_data}

Tasks:
1. Summarize the major ADMET liabilities (e.g., consistent hERG alerts, high MW).
2. Differentiate between observed experimental activity and the predicted heuristic risks.
3. Suggest 2-3 optimization goals for the next design iteration to improve the developability score.
"""
        full_prompt = f"{DEVELOPABILITY_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def suggest_optimization_targets(self, compound_data: dict) -> str:
        """
        Focuses deeply on a single compound's liability profile and suggests modifications.
        """
        prompt = f"""Review the following compound's ADMET and physicochemical profile:
{compound_data}

Tasks:
1. State the most critical developability liability.
2. Provide a HYPOTHETICAL structural modification that could address this liability.
3. Explain the physicochemical reasoning (e.g. "Exchanging the phenyl for a pyridine lowers LogP, which may reduce hERG binding").
"""
        full_prompt = f"{DEVELOPABILITY_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
