"""
core/pams/models.py
===================
Protein Asset Management System (PAMS) — domain model.

Every protein that enters Chemistry Companion — uploaded, fetched from RCSB,
predicted by AlphaFold, or loaded from disk — becomes a single domain object: a
``ProteinAsset``. Docking, visualization, analysis, and future AI services all
consume this object through a stable, provider-agnostic, versioned contract.

Design rules honored here:
  * Pure domain: NO I/O, NO network, NO docking imports. (Testable in isolation.)
  * Extensible-by-composition: derived files live in a generic ``artifacts`` list
    and overlays in a generic ``annotations`` list, so new lifecycle stages attach
    data instead of forcing a schema change.
  * AI-ready: ``to_ai_context()`` is the stable projection every AI module reads.
  * Forward-compatible: ``schema_version`` on the asset and on the metadata.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

# Bump when the serialized shape changes in a way consumers must notice.
ASSET_SCHEMA_VERSION = 1
METADATA_SCHEMA_VERSION = 1


def _now() -> float:
    return time.time()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums (stored as their string values for stable serialization)
# ---------------------------------------------------------------------------

class Origin(str, Enum):
    UPLOAD = "upload"
    FETCH = "fetch"
    LOCAL = "local"


class LifecycleStage(str, Enum):
    """Ordered stages an asset moves through. Search→…→Reports."""
    DISCOVERED = "discovered"        # known by id, not yet downloaded
    DOWNLOADED = "downloaded"        # structure bytes present
    VALIDATED = "validated"          # parsed/sanity-checked
    ANALYZED = "analyzed"            # chains/ligands/metadata computed
    PREPARED = "prepared"            # receptor preparation complete
    DOCKING_READY = "docking_ready"  # PDBQT artifact present
    DOCKED = "docked"                # at least one docking job run
    POSE_ANALYZED = "pose_analyzed"  # interactions/rmsd computed
    REPORTED = "reported"            # a report has been generated


class PreparationStep(str, Enum):
    VALIDATED = "validated"
    HYDROGENS_ADDED = "hydrogens_added"
    WATERS_REMOVED = "waters_removed"
    LIGAND_REMOVED = "ligand_removed"
    CHARGES_ASSIGNED = "charges_assigned"
    PDBQT_GENERATED = "pdbqt_generated"


class StepStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class PreparationStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY = "ready"
    FAILED = "failed"


# Artifact kinds are intentionally open strings (not an enum) so new derived
# outputs never require a code change. These constants document the common ones.
class ArtifactKind:
    SOURCE_STRUCTURE = "source_structure"     # the fetched/uploaded original (PDB)
    SOURCE_STRUCTURE_CIF = "source_structure_cif"
    PREPARED_STRUCTURE = "prepared_structure"  # cleaned receptor PDB
    RECEPTOR_PDBQT = "receptor_pdbqt"          # docking-ready receptor
    SURFACE = "surface"                        # cached surface mesh (future viewer)
    THUMBNAIL = "thumbnail"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass
class ChainSummary:
    chain_id: str
    num_residues: int = 0
    num_standard_aa: int = 0
    is_protein: bool = False
    first_resnum: Optional[int] = None
    last_resnum: Optional[int] = None


@dataclass
class LigandSummary:
    resname: str
    chain_id: str = ""
    resnum: int = 0
    num_atoms: int = 0
    centroid: Optional[Dict[str, float]] = None
    role: Optional[str] = None   # e.g. "cocrystal", "cofactor" (annotated later)


@dataclass
class PocketSummary:
    """Empty until pocket detection runs; a future stage attaches these."""
    pocket_id: str
    score: Optional[float] = None
    center: Optional[Dict[str, float]] = None
    radius: Optional[float] = None
    residues: List[str] = field(default_factory=list)
    druggability: Optional[float] = None
    source: Optional[str] = None   # "fpocket", "cocrystal", "ai", ...


@dataclass
class LiteratureRef:
    title: str = ""
    identifier: str = ""   # PMID / DOI
    url: str = ""


@dataclass
class StructureMetadata:
    """Normalized, provider-agnostic metadata. Vendor payloads are quarantined
    in ``raw``. This is the contract AI services and the UI both read."""
    title: Optional[str] = None
    resolution: Optional[float] = None
    method: Optional[str] = None
    organism: Optional[str] = None
    deposited_date: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    chains: List[ChainSummary] = field(default_factory=list)
    ligands: List[LigandSummary] = field(default_factory=list)
    pockets: List[PocketSummary] = field(default_factory=list)
    sequence: Optional[str] = None
    function: Optional[str] = None                      # free-text biological function
    literature_refs: List[LiteratureRef] = field(default_factory=list)
    source_url: Optional[str] = None
    license: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)   # provider-native payload
    schema_version: int = METADATA_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Artifact:
    """A derived file/blob attached to an asset (structure, prepared receptor,
    PDBQT, surface mesh, thumbnail, ...). Referenced by ``ref`` (a store key)."""
    kind: str
    ref: str
    format: str = ""
    checksum: Optional[str] = None
    produced_by: str = ""            # "rcsb", "preparation", "docking", ...
    created_at: float = field(default_factory=_now)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Annotation:
    """A viewer/AI overlay attached to an asset (residue highlight, pocket,
    measurement, AI note). Open ``kind``/``producer`` so new overlay types need
    no schema change."""
    kind: str
    producer: str
    selection: Dict[str, Any] = field(default_factory=dict)   # {"chain":"A","resnums":[45]}
    label: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)        # color/text/distance/...
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PreparationState:
    """Receptor preparation modeled as a pipeline, not a button."""
    status: str = PreparationStatus.NOT_STARTED.value
    steps: List[Dict[str, Any]] = field(default_factory=list)   # [{step,status,detail,at}]
    options: Dict[str, Any] = field(default_factory=dict)
    docking_ready: bool = False
    prepared_artifact_kind: Optional[str] = None               # points into artifacts

    def record_step(self, step: str, status: str, detail: str = "") -> None:
        self.steps.append({"step": step, "status": status, "detail": detail, "at": _now()})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Provenance:
    origin: str
    provider: Optional[str] = None       # "rcsb","alphafold",... ; None for upload
    provider_ref: Optional[str] = None   # "4DUH","P0DTD1",...
    source_url: Optional[str] = None
    fetched_at: float = field(default_factory=_now)
    requested_by: Optional[str] = None   # user id (multi-tenant future)
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Aggregate root
# ---------------------------------------------------------------------------

@dataclass
class ProteinAsset:
    name: str
    origin: str
    asset_id: str = field(default_factory=_new_id)
    provider: Optional[str] = None
    provider_ref: Optional[str] = None
    primary_format: str = "pdb"
    checksum: Optional[str] = None
    lifecycle_stage: str = LifecycleStage.DISCOVERED.value
    metadata: StructureMetadata = field(default_factory=StructureMetadata)
    preparation: PreparationState = field(default_factory=PreparationState)
    artifacts: List[Artifact] = field(default_factory=list)
    annotations: List[Annotation] = field(default_factory=list)
    provenance: Optional[Provenance] = None
    # Future project/collection ownership — nullable so projects adopt assets later.
    project_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    collection_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    schema_version: int = ASSET_SCHEMA_VERSION

    # -- helpers --------------------------------------------------------------
    def touch(self) -> None:
        self.updated_at = _now()

    def get_artifact(self, kind: str) -> Optional[Artifact]:
        for a in self.artifacts:
            if a.kind == kind:
                return a
        return None

    def add_artifact(self, artifact: Artifact) -> Artifact:
        # Replace an existing artifact of the same kind (idempotent stages).
        self.artifacts = [a for a in self.artifacts if a.kind != artifact.kind]
        self.artifacts.append(artifact)
        self.touch()
        return artifact

    def add_annotation(self, annotation: Annotation) -> Annotation:
        self.annotations.append(annotation)
        self.touch()
        return annotation

    def advance_stage(self, stage: LifecycleStage | str) -> None:
        self.lifecycle_stage = stage.value if isinstance(stage, LifecycleStage) else stage
        self.touch()

    # -- serialization --------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "origin": self.origin,
            "provider": self.provider,
            "provider_ref": self.provider_ref,
            "primary_format": self.primary_format,
            "checksum": self.checksum,
            "lifecycle_stage": self.lifecycle_stage,
            "metadata": self.metadata.to_dict(),
            "preparation": self.preparation.to_dict(),
            "artifacts": [a.to_dict() for a in self.artifacts],
            "annotations": [a.to_dict() for a in self.annotations],
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "project_id": self.project_id,
            "tags": list(self.tags),
            "collection_ids": list(self.collection_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProteinAsset":
        md = d.get("metadata", {}) or {}
        metadata = StructureMetadata(
            title=md.get("title"),
            resolution=md.get("resolution"),
            method=md.get("method"),
            organism=md.get("organism"),
            deposited_date=md.get("deposited_date"),
            keywords=md.get("keywords", []) or [],
            chains=[ChainSummary(**c) for c in md.get("chains", []) or []],
            ligands=[LigandSummary(**l) for l in md.get("ligands", []) or []],
            pockets=[PocketSummary(**p) for p in md.get("pockets", []) or []],
            sequence=md.get("sequence"),
            function=md.get("function"),
            literature_refs=[LiteratureRef(**r) for r in md.get("literature_refs", []) or []],
            source_url=md.get("source_url"),
            license=md.get("license"),
            raw=md.get("raw", {}) or {},
            schema_version=md.get("schema_version", METADATA_SCHEMA_VERSION),
        )
        prep_d = d.get("preparation", {}) or {}
        preparation = PreparationState(
            status=prep_d.get("status", PreparationStatus.NOT_STARTED.value),
            steps=prep_d.get("steps", []) or [],
            options=prep_d.get("options", {}) or {},
            docking_ready=prep_d.get("docking_ready", False),
            prepared_artifact_kind=prep_d.get("prepared_artifact_kind"),
        )
        prov_d = d.get("provenance")
        provenance = Provenance(**prov_d) if prov_d else None

        return cls(
            name=d["name"],
            origin=d["origin"],
            asset_id=d.get("asset_id", _new_id()),
            provider=d.get("provider"),
            provider_ref=d.get("provider_ref"),
            primary_format=d.get("primary_format", "pdb"),
            checksum=d.get("checksum"),
            lifecycle_stage=d.get("lifecycle_stage", LifecycleStage.DISCOVERED.value),
            metadata=metadata,
            preparation=preparation,
            artifacts=[Artifact(**a) for a in d.get("artifacts", []) or []],
            annotations=[Annotation(**a) for a in d.get("annotations", []) or []],
            provenance=provenance,
            project_id=d.get("project_id"),
            tags=d.get("tags", []) or [],
            collection_ids=d.get("collection_ids", []) or [],
            created_at=d.get("created_at", _now()),
            updated_at=d.get("updated_at", _now()),
            schema_version=d.get("schema_version", ASSET_SCHEMA_VERSION),
        )

    def to_ai_context(self) -> Dict[str, Any]:
        """Stable, versioned projection every AI module consumes (summarization,
        chat, residue/pocket/ligand/function explanation, docking/target
        recommendation). Deliberately excludes internal store refs and raw
        vendor payloads."""
        md = self.metadata
        return {
            "schema_version": self.schema_version,
            "asset_id": self.asset_id,
            "name": self.name,
            "identity": {
                "provider": self.provider,
                "provider_ref": self.provider_ref,
                "origin": self.origin,
            },
            "structure": {
                "title": md.title,
                "method": md.method,
                "resolution": md.resolution,
                "organism": md.organism,
                "deposited_date": md.deposited_date,
                "keywords": md.keywords,
            },
            "chains": [asdict(c) for c in md.chains],
            "ligands": [asdict(l) for l in md.ligands],
            "pockets": [asdict(p) for p in md.pockets],
            "sequence": md.sequence,
            "function": md.function,
            "literature": [asdict(r) for r in md.literature_refs],
            "lifecycle_stage": self.lifecycle_stage,
            "preparation": {
                "status": self.preparation.status,
                "docking_ready": self.preparation.docking_ready,
            },
            "annotations": [a.to_dict() for a in self.annotations],
        }


__all__ = [
    "ASSET_SCHEMA_VERSION", "METADATA_SCHEMA_VERSION",
    "Origin", "LifecycleStage", "PreparationStep", "StepStatus", "PreparationStatus",
    "ArtifactKind",
    "ChainSummary", "LigandSummary", "PocketSummary", "LiteratureRef",
    "StructureMetadata", "Artifact", "Annotation", "PreparationState", "Provenance",
    "ProteinAsset",
]
