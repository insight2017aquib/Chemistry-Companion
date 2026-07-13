"""
services/ai/scientific_writer.py
================================
AI Scientific Writer for drafting Manuscripts.
Strictly enforced evidence linking to prevent generation of unsupported conclusions.
"""

from services.ai.provider_manager import AIProviderManager

WRITER_SYSTEM_PROMPT = """You are an academic Scientific Writer assisting in drafting manuscripts and thesis chapters.

CRITICAL RULES FOR EVIDENCE LINKING:
1. NO HALLUCINATION: You must NEVER invent data, experimental conditions, or outcomes.
2. CITATION REQUIREMENTS: Every factual statement regarding activity or properties MUST explicitly reference a Compound ID (e.g., "Compound cmp_123 demonstrated a pIC50 of 7.2").
3. SEPARATION OF CONCERNS: Clearly separate your text into three distinct areas: [Observed Data], [Derived Analysis], and [AI Interpretation].
4. ADVISORY TONE: Use phrases like "Based on the recorded ADMET heuristics..." or "The dataset indicates...". Do not use definitive language like "This proves...".
5. DRAFT STATUS: Frame your output as a preliminary draft intended for human review.
6. Format your output in clean Markdown.
"""

class ScientificWriterService:
    def __init__(self):
        self.ai = AIProviderManager()

    def draft_results_section(self, campaign_name: str, compounds_data: list) -> str:
        """
        Drafts a Results section based on the Top Compounds in a Campaign.
        """
        prompt = f"""Draft a formal 'Results' section for a manuscript describing the Optimization Campaign '{campaign_name}'.

Here is the raw data for the synthesized/evaluated compounds:
{compounds_data}

Tasks:
1. Describe the Structure-Activity Relationship (SAR) trends observed in the data.
2. Highlight the most potent compound, strictly citing its ID and pIC50.
3. Discuss the Multi-Parameter Optimization (MPO) and ADMET profile of the lead candidate compared to the rest of the series.
4. Ensure every numerical claim is backed by the provided JSON data.
"""
        full_prompt = f"{WRITER_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def draft_methods_section(self, reproducibility_data: dict) -> str:
        """
        Drafts a Methods section based on ReproducibilityLogs.
        """
        prompt = f"""Draft a formal 'Materials and Methods' paragraph regarding the computational protocols used in this study.

Here is the Reproducibility Package (Software versions and parameters):
{reproducibility_data}

Tasks:
1. Write a narrative paragraph detailing the software used (include specific version numbers provided).
2. Detail the exact parameters used (e.g., grid box coordinates, exhaustiveness).
3. Do not invent any missing parameters. If grid box size is missing, state "Standard parameters were utilized."
"""
        full_prompt = f"{WRITER_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text

    def generate_figure_caption(self, figure_type: str, context_data: str) -> str:
        """
        Generates a formal academic caption for a figure.
        """
        prompt = f"""Write a concise, formal academic caption for a {figure_type}.

Context Data depicted in the figure:
{context_data}

Tasks:
1. Start with a bold title fragment (e.g., **Figure 1. Structure-Activity Relationship Trends.**).
2. Describe what the axes or colors represent.
3. Briefly mention the key takeaway without overstating the conclusion.
"""
        full_prompt = f"{WRITER_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
        
    def generate_table_caption(self, table_title: str, context_data: str) -> str:
        """
        Generates a formal academic caption for a table.
        """
        prompt = f"""Write a concise, formal academic caption for a table titled '{table_title}'.

Context Data depicted in the table:
{context_data}

Tasks:
1. Start with a bold title fragment (e.g., **Table 1. {table_title}.**).
2. Note any standard deviations or units applicable to the columns (e.g., IC50 in nM).
3. Do not draw exhaustive conclusions; merely describe what the data is.
"""
        full_prompt = f"{WRITER_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
