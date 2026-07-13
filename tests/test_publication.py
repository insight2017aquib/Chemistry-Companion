import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, LiteratureReference, ResearchProject, SeriesCompound, CampaignSeriesLink, OptimizationCampaign
from services.publication_service import PublicationService
from services.ai.scientific_writer import ScientificWriterService

# In-memory SQLite for testing
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

def test_acs_citation_formatting(db):
    svc = PublicationService(db)
    
    ref = LiteratureReference(
        id="lit_1", project_id="proj_1", 
        authors="Smith, J.; Doe, A.", 
        title="Novel Kinase Inhibitors", 
        journal="J. Med. Chem.", 
        year=2025
    )
    db.add(ref)
    db.commit()
    
    citations = svc.format_citations("proj_1", style="ACS")
    assert len(citations) == 1
    assert "Smith, J.; Doe, A." in citations[0]["text"]
    assert "Novel Kinase Inhibitors" in citations[0]["text"]
    assert "<b>2025</b>" in citations[0]["text"]

def test_vancouver_citation_formatting(db):
    svc = PublicationService(db)
    
    ref = LiteratureReference(
        id="lit_2", project_id="proj_2", 
        authors="Smith J, Doe A", 
        title="Novel Kinase Inhibitors", 
        journal="J Med Chem", 
        year=2025
    )
    db.add(ref)
    db.commit()
    
    citations = svc.format_citations("proj_2", style="Vancouver")
    assert len(citations) == 1
    assert "1. Smith J, Doe A. Novel Kinase Inhibitors. J Med Chem. 2025;" in citations[0]["text"]

def test_latex_table_escaping(db):
    svc = PublicationService(db)
    
    latex = svc._to_latex(["ID", "Name_With_Underscore"], [["cmp_1", "Test_100%"]])
    assert "\\_" in latex
    assert "\\%" in latex

def test_scientific_writer_enforces_rules():
    # We mock the AI provider since we don't want to make live API calls in tests
    # But we can verify the prompt contains the strict rules
    writer = ScientificWriterService()
    
    # We are just testing the prompt string here
    from services.ai.scientific_writer import WRITER_SYSTEM_PROMPT
    assert "NO HALLUCINATION" in WRITER_SYSTEM_PROMPT
    assert "CITATION REQUIREMENTS" in WRITER_SYSTEM_PROMPT
    assert "[Observed Data]" in WRITER_SYSTEM_PROMPT
