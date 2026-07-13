"""
services/ai/research_assistant.py
=================================
AI Assistant for the Research OS.
Summarizes Knowledge Graph data and extracts Lessons Learned without inventing history.
"""

import json
from services.ai.provider_manager import AIProviderManager

RESEARCH_SYSTEM_PROMPT = """You are the Principal Investigator AI for the Chemistry Companion Research OS.
Your role is to synthesize complex, multi-layered scientific data into coherent summaries and insights.

CRITICAL RULES:
1. STRICT ADHERENCE TO HISTORY: Do not invent, hallucinate, or assume any events, experiments, or decisions that are not explicitly provided in the data.
2. SYNTHESIS, NOT FICTION: When summarizing a project, stick only to the provided Notebook Entries, Decisions, and Experiments.
3. EXTRACT LESSONS: When reviewing hypotheses against decisions, explicitly call out what the data proved or disproved.
4. Format your output in clean Markdown.
"""

class ResearchAssistantService:
    def __init__(self):
        self.ai = AIProviderManager()

    def summarize_project(self, project_name: str, timeline_events: list) -> str:
        """
        Reads the chronological timeline of a project and writes an executive summary.
        """
        prompt = f"""Write an Executive Summary for the Research Project '{project_name}'.

Here is the chronological ledger of all scientific events (Notebook entries and Decisions) in this project:
{json.dumps(timeline_events, indent=2, default=str)}

Tasks:
1. Provide a high-level summary of the project's journey from the earliest entry to the most recent.
2. Highlight the major pivot points or critical decisions made.
3. Conclude with the current status of the project based strictly on the final entries.
Do NOT invent any data or outcomes.
"""
        full_prompt = f"{RESEARCH_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def extract_lessons_learned(self, project_name: str, timeline_events: list) -> str:
        """
        Analyzes the timeline specifically to find resolved hypotheses.
        """
        prompt = f"""Perform a 'Lessons Learned' analysis for the Research Project '{project_name}'.

Here is the chronological ledger of all scientific events:
{json.dumps(timeline_events, indent=2, default=str)}

Tasks:
1. Identify specific "Hypotheses" or "Questions" posed early in the notebook.
2. Trace those hypotheses to later "Decisions", "Conclusions", or "Observations".
3. Write a bulleted list of "Lessons Learned" (e.g., "Hypothesis X was proven false because Decision Y discarded the series due to poor permeability").
If there are no clear resolutions, state that the hypotheses remain untested.
"""
        full_prompt = f"{RESEARCH_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
