"""
services/ai/scientific_librarian.py
===================================
AI Interface to the Scientific Knowledge Engine.
Answers queries based STRICTLY on retrieved BM25 results.
"""

from services.ai.provider_manager import AIProviderManager
from services.memory_search import MemorySearchService
from sqlalchemy.orm import Session
import json

LIBRARIAN_SYSTEM_PROMPT = """You are the Chemistry Companion Scientific Librarian.
Your job is to answer user queries using ONLY the provided Search Results.

CRITICAL RULES:
1. DO NOT INVENT SCIENTIFIC FACTS. Treat all search results as observed patterns, not universal truths.
2. If the answer is not in the Search Results, state: "I do not have enough organizational memory to answer this."
3. You MUST format your response with the following exact headers:
   - **Answer**: Your narrative response.
   - **Evidence**: Quote or cite the exact IDs (e.g., Notebook ID, Rule ID) from the search results.
   - **Confidence**: Rate the confidence of your answer based on the volume of evidence provided (Low, Moderate, High).
   - **Referenced Projects**: List the project or campaign IDs mentioned in the evidence.
"""

class ScientificLibrarianService:
    def __init__(self, db: Session):
        self.ai = AIProviderManager()
        self.search_service = MemorySearchService(db)

    def ask_question(self, query: str) -> str:
        """
        Executes a BM25 search, feeds the hits to the AI, and returns the formatted answer.
        """
        search_payload = self.search_service.search_organizational_memory(query)
        
        if not search_payload["results"]:
            return "**Answer**: I do not have enough organizational memory to answer this.\n\n**Evidence**: N/A\n\n**Confidence**: N/A\n\n**Referenced Projects**: N/A"
            
        # Format results for the AI context window
        context_str = json.dumps(search_payload["results"], indent=2)
        
        prompt = f"""User Query: {query}

Search Results from Organizational Memory:
{context_str}

Please provide the Answer, Evidence, Confidence, and Referenced Projects based on these results.
"""
        full_prompt = f"{LIBRARIAN_SYSTEM_PROMPT}\n\n{prompt}"
        response = self.ai.query(full_prompt)
        return response.text
