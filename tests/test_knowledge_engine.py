import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, KnowledgeRule, NotebookEntry, OptimizationDecision
from services.memory_search import SimpleBM25, MemorySearchService
from services.knowledge_miner import KnowledgeMinerService

engine = create_engine('sqlite:///:memory:')
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_bm25_search_scoring():
    corpus = [
        "Kinase inhibitors often struggle with poor aqueous solubility.",
        "The project focused on optimizing the pyridine scaffold.",
        "Scaffold X failed due to hERG liability and toxicity."
    ]
    bm25 = SimpleBM25()
    bm25.fit(corpus)
    
    # Query should highly rank doc 0
    top_hits = bm25.search("solubility issues", top_n=1)
    assert top_hits[0] == 0
    
    # Query should highly rank doc 2
    top_hits_tox = bm25.search("toxicity hERG", top_n=1)
    assert top_hits_tox[0] == 2

def test_calculate_confidence_dynamic(db):
    svc = KnowledgeMinerService(db)
    
    # Volume + Diversity + Consistency = High
    high_conf = svc.calculate_confidence(
        project_ids=["p1", "p2", "p3", "p4"],
        compound_ids=[f"c{i}" for i in range(25)]
    )
    assert high_conf == "High"
    
    # Low diversity and low volume
    low_conf = svc.calculate_confidence(
        project_ids=["p1"],
        compound_ids=["c1", "c2"]
    )
    assert low_conf == "Low"

def test_memory_search_service(db):
    svc = MemorySearchService(db)
    
    # Insert dummy data
    rule = KnowledgeRule(id="kr_1", description="Pyridine replacements worked.", status="Approved")
    db.add(rule)
    
    note = NotebookEntry(id="nt_1", content="Solubility remains a massive problem.")
    db.add(note)
    db.commit()
    
    # Test search
    res = svc.search_organizational_memory("solubility")
    assert len(res["results"]) == 1
    assert res["results"][0]["type"] == "Notebook"
    assert res["results"][0]["id"] == "nt_1"
