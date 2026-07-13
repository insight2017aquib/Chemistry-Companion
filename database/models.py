"""
database/models.py
==================
SQLAlchemy models for Chemistry Companion database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, Float, Boolean, JSON, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class AnalysisResult(Base):
    """Database model for analysis results."""

    __tablename__ = "analysis_results"

    id = Column(String(50), primary_key=True)
    name = Column(String(200))
    smiles = Column(Text)
    inchi = Column(Text)
    iupac = Column(Text)

    # Analysis data
    descriptors = Column(JSON)
    functional_groups = Column(JSON)
    ir_prediction = Column(JSON)
    proton_nmr_prediction = Column(JSON)
    carbon_nmr_prediction = Column(JSON)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String(50))  # For future multi-user support
    tags = Column(JSON)  # User-defined tags

    # File paths
    structure_image_path = Column(String(500))
    export_paths = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "smiles": self.smiles,
            "inchi": self.inchi,
            "iupac": self.iupac,
            "descriptors": self.descriptors,
            "functional_groups": self.functional_groups,
            "ir_prediction": self.ir_prediction,
            "proton_nmr_prediction": self.proton_nmr_prediction,
            "carbon_nmr_prediction": self.carbon_nmr_prediction,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "tags": self.tags or [],
            "structure_image_path": self.structure_image_path,
            "export_paths": self.export_paths or {}
        }


class BatchJob(Base):
    """Database model for batch processing jobs."""

    __tablename__ = "batch_jobs"

    id = Column(String(50), primary_key=True)
    name = Column(String(200))
    description = Column(Text)

    # Job configuration
    molecules = Column(JSON)  # List of molecule inputs
    include_spectra = Column(JSON, default=True)
    save_images = Column(JSON, default=False)
    export_formats = Column(JSON)

    # Status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(JSON)  # Current progress info
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Results
    results = Column(JSON)
    error_message = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(50))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "molecules": self.molecules or [],
            "include_spectra": self.include_spectra,
            "save_images": self.save_images,
            "export_formats": self.export_formats or [],
            "status": self.status,
            "progress": self.progress or {},
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": self.results,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "created_by": self.created_by
        }


class DockingJob(Base):
    """
    Database model for docking workspace jobs (Phase 1+ of Advanced Docking Platform).

    The heavy artifacts (poses, vina output, reports) stay on disk in
    outputs/docking_workspace/<id>/. This table only stores lightweight metadata
    for history, reload, and search.
    """

    __tablename__ = "docking_jobs"

    id = Column(String(50), primary_key=True)          # the job_id / uuid
    name = Column(String(200))                         # user-friendly label
    receptor_name = Column(String(200))
    ligand_smiles = Column(Text)
    ligand_name = Column(String(200))

    # Grid definition
    grid = Column(JSON)                                # {center, size, exhaustiveness, num_modes}

    # Results summary
    best_affinity = Column(String(20))
    num_poses = Column(Integer, default=0)
    status = Column(String(20), default="completed")   # completed, failed, etc.

    # Full paths (for convenience)
    workspace_path = Column(String(500))
    report_path = Column(String(500))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "receptor_name": self.receptor_name,
            "ligand_smiles": self.ligand_smiles,
            "ligand_name": self.ligand_name,
            "grid": self.grid or {},
            "best_affinity": self.best_affinity,
            "num_poses": self.num_poses,
            "status": self.status,
            "workspace_path": self.workspace_path,
            "report_path": self.report_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags or [],
        }


# Database connection
def create_database_engine(database_url: str = "sqlite:///chemistry_companion.db"):
    """Create database engine."""
    return create_engine(database_url, echo=False)


def create_session_factory(engine):
    """Create session factory."""
    return sessionmaker(bind=engine)


def init_database(engine):
    """Initialize database tables."""
    Base.metadata.create_all(engine)


# Global session factory — configured at app startup
_engine = None
SessionLocal = None


def configure_database(database_url: str = "sqlite:///chemistry_companion.db") -> None:
    """Create engine, session factory, tables, then reconcile schema/backfill."""
    global _engine, SessionLocal
    _engine = create_database_engine(database_url)
    SessionLocal = create_session_factory(_engine)
    init_database(_engine)

    # Idempotent schema reconcile + legacy data adoption (see database/migrations.py)
    from database.migrations import run_migrations
    run_migrations(_engine)


def get_db():
    """Get database session (dependency injection for FastAPI)."""
    if SessionLocal is None:
        configure_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Workspace(Base):
    """
    Database model for project-level workspaces.
    Stores metadata, versions, and lightweight state. Heavy blobs (PDB text)
    are saved to the filesystem via WorkspaceManager.
    """
    __tablename__ = "workspaces"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), default="Untitled Workspace")
    module = Column(String(50), default="docking")
    version = Column(Integer, default=1)

    state = Column(JSON)  # Lightweight JSON state (UI toggles, step, etc.)
    file_path = Column(String(500))  # Path to heavy blobs JSON on disk

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "module": self.module,
            "version": self.version,
            "state": self.state or {},
            "file_path": self.file_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class ScreeningWorkspace(Base):
    """
    Database model for Phase 8 Virtual Screening batch jobs.
    Ties into a prepared receptor workspace.
    """
    __tablename__ = "screening_workspaces"

    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50)) # ID of the prepared receptor workspace
    name = Column(String(200), default="Virtual Screen")
    
    # Library and Grid
    library_name = Column(String(200))
    total_ligands = Column(Integer, default=0)
    completed_ligands = Column(Integer, default=0)
    failed_ligands = Column(Integer, default=0)
    
    grid_config = Column(JSON)
    exhaustiveness = Column(Integer, default=8)
    
    status = Column(String(20), default="queued") # queued, running, completed, failed
    progress = Column(JSON)
    metrics = Column(JSON) # e.g. avg affinity, best affinity
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "name": self.name,
            "library_name": self.library_name,
            "total_ligands": self.total_ligands,
            "completed_ligands": self.completed_ligands,
            "failed_ligands": self.failed_ligands,
            "grid_config": self.grid_config or {},
            "exhaustiveness": self.exhaustiveness,
            "status": self.status,
            "progress": self.progress or {},
            "metrics": self.metrics or {},
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "created_at": self.created_at
        }

class ScreeningHit(Base):
    """
    Individual docking result for a screening job.
    """
    __tablename__ = "screening_hits"

    id = Column(String(50), primary_key=True)
    screening_id = Column(String(50))
    
    ligand_name = Column(String(200))
    smiles = Column(Text)
    scaffold_smiles = Column(Text) # For Murcko clustering
    
    best_affinity = Column(String(20)) # Stored as string to handle "N/A" or failed
    affinity_value = Column(Integer) # Optional: stored as float * 100 for easy DB sorting, or just use Float
    
    status = Column(String(20), default="completed")
    error_message = Column(Text)
    
    # Path to the actual output PDBQT pose file in the filesystem
    pose_path = Column(String(500))
    
    # Summary of interactions to avoid running analyzer on every page load
    interactions_summary = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "screening_id": self.screening_id,
            "ligand_name": self.ligand_name,
            "smiles": self.smiles,
            "scaffold_smiles": self.scaffold_smiles,
            "best_affinity": self.best_affinity,
            "status": self.status,
            "error_message": self.error_message,
            "interactions_summary": self.interactions_summary or {}
        }

class ChemicalSeries(Base):
    """
    Medicinal Chemistry Series (Phase 9).
    Groups a set of optimized compounds for a specific target.
    """
    __tablename__ = "chemical_series"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), default="Untitled Series")
    target_name = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "target_name": self.target_name,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

class SeriesCompound(Base):
    """
    Individual compound within a MedChem Series.
    """
    __tablename__ = "series_compounds"

    id = Column(String(50), primary_key=True)
    series_id = Column(String(50))
    
    smiles = Column(Text)
    name = Column(String(200))
    
    # Experimental Data
    activity_type = Column(String(50)) # e.g. "IC50", "Ki", "MIC", "% Inhibition"
    activity_value = Column(Float)
    activity_unit = Column(String(20)) # e.g. "nM", "uM", "%"
    normalized_value = Column(Float)   # e.g. pIC50, calculated automatically
    
    # Computational Data
    docking_affinity = Column(String(20)) # Best docking score
    screening_hit_id = Column(String(50)) # Optional link to a Virtual Screening hit
    
    # RDKit Calculated Properties (MW, LogP, TPSA, HBD, HBA, Rotatable Bonds, Fsp3, SAScore, Lipinski/Veber flags)
    properties = Column(JSON)
    
    # Metadata
    notes = Column(Text)
    tags = Column(JSON) # Array of strings
    
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "series_id": self.series_id,
            "smiles": self.smiles,
            "name": self.name,
            "activity_type": self.activity_type,
            "activity_value": self.activity_value,
            "activity_unit": self.activity_unit,
            "normalized_value": self.normalized_value,
            "docking_affinity": self.docking_affinity,
            "screening_hit_id": self.screening_hit_id,
            "properties": self.properties or {},
            "notes": self.notes,
            "tags": self.tags or [],
            "created_at": self.created_at
        }

# ==========================================
# Phase 11: Lead Optimization Studio
# ==========================================

class Portfolio(Base):
    """
    Groups optimization campaigns. Owned by exactly one ResearchProject
    (Project -> Portfolio is 1:N). Nullable during migration; the legacy
    ProjectPortfolioLink table is retained read-only for backfill only.
    """
    __tablename__ = "portfolios"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), index=True)  # Logical FK -> research_projects.id
    name = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class OptimizationCampaign(Base):
    """A campaign groups multiple series under a specific objective."""
    __tablename__ = "optimization_campaigns"
    id = Column(String(50), primary_key=True)
    portfolio_id = Column(String(50)) # Logical FK
    name = Column(String(200), nullable=False)
    target_profile = Column(Text)
    goal_type = Column(String(100)) # e.g. "CNS Penetrant", "Peripheral"
    mpo_weights = Column(JSON) # User-defined desirability weights
    created_at = Column(DateTime, default=datetime.utcnow)
    
class CampaignSeriesLink(Base):
    """Maps ChemicalSeries to OptimizationCampaigns."""
    __tablename__ = "campaign_series_links"
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(String(50))
    series_id = Column(String(50))
    
class OptimizationDecision(Base):
    """Tracks discrete decisions made on compounds/series."""
    __tablename__ = "optimization_decisions"
    id = Column(String(50), primary_key=True)
    campaign_id = Column(String(50))
    compound_ids = Column(JSON) # List of compound IDs involved
    decision_type = Column(String(50)) # "Promote", "Discard", "Synthesize"
    rationale = Column(Text)
    evidence_data = Column(JSON) # MPO scores, alerts at the time of decision
    date = Column(DateTime, default=datetime.utcnow)

# ==========================================
# Phase 12: Research Operating System
# ==========================================

class ResearchProject(Base):
    """The master entity organizing scientific workflows."""
    __tablename__ = "research_projects"
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    objectives = Column(Text)
    target = Column(String(200))
    status = Column(String(50), default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)

class ProjectPortfolioLink(Base):
    """Maps Portfolios to ResearchProjects."""
    __tablename__ = "project_portfolio_links"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50))
    portfolio_id = Column(String(50))

class NotebookEntry(Base):
    """Chronological ledger of scientific observations."""
    __tablename__ = "notebook_entries"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50))
    entity_type = Column(String(50)) # e.g., "Compound", "Series", "Campaign", "Project"
    entity_id = Column(String(50))
    entry_type = Column(String(50)) # "Observation", "Hypothesis", "Conclusion", "Question", "Action Item", "Meeting Note"
    content = Column(Text, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

class LiteratureReference(Base):
    """Repository for external research."""
    __tablename__ = "literature_references"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50))
    doi = Column(String(100))
    pmid = Column(String(50))
    title = Column(Text)
    authors = Column(Text)
    journal = Column(String(200))
    year = Column(Integer)
    notes = Column(Text)
    date_added = Column(DateTime, default=datetime.utcnow)

class ExperimentRegistry(Base):
    """Formalized tracking of performed experiments and computations."""
    __tablename__ = "experiment_registry"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50))
    experiment_type = Column(String(100)) # e.g., "Docking", "SAR Analysis", "ADMET Prediction"
    target_entity_id = Column(String(50)) # What was tested
    parameters = Column(JSON) # e.g., Docking grid box, filter settings
    results_summary = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)

# ==========================================
# Phase 13: Publication & Thesis Assistant
# ==========================================

class PublicationWorkspace(Base):
    """A workspace compiling resources for a specific manuscript or thesis chapter."""
    __tablename__ = "publication_workspaces"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50))
    title = Column(String(200))
    type = Column(String(50)) # e.g., "Manuscript", "Thesis Chapter", "Weekly Report"
    created_at = Column(DateTime, default=datetime.utcnow)

class PublicationDraft(Base):
    """Stores generated AI manuscripts linked to a specific workspace."""
    __tablename__ = "publication_drafts"
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50))
    title = Column(String(200))
    content_type = Column(String(50)) # "Results", "Discussion", "Methods", "Full"
    content = Column(Text)
    evidence_links = Column(JSON) # Maps text spans back to entity IDs
    status = Column(String(50), default="Draft")
    version = Column(Integer, default=1)
    template_type = Column(String(100), default="Standard") # "ACS", "JMedChem", etc.
    created_at = Column(DateTime, default=datetime.utcnow)

class FigureAsset(Base):
    """Stores generated plots (e.g. SAR heatmaps) using matplotlib."""
    __tablename__ = "figure_assets"
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50))
    title = Column(String(200))
    figure_type = Column(String(100))
    file_path = Column(String(500)) # Path to saved PNG/SVG
    caption = Column(Text)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class TableAsset(Base):
    """Stores generated structured tables."""
    __tablename__ = "table_assets"
    id = Column(String(50), primary_key=True)
    workspace_id = Column(String(50))
    title = Column(String(200))
    table_type = Column(String(100))
    data_payload = Column(JSON)
    caption = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReproducibilityLog(Base):
    """Ledger tracking software versions and environment variables for Methods section generation."""
    __tablename__ = "reproducibility_logs"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50))
    experiment_id = Column(String(50)) # Links to ExperimentRegistry
    software_versions = Column(JSON) # e.g., {"rdkit": "2023.09.1", "vina": "1.2.3", "python": "3.10"}
    environment_snapshot = Column(JSON) # e.g., OS version, hardware
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# Phase 14: Scientific Knowledge Engine
# ==========================================

class KnowledgeRule(Base):
    """
    Stores extracted organizational memory / lessons learned.
    Cross-project by design: project_id is NULL for rules mined across all
    projects, and set only when the user explicitly scopes mining to one project.
    """
    __tablename__ = "knowledge_rules"
    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), index=True)  # NULL == cross-project rule
    description = Column(Text) # The core lesson
    category = Column(String(100)) # e.g., "SAR", "ADMET", "Failure"
    confidence = Column(String(50), default="Low") # Low, Moderate, High
    status = Column(String(50), default="Pending") # Pending, Approved, Rejected
    evidence_payload = Column(JSON) # Links to projects, campaigns, compounds
    provenance = Column(JSON) # Metadata about when/how it was extracted
    version = Column(Integer, default=1)
    is_negative_knowledge = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class RuleContradiction(Base):
    """Flags when two rules conflict for manual review."""
    __tablename__ = "rule_contradictions"
    id = Column(String(50), primary_key=True)
    rule_id_1 = Column(String(50))
    rule_id_2 = Column(String(50))
    description = Column(Text)
    status = Column(String(50), default="Unresolved")
    created_at = Column(DateTime, default=datetime.utcnow)