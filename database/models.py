"""
database/models.py
==================
SQLAlchemy models for Chemistry Companion database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, create_engine
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
    """Create engine, session factory, and tables."""
    global _engine, SessionLocal
    _engine = create_database_engine(database_url)
    SessionLocal = create_session_factory(_engine)
    init_database(_engine)


def get_db():
    """Get database session (dependency injection for FastAPI)."""
    if SessionLocal is None:
        configure_database()

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()