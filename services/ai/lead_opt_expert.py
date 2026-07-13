"""
services/ai/lead_opt_expert.py
==============================
AI Expert for Lead Optimization.
Analyzes MPO tradeoffs and evaluates hypothetical structural changes (What-If analysis).
"""

from services.ai.provider_manager import AIProviderManager

LEAD_OPT_SYSTEM_PROMPT = """You are a Lead Optimization Decision Scientist.
Your role is to analyze Multi-Parameter Optimization (MPO) scores and physicochemical tradeoffs to help researchers prioritize compounds for synthesis or progression.

CRITICAL RULES:
1. NO SPECULATIVE CERTAINTY: Never guarantee experimental outcomes. Use phrases like "Based on MPO scoring...", "The data suggests...", or "This structural change typically results in...".
2. EVIDENCE-BASED: Base your ranking explanations strictly on the MPO scores, experimental data, and ADMET liabilities provided.
3. TRADEOFF ANALYSIS: Explicitly highlight tradeoffs (e.g., "Compound X is more potent, but Compound Y has a superior developability profile without PAINS alerts").
4. WHAT-IF ANALYSIS: When evaluating a hypothetical structural change, estimate the directional impact on MPO parameters (e.g., "Adding a fluorine will likely increase LogP, which may negatively impact the ADMET safety score").
5. Format your output in clean Markdown.
"""

class LeadOptExpertService:
    def __init__(self):
        self.ai = AIProviderManager()

    def prioritize_leads(self, campaign_name: str, compounds_data: list) -> str:
        """
        Analyzes the top compounds and explains the ranking logic based on MPO scores.
        """
        prompt = f"""Evaluate the prioritized lead candidates for the Optimization Campaign '{campaign_name}'.

Here is the data for the top candidates (including MPO scores, Potency, and ADMET alerts):
{compounds_data}

Tasks:
1. Explain the rationale behind the current ranking. Why is the top compound ranked #1?
2. Perform a Tradeoff Analysis between the top 2-3 compounds. What does the highest ranked compound sacrifice (if anything) compared to the runners-up?
3. Summarize the overall health of the campaign (e.g., "Potency is acceptable, but ADMET liabilities remain a systemic issue").
"""
        full_prompt = f"{LEAD_OPT_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def what_if_analysis(self, compound_data: dict, hypothesis: str) -> str:
        """
        Evaluates a hypothetical structural modification.
        """
        prompt = f"""Perform a "What-If" Analysis on the following compound based on a proposed structural hypothesis.

Current Compound Data:
{compound_data}

Proposed Hypothesis / Modification:
"{hypothesis}"

Tasks:
1. Evaluate the likely directional impact of this modification on physicochemical properties (MW, LogP, TPSA).
2. Discuss the potential impact on the MPO scores (Pfizer CNS / Generic).
3. Identify any new ADMET liabilities this modification might introduce (e.g., "Adding an amine may introduce a hERG liability").
"""
        full_prompt = f"{LEAD_OPT_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
