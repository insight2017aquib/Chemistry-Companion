"""
services/memory_search.py
=========================
Local BM25/Inverted-Index search over organizational memory.
Maintains lightweight SQLite footprint without vector DBs.
"""

import re
import math
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from database.models import KnowledgeRule, NotebookEntry, OptimizationDecision, ResearchProject

class SimpleBM25:
    """A lightweight BM25 implementation for text search."""
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.documents = []
        self.doc_freqs = []
        self.idf = {}
        self.doc_len = []
        self.avgdl = 0

    def fit(self, corpus: List[str]):
        self.documents = corpus
        self.doc_len = [len(self._tokenize(doc)) for doc in corpus]
        self.avgdl = sum(self.doc_len) / len(self.doc_len) if self.doc_len else 1
        
        df = {}
        for doc in corpus:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                df[token] = df.get(token, 0) + 1
                
        num_docs = len(corpus)
        for token, freq in df.items():
            self.idf[token] = math.log(1 + (num_docs - freq + 0.5) / (freq + 0.5))
            
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())
        
    def search(self, query: str, top_n: int = 5) -> List[int]:
        query_tokens = self._tokenize(query)
        scores = []
        
        for idx, doc in enumerate(self.documents):
            score = 0
            doc_tokens = self._tokenize(doc)
            for token in query_tokens:
                if token not in self.idf:
                    continue
                tf = doc_tokens.count(token)
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1 - self.b + self.b * self.doc_len[idx] / self.avgdl)
                score += self.idf[token] * (num / den)
            scores.append((idx, score))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, score in scores[:top_n] if score > 0]

class MemorySearchService:
    def __init__(self, db: Session):
        self.db = db

    def search_organizational_memory(self, query: str) -> Dict[str, Any]:
        """
        Gathers all text from Notebooks, Decisions, and KnowledgeRules.
        Uses BM25 to rank the top hits.
        """
        # 1. Gather Corpus
        rules = self.db.query(KnowledgeRule).filter(KnowledgeRule.status == "Approved").all()
        notes = self.db.query(NotebookEntry).all()
        decisions = self.db.query(OptimizationDecision).all()
        
        corpus = []
        mapping = []
        
        for r in rules:
            corpus.append(r.description or "")
            mapping.append({"type": "Rule", "id": r.id, "text": r.description})
            
        for n in notes:
            corpus.append(n.content or "")
            mapping.append({"type": "Notebook", "id": n.id, "text": n.content})
            
        for d in decisions:
            corpus.append(d.rationale or "")
            mapping.append({"type": "Decision", "id": d.id, "text": d.rationale})
            
        if not corpus:
            return {"query": query, "results": []}
            
        # 2. Search
        bm25 = SimpleBM25()
        bm25.fit(corpus)
        top_indices = bm25.search(query, top_n=10)
        
        results = [mapping[i] for i in top_indices]
        return {"query": query, "results": results}
