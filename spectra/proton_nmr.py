"""
chemistry_companion/spectra/proton_nmr.py
=========================================
Production-ready heuristic 1H NMR predictor for Chemistry Companion.

IMPORTANT
---------
All predictions in this module are APPROXIMATE HEURISTICS only.
This module does not provide experimental, DFT, or ML-calibrated accuracy.
Use these outputs for rough annotation and educational guidance only.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from rdkit import Chem

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

PpmRange = Tuple[float, float]
HEURISTIC_DISCLAIMER = "HEURISTIC ONLY — approximate ppm ranges, not experimental values."

_MULTIPLICITY_MAP: Dict[int, str] = {
    0: "s",
    1: "d",
    2: "t",
    3: "q",
    4: "quint",
    5: "sext",
    6: "sept",
}

_BASE_SHIFT: Dict[str, float] = {
    "alkyl_CH3": 0.90,
    "alkyl_CH2": 1.25,
    "alkyl_CH": 1.55,
    "alkyl_C": 0.75,
    "benzylic": 2.30,
    "allylic": 1.90,
    "propargylic": 2.15,
    "alpha_carbonyl": 2.25,
    "alpha_nitrogen": 2.65,
    "alpha_oxygen": 3.55,
    "alpha_sulfur": 2.20,
    "alpha_halogen": 3.60,
    "vinyl": 5.40,
    "aromatic": 7.20,
    "heteroaromatic": 7.70,
    "aldehyde": 9.75,
    "terminal_alkyne": 2.50,
    "alcohol_OH": 2.50,
    "phenol_OH": 5.80,
    "carboxylic_OH": 11.50,
    "amide_NH": 7.40,
    "amine_NH": 2.20,
    "thiol_SH": 1.80,
    "pyridine_alpha": 8.55,
    "pyridine_beta": 7.55,
    "pyridine_gamma": 7.85,
    "diazine_alpha": 8.75,
    "diazine_beta": 8.05,
    "pyrrole_CH": 6.35,
    "indole_CH": 6.95,
    "imidazole_CH": 7.35,
    "pyrazine_CH": 8.55,
    "quinoline_alpha": 8.75,
    "quinoline_other": 7.80,
    "quinoxaline_CH": 8.55,
    "quinazoline_CH": 8.65,
    "triazine_CH": 8.85,
}

_ELECTRONEGATIVE_CORRECTION: Dict[str, float] = {
    "F": 1.60,
    "Cl": 1.10,
    "Br": 0.90,
    "I": 0.55,
    "O": 1.10,
    "N": 0.70,
    "S": 0.45,
}

_GROUP_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "aldehyde": {"label": "Aldehyde H", "ppm_range": (9.0, 10.2), "multiplicity": "s"},
    "carboxy": {"label": "Carboxylic OH", "ppm_range": (10.0, 13.0), "multiplicity": "br s"},
    "carboxylic": {"label": "Carboxylic OH", "ppm_range": (10.0, 13.0), "multiplicity": "br s"},
    "acid": {"label": "Carboxylic OH", "ppm_range": (10.0, 13.0), "multiplicity": "br s"},
    "aromatic": {"label": "Aromatic H", "ppm_range": (6.4, 8.4), "multiplicity": "m"},
    "aryl": {"label": "Aromatic H", "ppm_range": (6.4, 8.4), "multiplicity": "m"},
    "alcohol": {"label": "Alcohol OH", "ppm_range": (0.5, 5.5), "multiplicity": "br s"},
    "hydroxyl": {"label": "Alcohol OH", "ppm_range": (0.5, 5.5), "multiplicity": "br s"},
    "phenol": {"label": "Phenol OH", "ppm_range": (4.0, 8.0), "multiplicity": "br s"},
    "amide": {"label": "Amide NH", "ppm_range": (5.5, 9.5), "multiplicity": "br s"},
    "amine": {"label": "Amine NH", "ppm_range": (0.5, 4.5), "multiplicity": "br s"},
    "alkene": {"label": "Vinyl CH", "ppm_range": (4.5, 6.5), "multiplicity": "m"},
    "vinyl": {"label": "Vinyl CH", "ppm_range": (4.5, 6.5), "multiplicity": "m"},
    "alkyne": {"label": "Alkynyl CH", "ppm_range": (1.8, 3.2), "multiplicity": "s"},
    "benzylic": {"label": "Benzylic CH", "ppm_range": (2.0, 3.0), "multiplicity": "m"},
    "halogen": {"label": "Halogenated CH", "ppm_range": (3.0, 5.0), "multiplicity": "m"},
}


@dataclass(frozen=True)
class ProtonEnvironment:
    label: str
    ppm_range: PpmRange
    multiplicity: str
    integration: int
    description: str
    rationale: str = ""
    atom_idx: int = -1
    ppm_mid: float = 0.0
    annotation: str = ""
    environment_class: str = "unclassified"
    confidence: str = "low"
    hybridization: str = "OTHER"
    is_aromatic: bool = False
    is_heteroaromatic: bool = False
    heterocycle_family: Optional[str] = None
    hetero_position: Optional[str] = None
    ring_size: int = 0
    attached_elements: Tuple[str, ...] = field(default_factory=tuple)
    coupling_partners: int = 0
    is_exchangeable: bool = False
    is_approximate: bool = True
    disclaimer: str = HEURISTIC_DISCLAIMER

    @property
    def ppmrange(self) -> PpmRange:
        return self.ppm_range

    @property
    def ppmmid(self) -> float:
        return self.ppm_mid

    @property
    def atomidx(self) -> int:
        return self.atom_idx

    @property
    def environmentclass(self) -> str:
        return self.environment_class

    @property
    def isaromatic(self) -> bool:
        return self.is_aromatic

    @property
    def isheteroaromatic(self) -> bool:
        return self.is_heteroaromatic

    @property
    def heterocyclefamily(self) -> Optional[str]:
        return self.heterocycle_family

    @property
    def heteroposition(self) -> Optional[str]:
        return self.hetero_position

    @property
    def ringsize(self) -> int:
        return self.ring_size

    @property
    def attachedelements(self) -> Tuple[str, ...]:
        return self.attached_elements

    @property
    def couplingpartners(self) -> int:
        return self.coupling_partners

    @property
    def isexchangeable(self) -> bool:
        return self.is_exchangeable

    @property
    def isapproximate(self) -> bool:
        return self.is_approximate

    def features_dict(self) -> Dict[str, Any]:
        hyb_map = {"SP3": 0, "SP2": 1, "SP": 2, "AROMATIC": 3, "OTHER": 4}
        return {
            "atom_idx": self.atom_idx,
            "ppm_mid_heuristic": self.ppm_mid,
            "integration": self.integration,
            "hybridization": hyb_map.get(self.hybridization, 4),
            "is_aromatic": int(self.is_aromatic),
            "is_heteroaromatic": int(self.is_heteroaromatic),
            "ring_size": self.ring_size,
            "attached_O": int("O" in self.attached_elements),
            "attached_N": int("N" in self.attached_elements),
            "attached_S": int("S" in self.attached_elements),
            "attached_F": int("F" in self.attached_elements),
            "attached_Cl": int("Cl" in self.attached_elements),
            "attached_Br": int("Br" in self.attached_elements),
            "attached_I": int("I" in self.attached_elements),
            "coupling_partners": self.coupling_partners,
            "is_exchangeable": int(self.is_exchangeable),
            "heterocycle_family": self.heterocycle_family or "",
            "hetero_position": self.hetero_position or "",
        }

    def featuresdict(self) -> Dict[str, Any]:
        return self.features_dict()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "ppmrange": list(self.ppm_range),
                "ppmmid": self.ppm_mid,
                "atomidx": self.atom_idx,
                "environmentclass": self.environment_class,
                "isaromatic": self.is_aromatic,
                "isheteroaromatic": self.is_heteroaromatic,
                "heterocyclefamily": self.heterocycle_family,
                "heteroposition": self.hetero_position,
                "ringsize": self.ring_size,
                "attachedelements": list(self.attached_elements),
                "couplingpartners": self.coupling_partners,
                "isexchangeable": self.is_exchangeable,
                "isapproximate": self.is_approximate,
            }
        )
        return data

    def todict(self) -> Dict[str, Any]:
        return self.to_dict()


@dataclass(frozen=True)
class ProtonSignal:
    label: str
    ppm_range: PpmRange
    multiplicity: str
    integration: int
    description: str
    rationale: str = ""
    ppm_mid: float = 0.0
    annotation: str = ""
    environment_class: str = "unclassified"
    confidence: str = "low"
    is_exchangeable: bool = False
    is_approximate: bool = True
    disclaimer: str = HEURISTIC_DISCLAIMER

    @property
    def ppmrange(self) -> PpmRange:
        return self.ppm_range

    @property
    def ppmmid(self) -> float:
        return self.ppm_mid

    @property
    def environmentclass(self) -> str:
        return self.environment_class

    @property
    def isexchangeable(self) -> bool:
        return self.is_exchangeable

    @property
    def isapproximate(self) -> bool:
        return self.is_approximate

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "ppmrange": list(self.ppm_range),
                "ppmmid": self.ppm_mid,
                "environmentclass": self.environment_class,
                "isexchangeable": self.is_exchangeable,
                "isapproximate": self.is_approximate,
            }
        )
        return data

    def todict(self) -> Dict[str, Any]:
        return self.to_dict()


class LegacyMappingMixin(Mapping[str, Any]):
    def _legacy_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def to_legacy_dict(self) -> Dict[str, Any]:
        return dict(self._legacy_dict())

    def tolegacydict(self) -> Dict[str, Any]:
        return self.to_legacy_dict()

    def __getitem__(self, key: str) -> Any:
        return self._legacy_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._legacy_dict())

    def __len__(self) -> int:
        return len(self._legacy_dict())

    def keys(self):
        return self._legacy_dict().keys()

    def items(self):
        return self._legacy_dict().items()

    def values(self):
        return self._legacy_dict().values()

    def get(self, key: str, default: Any = None) -> Any:
        return self._legacy_dict().get(key, default)


_LegacyMappingMixin = LegacyMappingMixin


def _legacy_hnmr_label(env: ProtonEnvironment) -> str:
    cls = (env.environment_class or "").lower()
    family = (env.heterocycle_family or "").lower()

    if env.is_exchangeable:
        if "carboxy" in cls:
            return "Carboxylic OH"
        if "phenol" in cls:
            return "Phenol OH"
        if "alcohol" in cls:
            return "Alcohol OH"
        if "amide" in cls:
            return "Amide NH"
        if "amine" in cls:
            return "Amine NH"
        if "thiol" in cls:
            return "Thiolic SH"
        if family:
            return f"{family.title()} NH"

    if "aldehyde" in cls:
        return "Aldehyde H"
    if "aromatic" in cls or cls == "aromatic":
        return "Aromatic H"
    if "pyridine" in cls:
        return "Pyridine H"
    if "quinoline" in cls:
        return "Quinoline H"
    if "quinoxaline" in cls:
        return "Quinoxaline H"
    if "quinazoline" in cls:
        return "Quinazoline H"
    if "imidazole" in cls:
        return "Imidazole H"
    if "indole" in cls:
        return "Indole H"
    if "pyrrole" in cls:
        return "Pyrrole H"
    if "vinyl" in cls:
        return "Vinyl H"
    if "terminal_alkyne" in cls or "alkynyl" in cls:
        return "Alkynyl H"
    if "benzylic" in cls:
        return "Benzylic CH"
    if "allylic" in cls:
        return "Allylic CH"
    if "propargylic" in cls:
        return "Propargylic CH"
    if "alpha_oxygen" in cls:
        return "CH alpha to O"
    if "alpha_nitrogen" in cls:
        return "CH alpha to N"
    if "alpha_sulfur" in cls:
        return "CH alpha to S"
    if "alpha_halogen" in cls:
        return "CH alpha to halogen"
    if "alpha_carbonyl" in cls:
        return "CH alpha to carbonyl"
    if "ch3" in cls:
        return "CH3 aliphatic"
    if "ch2" in cls:
        return "CH2 aliphatic"
    if "alkyl_ch" in cls or cls == "alkyl_ch":
        return "CH aliphatic"
    return env.label or "Proton"


@dataclass
class NMRPrediction(LegacyMappingMixin):
    smiles: str
    environments: List[ProtonEnvironment] = field(default_factory=list)
    signals: List[ProtonSignal] = field(default_factory=list)
    is_heuristic: bool = True
    warnings: List[str] = field(default_factory=list)
    total_H: int = 0
    n_signals: int = 0
    disclaimer: str = HEURISTIC_DISCLAIMER

    @property
    def totalH(self) -> int:
        return self.total_H

    @property
    def nsignals(self) -> int:
        return self.n_signals

    @property
    def isheuristic(self) -> bool:
        return self.is_heuristic

    def _legacy_dict(self) -> Dict[str, float]:
        ordered: Dict[str, float] = {}
        for env in sorted(self.environments, key=lambda e: e.ppm_mid, reverse=True):
            base = _legacy_hnmr_label(env)
            key = base
            counter = 2
            while key in ordered:
                key = f"{base} ({counter})"
                counter += 1
            ordered[key] = float(env.ppm_mid)
        return ordered

    def summary(self) -> str:
        if not self.signals:
            return "No proton environments predicted (HEURISTIC — approximate)."
        lines = [
            "1H NMR Prediction (HEURISTIC — approximate only)",
            f"SMILES: {self.smiles}",
            f"Total signals: {self.n_signals}",
            f"Total integrated H: {self.total_H}",
            "",
            f"{'Label':<26} {'Range (ppm)':<16} {'Mult':<6} {'Int':<4} Annotation",
            "-" * 92,
        ]
        for sig in self.signals:
            lo, hi = sig.ppm_range
            lines.append(
                f"{sig.label:<26} {lo:.2f}-{hi:.2f} {sig.multiplicity:<6} {sig.integration:<4} {sig.annotation or sig.description}"
            )
        if self.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f" - {w}" for w in self.warnings)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smiles": self.smiles,
            "environments": [e.to_dict() for e in self.environments],
            "signals": [s.to_dict() for s in self.signals],
            "is_heuristic": self.is_heuristic,
            "warnings": list(self.warnings),
            "total_H": self.total_H,
            "n_signals": self.n_signals,
            "disclaimer": self.disclaimer,
            "totalH": self.total_H,
            "nsignals": self.n_signals,
            "isheuristic": self.is_heuristic,
            "legacy": self._legacy_dict(),
        }

    def todict(self) -> Dict[str, Any]:
        return self.to_dict()


class MLShiftModel:
    def is_available(self) -> bool:
        return False

    def predict(self, features: Dict[str, Any]) -> Optional[float]:
        logger.debug("MLShiftModel.predict called without a loaded model.")
        return None

    @classmethod
    def load(cls, path: str) -> "MLShiftModel":
        raise NotImplementedError("No trained ML proton-shift model is available yet.")



def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")



def _cap_range(lo: float, hi: float, min_lo: float = -1.0, max_hi: float = 20.0) -> PpmRange:
    lo = max(lo, min_lo)
    hi = min(hi, max_hi)
    if hi < lo:
        hi = lo + 0.1
    return (round(lo, 2), round(hi, 2))



def _average(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0



def predict_from_groups(groups: Dict[str, int]) -> List[ProtonEnvironment]:
    if not isinstance(groups, dict):
        raise TypeError("groups must be a dict[str, int]")
    envs: List[ProtonEnvironment] = []
    idx = 0
    for name, count in groups.items():
        try:
            cnt = int(count)
        except Exception:
            cnt = 1
        if cnt <= 0:
            continue

        lname = _norm_key(str(name))
        matched = None
        for key, spec in _GROUP_DEFAULTS.items():
            if _norm_key(key) in lname:
                matched = spec
                break

        if matched is None:
            label = str(name)
            ppm_range = (0.5, 2.2)
            multiplicity = "m"
            description = "Fallback aliphatic environment"
            annotation = "Functional-group fallback"
            env_class = "group_fallback"
        else:
            label = matched["label"]
            ppm_range = matched["ppm_range"]
            multiplicity = matched["multiplicity"]
            description = f"{label} from functional-group heuristic"
            annotation = f"{label} (group-derived)"
            env_class = _norm_key(label)

        lo, hi = ppm_range
        envs.append(
            ProtonEnvironment(
                label=label,
                ppm_range=(round(lo, 2), round(hi, 2)),
                multiplicity=multiplicity,
                integration=cnt,
                description=description,
                rationale=f"Group-only heuristic from input key: {name}",
                atom_idx=idx,
                ppm_mid=round((lo + hi) / 2.0, 2),
                annotation=annotation,
                environment_class=env_class,
                confidence="low",
                is_aromatic=("aromatic" in lname or "aryl" in lname),
                is_exchangeable=any(token in lname for token in ("oh", "nh", "carboxy", "acid", "hydroxyl")),
            )
        )
        idx += 1
    return envs


class ProtonNMRPredictor:
    def __init__(self, ml_model: Optional[MLShiftModel] = None) -> None:
        self._ml = ml_model or MLShiftModel()
        self.warnings: List[str] = []

    def predict_from_smiles(self, smiles: str) -> NMRPrediction:
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError("smiles must be a non-empty string")
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            raise ValueError(f"Could not parse SMILES: {smiles}")
        return self.predict(mol)

    def predict(self, mol: Chem.Mol) -> NMRPrediction:
        if mol is None:
            raise ValueError("mol cannot be None")
        if not hasattr(mol, "GetNumAtoms"):
            raise TypeError("mol must be an RDKit Mol object")

        self.warnings = []
        try:
            smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
        except Exception:
            smiles = ""

        mol_h = Chem.AddHs(mol)
        environments: List[ProtonEnvironment] = []

        for atom in mol_h.GetAtoms():
            if atom.GetAtomicNum() == 1:
                continue
            if self._hydrogen_count(atom) <= 0:
                continue
            try:
                environments.append(self._predict_environment(atom, mol_h))
            except Exception as exc:
                msg = f"Failed to classify atom {atom.GetIdx()} ({atom.GetSymbol()}): {exc}"
                logger.exception(msg)
                self.warnings.append(msg)

        environments.sort(key=lambda e: e.ppm_range[0], reverse=True)
        signals = self._group_signals(environments)
        total_H = sum(e.integration for e in environments)

        if not environments:
            self.warnings.append("No proton environments detected.")
        if mol_h.GetNumHeavyAtoms() > 80:
            self.warnings.append("Large molecule detected; heuristic reliability may decrease.")

        return NMRPrediction(
            smiles=smiles,
            environments=environments,
            signals=signals,
            is_heuristic=True,
            warnings=list(self.warnings),
            total_H=total_H,
            n_signals=len(signals),
        )

    def predict_features(self, mol: Chem.Mol) -> List[Dict[str, Any]]:
        result = self.predict(mol)
        return [env.features_dict() for env in result.environments]

    def _hydrogen_count(self, atom: Chem.Atom) -> int:
        explicit_h = sum(1 for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() == 1)
        implicit_h = int(atom.GetNumImplicitHs())
        total_h = explicit_h + implicit_h
        if total_h == 0:
            total_h = int(atom.GetTotalNumHs())
        return total_h

    def _predict_environment(self, atom: Chem.Atom, mol: Chem.Mol) -> ProtonEnvironment:
        elem = atom.GetSymbol()
        hyb = atom.GetHybridization().name

        if elem == "O":
            return self._predict_exchangeable_oxygen(atom, mol)
        if elem == "N":
            return self._predict_exchangeable_nitrogen(atom, mol)
        if elem == "S":
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["thiol_SH"],
                half_width=0.6,
                label="Thiolic SH",
                annotation="Thiol proton (exchangeable)",
                env_class="thiol_SH",
                description="Exchangeable sulfur-bound proton",
                rationale="S-H proton assigned by functional environment",
                confidence="medium",
                multiplicity="br s",
                coupling_partners=0,
                is_exchangeable=True,
                heterocycle_family=None,
                hetero_position=None,
            )

        if elem != "C":
            return self._build_environment(
                atom=atom,
                ppm_mid=1.5,
                half_width=0.6,
                label=f"{elem}-H",
                annotation="Unclassified proton-bearing atom",
                env_class="unclassified",
                description="Fallback environment",
                rationale=f"Fallback classification for {elem}-bound proton",
                confidence="low",
                multiplicity="m",
                coupling_partners=0,
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_aldehyde_carbon(atom, mol):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["aldehyde"],
                half_width=0.25,
                label="Aldehyde CH",
                annotation="CHO proton",
                env_class="aldehyde",
                description="Aldehydic proton",
                rationale="Carbonyl carbon bearing one hydrogen",
                confidence="high",
                multiplicity="m",
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if hyb == "SP":
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["terminal_alkyne"],
                half_width=0.25,
                label="Alkynyl CH",
                annotation="Terminal alkyne proton",
                env_class="terminal_alkyne",
                description="sp carbon-bound proton",
                rationale="sp-hybridized carbon bearing hydrogen",
                confidence="high",
                multiplicity="s",
                coupling_partners=0,
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        family, position = self._heteroaromatic_context(atom, mol)
        if atom.GetIsAromatic():
            return self._predict_aromatic_carbon(atom, mol, family, position)

        if hyb == "SP2":
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["vinyl"] + self._substituent_correction(atom, mol),
                half_width=0.45,
                label="Vinyl CH",
                annotation="Olefinic proton",
                env_class="vinyl",
                description="sp2 carbon-bound proton",
                rationale="Olefinic carbon with substituent correction",
                confidence="medium",
                multiplicity="m",
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        return self._predict_sp3_carbon(atom, mol)

    def _predict_exchangeable_oxygen(self, atom: Chem.Atom, mol: Chem.Mol) -> ProtonEnvironment:
        if self._is_carboxylic_oh(atom, mol):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["carboxylic_OH"],
                half_width=1.4,
                label="Carboxylic OH",
                annotation="COOH proton (exchangeable)",
                env_class="carboxylic_OH",
                description="Carboxylic acid proton",
                rationale="O-H attached to carboxyl system",
                confidence="high",
                multiplicity="br s",
                coupling_partners=0,
                is_exchangeable=True,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_phenol(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["phenol_OH"],
                half_width=1.8,
                label="Phenol OH",
                annotation="ArOH proton (exchangeable)",
                env_class="phenol_OH",
                description="Phenolic hydroxyl proton",
                rationale="Aromatic oxygen-bound exchangeable proton",
                confidence="medium",
                multiplicity="br s",
                coupling_partners=0,
                is_exchangeable=True,
                heterocycle_family=None,
                hetero_position=None,
            )

        return self._build_environment(
            atom=atom,
            ppm_mid=_BASE_SHIFT["alcohol_OH"],
            half_width=1.6,
            label="Alcohol OH",
            annotation="ROH proton (exchangeable)",
            env_class="alcohol_OH",
            description="Alcohol hydroxyl proton",
            rationale="Non-phenolic O-H proton",
            confidence="medium",
            multiplicity="br s",
            coupling_partners=0,
            is_exchangeable=True,
            heterocycle_family=None,
            hetero_position=None,
        )

    def _predict_exchangeable_nitrogen(self, atom: Chem.Atom, mol: Chem.Mol) -> ProtonEnvironment:
        family = self._heterocycle_family_for_nh(atom, mol)

        if self._is_amide_nh(atom, mol):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["amide_NH"],
                half_width=1.4,
                label="Amide NH",
                annotation="Amide N-H (exchangeable)",
                env_class="amide_NH",
                description="Amide proton",
                rationale="Nitrogen adjacent to carbonyl",
                confidence="medium",
                multiplicity="br s",
                coupling_partners=0,
                is_exchangeable=True,
                heterocycle_family=family,
                hetero_position=None,
            )

        if family in {"pyrrole", "indole", "imidazole", "pyrazole"}:
            mid = {"pyrrole": 9.7, "indole": 10.4, "imidazole": 11.7, "pyrazole": 12.2}.get(family, 9.5)
            return self._build_environment(
                atom=atom,
                ppm_mid=mid,
                half_width=1.2,
                label=f"{family.title()} NH",
                annotation=f"{family.title()} N-H (exchangeable)",
                env_class=f"{family}_NH",
                description="Heteroaromatic N-H proton",
                rationale=f"Exchangeable NH in {family}-like heterocycle",
                confidence="medium",
                multiplicity="br s",
                coupling_partners=0,
                is_exchangeable=True,
                heterocycle_family=family,
                hetero_position=None,
            )

        return self._build_environment(
            atom=atom,
            ppm_mid=_BASE_SHIFT["amine_NH"],
            half_width=1.8,
            label="Amine NH",
            annotation="Amine N-H (exchangeable)",
            env_class="amine_NH",
            description="Amine proton",
            rationale="Non-amide N-H environment",
            confidence="low",
            multiplicity="br s",
            coupling_partners=0,
            is_exchangeable=True,
            heterocycle_family=family,
            hetero_position=None,
        )

    def _predict_aromatic_carbon(
        self,
        atom: Chem.Atom,
        mol: Chem.Mol,
        family: Optional[str],
        hetero_position: Optional[str],
    ) -> ProtonEnvironment:
        if family:
            mid = self._heterocycle_specific_shift(family, hetero_position)
            mid += self._aromatic_substituent_walk_correction(atom, mol)
            return self._build_environment(
                atom=atom,
                ppm_mid=mid,
                half_width=0.4,
                label=f"{family.title()} CH",
                annotation=self._hetero_annotation(family, hetero_position),
                env_class=f"{family}_CH",
                description="Heteroaromatic carbon-bound proton",
                rationale=f"Heteroaromatic proton in {family}" + (f" at {hetero_position} position" if hetero_position else ""),
                confidence="medium",
                multiplicity="m",
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=family,
                hetero_position=hetero_position,
            )

        return self._build_environment(
            atom=atom,
            ppm_mid=_BASE_SHIFT["aromatic"] + self._aromatic_substituent_walk_correction(atom, mol),
            half_width=0.4,
            label="Aromatic CH",
            annotation="Aryl proton",
            env_class="aromatic",
            description="Benzenoid aromatic proton",
            rationale="Aromatic carbon-bound proton with simple substituent correction",
            confidence="high",
            multiplicity="m",
            coupling_partners=self._count_vicinal_h(atom),
            is_exchangeable=False,
            heterocycle_family=None,
            hetero_position=None,
        )

    def _predict_sp3_carbon(self, atom: Chem.Atom, mol: Chem.Mol) -> ProtonEnvironment:
        total_h = self._hydrogen_count(atom)
        attached = [n.GetSymbol() for n in atom.GetNeighbors() if n.GetAtomicNum() != 1]

        if self._is_alpha_to_halogen(atom):
            halogens = [x for x in attached if x in {"F", "Cl", "Br", "I"}]
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["alpha_halogen"] + self._halogen_heavy_correction(halogens),
                half_width=0.45,
                label=self._sp3_label(total_h),
                annotation="C-H alpha to halogen",
                env_class="alpha_halogen",
                description="sp3 carbon adjacent to halogen",
                rationale=f"Halogen deshielding from neighbors: {','.join(halogens) or 'unknown'}",
                confidence="high" if len(halogens) >= 2 else "medium",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_alpha_to_oxygen(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["alpha_oxygen"] + self._substituent_correction(atom, mol),
                half_width=0.4,
                label=self._sp3_label(total_h),
                annotation="C-H alpha to oxygen",
                env_class="alpha_oxygen",
                description="O-substituted sp3 carbon",
                rationale="Deshielding from oxygen adjacency",
                confidence="high",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_alpha_to_nitrogen(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["alpha_nitrogen"] + self._substituent_correction(atom, mol),
                half_width=0.4,
                label=self._sp3_label(total_h),
                annotation="C-H alpha to nitrogen",
                env_class="alpha_nitrogen",
                description="N-substituted sp3 carbon",
                rationale="Deshielding from nitrogen adjacency",
                confidence="high",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_alpha_to_sulfur(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["alpha_sulfur"] + self._substituent_correction(atom, mol),
                half_width=0.35,
                label=self._sp3_label(total_h),
                annotation="C-H alpha to sulfur",
                env_class="alpha_sulfur",
                description="S-substituted sp3 carbon",
                rationale="Deshielding from sulfur adjacency",
                confidence="medium",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_alpha_to_carbonyl(atom, mol):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["alpha_carbonyl"] + self._substituent_correction(atom, mol),
                half_width=0.4,
                label=self._sp3_label(total_h),
                annotation="C-H alpha to carbonyl",
                env_class="alpha_carbonyl",
                description="Carbonyl-adjacent sp3 carbon",
                rationale="Neighbor-walk detected adjacent carbonyl",
                confidence="high",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_benzylic(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["benzylic"] + self._substituent_correction(atom, mol),
                half_width=0.35,
                label=self._sp3_label(total_h),
                annotation="Benzylic C-H",
                env_class="benzylic",
                description="sp3 carbon adjacent to aromatic ring",
                rationale="Benzylic deshielding from adjacent aromatic system",
                confidence="high",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_allylic(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["allylic"] + self._substituent_correction(atom, mol),
                half_width=0.35,
                label=self._sp3_label(total_h),
                annotation="Allylic C-H",
                env_class="allylic",
                description="sp3 carbon adjacent to alkene",
                rationale="Allylic deshielding from neighboring sp2 system",
                confidence="medium",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        if self._is_propargylic(atom):
            return self._build_environment(
                atom=atom,
                ppm_mid=_BASE_SHIFT["propargylic"] + self._substituent_correction(atom, mol),
                half_width=0.35,
                label=self._sp3_label(total_h),
                annotation="Propargylic C-H",
                env_class="propargylic",
                description="sp3 carbon adjacent to alkyne",
                rationale="Propargylic environment from neighboring sp carbon",
                confidence="medium",
                multiplicity=self._estimate_multiplicity(atom),
                coupling_partners=self._count_vicinal_h(atom),
                is_exchangeable=False,
                heterocycle_family=None,
                hetero_position=None,
            )

        base_class = (
            "alkyl_CH3" if total_h >= 3 else
            "alkyl_CH2" if total_h == 2 else
            "alkyl_CH" if total_h == 1 else
            "alkyl_C"
        )
        return self._build_environment(
            atom=atom,
            ppm_mid=_BASE_SHIFT[base_class] + self._substituent_correction(atom, mol),
            half_width=0.3,
            label=self._sp3_label(total_h),
            annotation="Simple alkyl proton",
            env_class=base_class,
            description="Unactivated aliphatic proton",
            rationale="Default sp3 alkyl assignment",
            confidence="high",
            multiplicity=self._estimate_multiplicity(atom),
            coupling_partners=self._count_vicinal_h(atom),
            is_exchangeable=False,
            heterocycle_family=None,
            hetero_position=None,
        )

    def _build_environment(
        self,
        atom: Chem.Atom,
        ppm_mid: float,
        half_width: float,
        label: str,
        annotation: str,
        env_class: str,
        description: str,
        rationale: str,
        confidence: str,
        multiplicity: str,
        coupling_partners: int,
        is_exchangeable: bool,
        heterocycle_family: Optional[str],
        hetero_position: Optional[str],
    ) -> ProtonEnvironment:
        lo, hi = _cap_range(ppm_mid - half_width, ppm_mid + half_width)
        mid = round(ppm_mid, 2)

        if self._ml.is_available():
            ml_val = self._ml.predict(
                {
                    "atom_idx": atom.GetIdx(),
                    "ppm_mid_heuristic": mid,
                    "hybridization": atom.GetHybridization().name,
                    "is_aromatic": int(atom.GetIsAromatic()),
                    "coupling_partners": coupling_partners,
                    "heterocycle_family": heterocycle_family or "",
                    "hetero_position": hetero_position or "",
                }
            )
            if ml_val is not None:
                mid = round(float(ml_val), 2)
                lo, hi = _cap_range(mid - half_width, mid + half_width)

        return ProtonEnvironment(
            label=label,
            ppm_range=(lo, hi),
            multiplicity=multiplicity,
            integration=self._hydrogen_count(atom),
            description=description,
            rationale=rationale,
            atom_idx=atom.GetIdx(),
            ppm_mid=mid,
            annotation=annotation,
            environment_class=env_class,
            confidence=confidence,
            hybridization=atom.GetHybridization().name,
            is_aromatic=bool(atom.GetIsAromatic()),
            is_heteroaromatic=bool(atom.GetIsAromatic() and heterocycle_family is not None),
            heterocycle_family=heterocycle_family,
            hetero_position=hetero_position,
            ring_size=self._smallest_ring_size(atom),
            attached_elements=tuple(sorted(n.GetSymbol() for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)),
            coupling_partners=coupling_partners,
            is_exchangeable=is_exchangeable,
        )

    def _group_signals(self, environments: List[ProtonEnvironment]) -> List[ProtonSignal]:
        if not environments:
            return []
        ordered = sorted(environments, key=lambda e: e.ppm_mid, reverse=True)
        groups: List[List[ProtonEnvironment]] = []

        for env in ordered:
            placed = False
            for grp in groups:
                head = grp[0]
                if (
                    env.environment_class == head.environment_class
                    and env.multiplicity == head.multiplicity
                    and env.is_exchangeable == head.is_exchangeable
                    and env.heterocycle_family == head.heterocycle_family
                    and env.hetero_position == head.hetero_position
                    and abs(env.ppm_mid - head.ppm_mid) <= 0.30
                ):
                    grp.append(env)
                    placed = True
                    break
            if not placed:
                groups.append([env])

        rank = {"high": 2, "medium": 1, "low": 0}
        signals: List[ProtonSignal] = []
        for grp in groups:
            head = grp[0]
            lo = min(e.ppm_range[0] for e in grp)
            hi = max(e.ppm_range[1] for e in grp)
            worst_conf = min(grp, key=lambda e: rank.get(e.confidence, 0)).confidence
            signals.append(
                ProtonSignal(
                    label=head.label,
                    ppm_range=(round(lo, 2), round(hi, 2)),
                    multiplicity=head.multiplicity,
                    integration=sum(e.integration for e in grp),
                    description=head.description,
                    rationale=head.rationale,
                    ppm_mid=_average([e.ppm_mid for e in grp]),
                    annotation=head.annotation,
                    environment_class=head.environment_class,
                    confidence=worst_conf,
                    is_exchangeable=head.is_exchangeable,
                )
            )
        return sorted(signals, key=lambda s: s.ppm_range[0], reverse=True)

    def _estimate_multiplicity(self, atom: Chem.Atom) -> str:
        if atom.GetIsAromatic() or atom.GetHybridization().name == "SP2":
            return "m"
        n = self._count_vicinal_h(atom)
        return _MULTIPLICITY_MAP.get(n, "m")

    def _count_vicinal_h(self, atom: Chem.Atom) -> int:
        total = 0
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 1:
                continue
            if nbr.GetHybridization().name == "SP3":
                total += self._hydrogen_count(nbr)
        return total

    def _substituent_correction(self, atom: Chem.Atom, mol: Chem.Mol) -> float:
        counts: Dict[str, int] = {}
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 1:
                continue
            sym = nbr.GetSymbol()
            if sym in _ELECTRONEGATIVE_CORRECTION:
                counts[sym] = counts.get(sym, 0) + 1
        corr = 0.0
        for sym, n in counts.items():
            inc = _ELECTRONEGATIVE_CORRECTION[sym]
            corr += inc * (1.0 + 0.5 * (n - 1))
        if self._is_alpha_to_carbonyl(atom, mol):
            corr += 0.45
        if self._is_benzylic(atom):
            corr += 0.20
        return round(corr, 2)

    def _halogen_heavy_correction(self, halogens: Sequence[str]) -> float:
        if not halogens:
            return 0.0
        weights = {"F": 1.0, "Cl": 1.15, "Br": 0.95, "I": 0.55}
        total = sum(weights.get(h, 0.0) for h in halogens)
        if len(halogens) >= 3:
            total += 1.4
        elif len(halogens) == 2:
            total += 0.7
        return round(total, 2)

    def _smallest_ring_size(self, atom: Chem.Atom) -> int:
        ring_info = atom.GetOwningMol().GetRingInfo()
        sizes = [len(r) for r in ring_info.AtomRings() if atom.GetIdx() in r]
        return min(sizes) if sizes else 0

    def _is_carboxylic_oh(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 8 or self._hydrogen_count(atom) <= 0:
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() != 6:
                continue
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetIdx() == atom.GetIdx():
                    continue
                if nbr2.GetAtomicNum() == 8:
                    bond = mol.GetBondBetweenAtoms(nbr.GetIdx(), nbr2.GetIdx())
                    if bond and bond.GetBondTypeAsDouble() == 2.0:
                        return True
        return False

    def _is_phenol(self, atom: Chem.Atom) -> bool:
        return atom.GetAtomicNum() == 8 and self._hydrogen_count(atom) > 0 and any(
            nbr.GetAtomicNum() == 6 and nbr.GetIsAromatic() for nbr in atom.GetNeighbors()
        )

    def _is_amide_nh(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 7 or self._hydrogen_count(atom) <= 0:
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() != 6:
                continue
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetIdx() == atom.GetIdx():
                    continue
                if nbr2.GetAtomicNum() == 8:
                    bond = mol.GetBondBetweenAtoms(nbr.GetIdx(), nbr2.GetIdx())
                    if bond and bond.GetBondTypeAsDouble() == 2.0:
                        return True
        return False

    def _is_aldehyde_carbon(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 6 or self._hydrogen_count(atom) != 1:
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 8:
                bond = mol.GetBondBetweenAtoms(atom.GetIdx(), nbr.GetIdx())
                if bond and bond.GetBondTypeAsDouble() == 2.0:
                    return True
        return False

    def _is_alpha_to_carbonyl(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 6:
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() != 6:
                continue
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetAtomicNum() == 8:
                    bond = mol.GetBondBetweenAtoms(nbr.GetIdx(), nbr2.GetIdx())
                    if bond and bond.GetBondTypeAsDouble() == 2.0:
                        return True
        return False

    def _is_benzylic(self, atom: Chem.Atom) -> bool:
        if atom.GetAtomicNum() != 6 or atom.GetIsAromatic():
            return False
        return any(nbr.GetAtomicNum() == 6 and nbr.GetIsAromatic() for nbr in atom.GetNeighbors())

    def _is_allylic(self, atom: Chem.Atom) -> bool:
        if atom.GetAtomicNum() != 6 or atom.GetIsAromatic():
            return False
        return any(
            nbr.GetAtomicNum() != 1 and nbr.GetHybridization().name == "SP2" and not nbr.GetIsAromatic()
            for nbr in atom.GetNeighbors()
        )

    def _is_propargylic(self, atom: Chem.Atom) -> bool:
        if atom.GetAtomicNum() != 6:
            return False
        return any(nbr.GetAtomicNum() != 1 and nbr.GetHybridization().name == "SP" for nbr in atom.GetNeighbors())

    def _is_alpha_to_oxygen(self, atom: Chem.Atom) -> bool:
        return any(nbr.GetSymbol() == "O" for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() != 1)

    def _is_alpha_to_nitrogen(self, atom: Chem.Atom) -> bool:
        return any(nbr.GetSymbol() == "N" for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() != 1)

    def _is_alpha_to_sulfur(self, atom: Chem.Atom) -> bool:
        return any(nbr.GetSymbol() == "S" for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() != 1)

    def _is_alpha_to_halogen(self, atom: Chem.Atom) -> bool:
        return any(nbr.GetSymbol() in {"F", "Cl", "Br", "I"} for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() != 1)

    def _sp3_label(self, hcount: int) -> str:
        if hcount >= 3:
            return "CH3"
        if hcount == 2:
            return "CH2"
        return "CH"

    def _heterocycle_family_for_nh(self, atom: Chem.Atom, mol: Chem.Mol) -> Optional[str]:
        if not atom.GetIsAromatic() or atom.GetAtomicNum() != 7:
            return None
        ring_sizes = sorted(len(r) for r in mol.GetRingInfo().AtomRings() if atom.GetIdx() in r)
        aromatic_n = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 7)
        if 5 in ring_sizes and 6 in ring_sizes:
            return "indole"
        if 5 in ring_sizes and aromatic_n >= 2:
            return "imidazole"
        if 5 in ring_sizes:
            return "pyrrole"
        return None

    def _heteroaromatic_context(self, atom: Chem.Atom, mol: Chem.Mol) -> Tuple[Optional[str], Optional[str]]:
        if not atom.GetIsAromatic() or atom.GetAtomicNum() != 6:
            return None, None
        ring_sizes = sorted(len(r) for r in mol.GetRingInfo().AtomRings() if atom.GetIdx() in r)
        aromatic_n_atoms = [a for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 7]
        aromatic_n = len(aromatic_n_atoms)
        aromatic_o = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 8)
        aromatic_s = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 16)
        fused_count = sum(1 for r in mol.GetRingInfo().AtomRings() if atom.GetIdx() in r)
        pos = self._hetero_position_from_aromatic_carbon(atom, mol)

        if 6 in ring_sizes and aromatic_n == 1 and aromatic_o == 0 and aromatic_s == 0:
            return "pyridine", pos
        if 6 in ring_sizes and aromatic_n == 2 and fused_count == 1:
            if len(aromatic_n_atoms) >= 2:
                dist = len(Chem.GetShortestPath(mol, aromatic_n_atoms[0].GetIdx(), aromatic_n_atoms[1].GetIdx()))
                if dist == 3:
                    return "pyridazine", pos
                if dist == 4:
                    return "pyrimidine", pos
            return "pyrazine", pos
        if 6 in ring_sizes and aromatic_n == 3:
            return "triazine", pos
        if 5 in ring_sizes and 6 in ring_sizes and aromatic_n == 1:
            return "indole", pos
        if 5 in ring_sizes and aromatic_n == 1 and aromatic_o == 0 and aromatic_s == 0:
            return "pyrrole", None
        if 5 in ring_sizes and aromatic_n == 2:
            return "imidazole", None
        if fused_count >= 2 and aromatic_n == 1:
            return "quinoline", pos
        if fused_count >= 2 and aromatic_n == 2:
            if len(aromatic_n_atoms) >= 2:
                dist = len(Chem.GetShortestPath(mol, aromatic_n_atoms[0].GetIdx(), aromatic_n_atoms[1].GetIdx()))
                if dist == 3:
                    return "quinazoline", pos
            return "quinoxaline", pos
        return None, None

    def _hetero_position_from_aromatic_carbon(self, atom: Chem.Atom, mol: Chem.Mol) -> Optional[str]:
        aromatic_hetero = [a for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() in {7, 8, 16}]
        if not aromatic_hetero:
            return None
        distances: List[int] = []
        for het in aromatic_hetero:
            try:
                path_len = len(Chem.GetShortestPath(mol, atom.GetIdx(), het.GetIdx())) - 1
                distances.append(path_len)
            except Exception:
                continue
        if not distances:
            return None
        d = min(distances)
        if d == 1:
            return "alpha"
        if d == 2:
            return "beta"
        if d == 3:
            return "gamma"
        return "remote"

    def _heterocycle_specific_shift(self, family: str, hetero_position: Optional[str]) -> float:
        if family == "pyridine":
            return _BASE_SHIFT.get(f"pyridine_{hetero_position or 'beta'}", 7.8)
        if family in {"pyridazine", "pyrimidine"}:
            return _BASE_SHIFT["diazine_alpha"] if hetero_position == "alpha" else _BASE_SHIFT["diazine_beta"]
        if family == "pyrazine":
            return _BASE_SHIFT["pyrazine_CH"]
        if family == "pyrrole":
            return _BASE_SHIFT["pyrrole_CH"]
        if family == "indole":
            return _BASE_SHIFT["indole_CH"]
        if family == "imidazole":
            return _BASE_SHIFT["imidazole_CH"]
        if family == "quinoline":
            return _BASE_SHIFT["quinoline_alpha"] if hetero_position == "alpha" else _BASE_SHIFT["quinoline_other"]
        if family == "quinoxaline":
            return _BASE_SHIFT["quinoxaline_CH"]
        if family == "quinazoline":
            return _BASE_SHIFT["quinazoline_CH"]
        if family == "triazine":
            return _BASE_SHIFT["triazine_CH"]
        return _BASE_SHIFT["heteroaromatic"]

    def _hetero_annotation(self, family: str, position: Optional[str]) -> str:
        return f"{family.title()} {position}-position proton" if position else f"{family.title()} heteroaromatic proton"

    def _aromatic_substituent_walk_correction(self, atom: Chem.Atom, mol: Chem.Mol) -> float:
        ewg = 0
        edg = 0
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 1:
                continue
            if nbr.GetAtomicNum() in {7, 8, 16} and not nbr.GetIsAromatic():
                edg += 1
            if self._atom_is_carbonyl_center(nbr, mol):
                ewg += 1
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetIdx() == atom.GetIdx():
                    continue
                if nbr2.GetAtomicNum() in {7, 8, 16} and not nbr2.GetIsAromatic():
                    edg += 1
                if self._atom_is_carbonyl_center(nbr2, mol):
                    ewg += 1
                if nbr2.GetAtomicNum() in {9, 17, 35, 53}:
                    ewg += 1
        return round(0.25 * ewg - 0.15 * edg, 2)

    def _atom_is_carbonyl_center(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 6:
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 8:
                bond = mol.GetBondBetweenAtoms(atom.GetIdx(), nbr.GetIdx())
                if bond and bond.GetBondTypeAsDouble() == 2.0:
                    return True
        return False


def predictprotonnmr(mol_or_smiles: Any, ml_model: Optional[MLShiftModel] = None) -> NMRPrediction:
    predictor = ProtonNMRPredictor(ml_model=ml_model)
    if isinstance(mol_or_smiles, str):
        return predictor.predict_from_smiles(mol_or_smiles)
    if mol_or_smiles is None:
        raise ValueError("predictprotonnmr received None")
    return predictor.predict(mol_or_smiles)


def predict_proton_nmr(mol_or_smiles: Any, ml_model: Optional[MLShiftModel] = None) -> NMRPrediction:
    """Legacy underscored wrapper for compatibility with existing imports."""
    return predictprotonnmr(mol_or_smiles, ml_model=ml_model)


def predictfromsmiles(smiles: str, ml_model: Optional[MLShiftModel] = None) -> NMRPrediction:
    return ProtonNMRPredictor(ml_model=ml_model).predict_from_smiles(smiles)


def predict_from_smiles(smiles: str, ml_model: Optional[MLShiftModel] = None) -> NMRPrediction:
    return predictfromsmiles(smiles, ml_model=ml_model)


def predictfromgroups(groups: Dict[str, int]) -> List[ProtonEnvironment]:
    return predict_from_groups(groups)


def summary_text(environments: Iterable[ProtonEnvironment]) -> str:
    return "; ".join(
        f"{e.label}: {e.ppm_range[0]:.2f}-{e.ppm_range[1]:.2f} ppm ({e.multiplicity}, {e.integration}H, HEURISTIC)"
        for e in environments
    )


def summarytext(environments: Iterable[ProtonEnvironment]) -> str:
    return summary_text(environments)


__all__ = [
    "HEURISTIC_DISCLAIMER",
    "LegacyMappingMixin",
    "MLShiftModel",
    "NMRPrediction",
    "PpmRange",
    "ProtonEnvironment",
    "ProtonNMRPredictor",
    "ProtonSignal",
    "predict_from_groups",
    "predict_from_smiles",
    "predictfromgroups",
    "predictfromsmiles",
    "predict_proton_nmr",
    "predictprotonnmr",
    "summary_text",
    "summarytext",
]
