"""
core/models.py
==============
Shared structured result models used across core, spectra, reports, exports, and CLI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


def _convert_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {f.name: _convert_value(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, Mapping):
        return {str(k): _convert_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_convert_value(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if hasattr(value, "todict") and callable(value.todict):
        return value.todict()
    # Handle RDKit Mol objects and other non-serializable objects
    if hasattr(value, '__class__'):
        class_name = value.__class__.__name__
        if 'Mol' in class_name or 'ROMol' in class_name:
            return f"<RDKit {class_name} object - not serializable>"
        # For other objects, try to convert to string
        try:
            return str(value)
        except:
            return f"<{class_name} object - not serializable>"
    return value


class ModelMixin:
    """Shared compatibility helpers for structured models."""

    def to_dict(self) -> dict[str, Any]:
        if is_dataclass(self):
            return {f.name: _convert_value(getattr(self, f.name)) for f in fields(self)}
        return dict(vars(self))

    def todict(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(slots=True)
class MoleculeRecord(ModelMixin):
    """Structured container for a parsed and characterized molecule."""

    smiles: str
    inchi: str | None = None
    inchikey: str | None = None
    name: str | None = None
    formula: str | None = None
    mol_weight: float | None = None
    exact_mass: float | None = None
    atom_counts: dict[str, int] = field(default_factory=dict)
    num_atoms: int | None = None
    num_heavy_atoms: int | None = None
    num_bonds: int | None = None
    num_rings: int | None = None
    is_aromatic: bool | None = None
    rdkit_mol: Any | None = None


@dataclass(slots=True)
class DescriptorRecord(ModelMixin):
    """Structured container for molecular descriptors and functional groups."""

    molecular_weight: float | None = None
    exact_mass: float | None = None
    formula: str | None = None
    logp: float | None = None
    tpsa: float | None = None
    hbd: int | None = None
    hba: int | None = None
    rotatable_bonds: int | None = None
    ring_count: int | None = None
    heavy_atom_count: int | None = None
    formal_charge: int | None = None
    fraction_csp3: float | None = None
    functional_groups: dict[str, int] = field(default_factory=dict)
    bertz_ct: float | None = None

    def has_group(self, key: str) -> bool:
        return self.functional_groups.get(key, 0) > 0

    hasgroup = has_group

    @property
    def legacy_flags(self) -> dict[str, bool]:
        return {f"has_{k}": v > 0 for k, v in self.functional_groups.items()}

    @property
    def ro5_pass(self) -> bool:
        if self.molecular_weight is None or self.logp is None or self.hbd is None or self.hba is None:
            return False
        return (
            self.molecular_weight <= 500
            and self.logp <= 5
            and self.hbd <= 5
            and self.hba <= 10
        )

    @property
    def ro5_violations(self) -> int:
        violations = 0
        if self.molecular_weight is not None and self.molecular_weight > 500:
            violations += 1
        if self.logp is not None and self.logp > 5:
            violations += 1
        if self.hbd is not None and self.hbd > 5:
            violations += 1
        if self.hba is not None and self.hba > 10:
            violations += 1
        return violations

    @property
    def ro5_details(self) -> dict[str, dict[str, Any]]:
        return {
            "Molecular weight": {
                "value": self.molecular_weight,
                "threshold": 500,
                "pass": self.molecular_weight is not None and self.molecular_weight <= 500,
            },
            "LogP": {
                "value": self.logp,
                "threshold": 5,
                "pass": self.logp is not None and self.logp <= 5,
            },
            "HBD": {
                "value": self.hbd,
                "threshold": 5,
                "pass": self.hbd is not None and self.hbd <= 5,
            },
            "HBA": {
                "value": self.hba,
                "threshold": 10,
                "pass": self.hba is not None and self.hba <= 10,
            },
        }

    @property
    def lipinski_pass(self) -> bool:
        return self.ro5_pass

    @property
    def lipinski_violations(self) -> int:
        return self.ro5_violations

    def __getattr__(self, name: str) -> Any:
        if name.startswith("has"):
            normalized = name[3:].lstrip("_").replace("_", "").lower()
            alias_map = {
                "hydroxyl": "alcohol",
                "primaryamine": "amine",
                "secondaryamine": "amine",
                "tertiaryamine": "amine",
                "aromaticring": "aromatic_ring",
                "carboxylicacid": "carboxylic_acid",
            }
            for key, value in self.functional_groups.items():
                if key.replace("_", "").lower() == normalized:
                    return value > 0
            if normalized in alias_map:
                alias = alias_map[normalized]
                return self.functional_groups.get(alias, 0) > 0
        raise AttributeError(name)


@dataclass(slots=True)
class FunctionalGroupMatch(ModelMixin):
    key: str
    name: str
    atom_indices: tuple[tuple[int, ...], ...] = field(default_factory=tuple)
    count: int = 1
    category: str | None = None
    ir_bands: tuple[tuple[str, int, int], ...] = field(default_factory=tuple)


@dataclass(slots=True)
class FunctionalGroupReport(ModelMixin):
    """Complete functional group analysis for one molecule."""

    smiles: str | None = None
    counts: dict[str, int] = field(default_factory=dict)
    matches: list[FunctionalGroupMatch] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    failed_patterns: list[str] = field(default_factory=list)
    summary_text: str = ""

    def has(self, key: str) -> bool:
        return self.counts.get(key, 0) > 0

    def get(self, key: str, default=None):
        group_matches = [match for match in self.matches if match.key == key]
        if not group_matches:
            return default

        if len(group_matches) == 1:
            return group_matches[0]

        return FunctionalGroupMatch(
            key=key,
            name=group_matches[0].name,
            atom_indices=tuple(idx for match in group_matches for idx in match.atom_indices),
            count=sum(match.count for match in group_matches),
            category=group_matches[0].category,
            ir_bands=group_matches[0].ir_bands,
        )

    @property
    def by_category(self) -> dict[str, list[FunctionalGroupMatch]]:
        grouped: dict[str, list[FunctionalGroupMatch]] = {}
        for match in self.matches:
            cat = match.category or "unknown"
            grouped.setdefault(cat, []).append(match)
        return grouped

    @property
    def total_groups(self) -> int:
        return len(self.matches)

    def summary(self) -> str:
        return self.summary_text


@dataclass(slots=True)
class IRBand(ModelMixin):
    label: str
    lower_cm1: int | None = None
    upper_cm1: int | None = None
    intensity: str | None = None
    confidence: float | None = None


@dataclass(slots=True)
class IRPrediction(ModelMixin):
    """Full heuristic IR prediction for one molecule."""

    bands: list[IRBand] = field(default_factory=list)
    summary_text: str = ""

    @property
    def peaks(self) -> list[IRBand]:
        return self.bands

    def to_legacy_dict(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(slots=True)
class ProtonSignal(ModelMixin):
    shift_ppm: float | None = None
    multiplicity: str | None = None
    integration: float | None = None
    label: str | None = None
    atom_indices: list[int] = field(default_factory=list)
    notes: str | None = None


@dataclass(slots=True)
class ProtonNMRPrediction(ModelMixin):
    """Top-level heuristic 1H NMR prediction result."""

    signals: list[ProtonSignal] = field(default_factory=list)
    summary_text: str = ""

    def to_legacy_dict(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(slots=True)
class CarbonEnvironment(ModelMixin):
    shift_ppm: float | None = None
    ppm_range: tuple[float, float] | None = None
    label: str | None = None
    atom_indices: list[int] = field(default_factory=list)
    carbon_count: int = 1
    attached_elements: list[str] = field(default_factory=list)
    attached_hydrogens: int | None = None
    is_quaternary: bool | None = None
    carbonyl_type: str | None = None
    heterocycle_family: str | None = None
    hetero_position: str | None = None

    def features_dict(self) -> dict[str, Any]:
        return self.to_dict()

    featuresdict = features_dict


@dataclass(slots=True)
class CarbonNMRPrediction(ModelMixin):
    """Top-level heuristic 13C NMR prediction result."""

    environments: list[CarbonEnvironment] = field(default_factory=list)
    total_carbons: int | None = None
    n_signals: int | None = None
    summary_text: str = ""

    @property
    def atom_environments(self) -> list[CarbonEnvironment]:
        return self.environments

    atomenvironments = atom_environments

    def summary(self) -> str:
        return self.summary_text

    def to_legacy_dict(self) -> dict[str, Any]:
        return self.to_dict()


@dataclass(slots=True)
class AnalysisResult(ModelMixin):
    """Structured result returned by the chemistry pipeline."""

    molecule: MoleculeRecord
    descriptors: DescriptorRecord
    descriptor_summary: str
    functional_groups: dict[str, int] = field(default_factory=dict)
    functional_group_report: FunctionalGroupReport | None = None
    ir_prediction: IRPrediction | None = None
    proton_nmr_prediction: ProtonNMRPrediction | None = None
    carbon_nmr_prediction: CarbonNMRPrediction | None = None
    visualization_path: Path | None = None
    export_row: dict[str, Any] | None = None
    export_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)