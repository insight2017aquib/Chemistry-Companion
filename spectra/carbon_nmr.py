"""
chemistry_companion/spectra/carbon_nmr.py
=========================================
Production-ready heuristic 13C NMR predictor for Chemistry Companion.

IMPORTANT
---------
All outputs from this module are APPROXIMATE HEURISTICS only.
This module does not provide quantum-accurate, DFT-derived, or ML-calibrated
13C shifts. Use it for rough annotation and educational guidance only.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from rdkit import Chem

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

PpmRange = Tuple[float, float]
HEURISTIC_DISCLAIMER = (
    "HEURISTIC ONLY — approximate 13C ppm ranges, not experimental or quantum-accurate values."
)

_DEFAULT_CARBONYL_CENTERS: Dict[str, float] = {
    "aldehyde": 196.0,
    "ketone": 205.0,
    "ester": 170.0,
    "amide": 171.0,
    "acid": 176.0,
    "carboxylate": 180.0,
    "carbonate": 154.0,
    "urea": 160.0,
}

_HETERO_FAMILY_BASES: Dict[str, float] = {
    "pyridine": 142.0,
    "pyridazine": 146.0,
    "pyrimidine": 150.0,
    "pyrazine": 148.0,
    "pyrrole": 120.0,
    "imidazole": 134.0,
    "indole": 122.0,
    "quinoline": 145.0,
    "quinoxaline": 145.0,
    "quinazoline": 149.0,
    "triazine": 162.0,
}

_HETERO_CORR: Dict[str, float] = {
    "F": 22.0,
    "Cl": 10.0,
    "Br": 8.0,
    "I": 4.0,
    "O": 12.0,
    "N": 8.0,
    "S": 5.0,
    "P": 3.0,
}

_GROUP_DEFAULTS: Dict[str, Tuple[str, PpmRange]] = {
    "aldehyde": ("aldehyde C=O carbon", (190.0, 205.0)),
    "ketone": ("ketone C=O carbon", (195.0, 220.0)),
    "ester": ("ester C=O carbon", (160.0, 180.0)),
    "amide": ("amide C=O carbon", (160.0, 180.0)),
    "acid": ("acid C=O carbon", (170.0, 185.0)),
    "aromatic": ("Ar carbon", (110.0, 155.0)),
    "alkene": ("alkene carbon", (100.0, 150.0)),
    "alkyne": ("alkyne carbon", (65.0, 95.0)),
    "nitrile": ("nitrile carbon", (110.0, 125.0)),
    "alcohol": ("C-O carbon", (45.0, 85.0)),
    "amine": ("C-N carbon", (25.0, 70.0)),
}


def _cap_range(center: float, half_width: float) -> PpmRange:
    lo = max(-10.0, center - half_width)
    hi = min(300.0, center + half_width)
    if hi <= lo:
        hi = lo + 0.5
    return (round(lo, 1), round(hi, 1))



def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0



def _safe_mid(ppm_range: PpmRange) -> float:
    return round((float(ppm_range[0]) + float(ppm_range[1])) / 2.0, 1)


class LegacyMappingMixin(Mapping[str, Any]):
    """Backward-compatible dict-like view for legacy CLI/tests."""

    def to_legacy_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def tolegacydict(self) -> Dict[str, Any]:
        return self.to_legacy_dict()

    def __getitem__(self, key: str) -> Any:
        return self.to_legacy_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_legacy_dict())

    def __len__(self) -> int:
        return len(self.to_legacy_dict())

    def keys(self):
        return self.to_legacy_dict().keys()

    def items(self):
        return self.to_legacy_dict().items()

    def values(self):
        return self.to_legacy_dict().values()

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_legacy_dict().get(key, default)


_LegacyMappingMixin = LegacyMappingMixin


@dataclass(frozen=True)
class CarbonEnvironment:
    """Structured heuristic annotation for one or more 13C environments."""

    label: str
    ppm_range: PpmRange
    description: str
    rationale: str = ""
    atom_indices: Tuple[int, ...] = field(default_factory=tuple)
    carbon_count: int = 1
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
    n_attached_h: int = 0
    is_quaternary: bool = False
    carbonyl_type: Optional[str] = None
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
    def atomindices(self) -> Tuple[int, ...]:
        return self.atom_indices

    @property
    def carboncount(self) -> int:
        return self.carbon_count

    @property
    def attachedelements(self) -> Tuple[str, ...]:
        return self.attached_elements

    @property
    def nattachedh(self) -> int:
        return self.n_attached_h

    @property
    def isquaternary(self) -> bool:
        return self.is_quaternary

    @property
    def carbonyltype(self) -> Optional[str]:
        return self.carbonyl_type

    @property
    def heterocyclefamily(self) -> Optional[str]:
        return self.heterocycle_family

    @property
    def heteroposition(self) -> Optional[str]:
        return self.hetero_position

    def features_dict(self) -> Dict[str, Any]:
        hyb_map = {"SP3": 0, "SP2": 1, "SP": 2, "AROMATIC": 3, "OTHER": 4}
        return {
            "ppm_mid_heuristic": self.ppm_mid,
            "carbon_count": self.carbon_count,
            "hybridization": hyb_map.get(self.hybridization, 4),
            "is_aromatic": int(self.is_aromatic),
            "is_heteroaromatic": int(self.is_heteroaromatic),
            "n_attached_h": self.n_attached_h,
            "is_quaternary": int(self.is_quaternary),
            "attached_O": int("O" in self.attached_elements),
            "attached_N": int("N" in self.attached_elements),
            "attached_S": int("S" in self.attached_elements),
            "attached_F": int("F" in self.attached_elements),
            "attached_Cl": int("Cl" in self.attached_elements),
            "attached_Br": int("Br" in self.attached_elements),
            "attached_I": int("I" in self.attached_elements),
            "heterocycle_family": self.heterocycle_family or "",
            "hetero_position": self.hetero_position or "",
            "carbonyl_type": self.carbonyl_type or "",
        }

    def featuresdict(self) -> Dict[str, Any]:
        return self.features_dict()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload.update(
            {
                "ppmrange": self.ppm_range,
                "ppmmid": self.ppm_mid,
                "environmentclass": self.environment_class,
                "atomindices": self.atom_indices,
                "carboncount": self.carbon_count,
                "attachedelements": self.attached_elements,
                "nattachedh": self.n_attached_h,
                "isquaternary": self.is_quaternary,
                "carbonyltype": self.carbonyl_type,
                "heterocyclefamily": self.heterocycle_family,
                "heteroposition": self.hetero_position,
            }
        )
        return payload

    def todict(self) -> Dict[str, Any]:
        return self.to_dict()



def _legacy_cnmr_label(env: CarbonEnvironment) -> str:
    label = env.label.lower()
    env_class = (env.environment_class or "").lower()
    carbonyl = (env.carbonyl_type or "").lower()

    if carbonyl == "acid" or "acid c=o" in label:
        return "Carboxylic acid carbonyl"
    if carbonyl == "ester":
        return "Ester carbonyl"
    if carbonyl == "amide":
        return "Amide carbonyl"
    if carbonyl == "aldehyde":
        return "Aldehyde carbonyl"
    if carbonyl == "ketone":
        return "Ketone carbonyl"
    if "benzylic" in env_class or "benzylic" in label:
        return "Benzylic carbon"
    if env.hybridization == "SP3" and env.n_attached_h >= 3:
        return "CH3 aliphatic carbon"
    if env.hybridization == "SP3" and env.n_attached_h == 2:
        return "CH2 aliphatic carbon"
    if env.hybridization == "SP3" and env.n_attached_h == 1:
        return "CH aliphatic carbon"
    if env.is_aromatic and env.n_attached_h > 0:
        return "Aromatic CH carbon"
    if env.is_aromatic and env.n_attached_h == 0:
        return "Aromatic quaternary carbon"
    return env.label


@dataclass
class CarbonNMRPrediction(LegacyMappingMixin):
    """Top-level heuristic 13C NMR prediction result."""

    smiles: str
    environments: List[CarbonEnvironment] = field(default_factory=list)
    atom_environments: List[CarbonEnvironment] = field(default_factory=list)
    is_heuristic: bool = True
    warnings: List[str] = field(default_factory=list)
    total_carbons: int = 0
    n_signals: int = 0
    disclaimer: str = HEURISTIC_DISCLAIMER

    @property
    def totalcarbons(self) -> int:
        return self.total_carbons

    @property
    def nsignals(self) -> int:
        return self.n_signals

    @property
    def atomenvironments(self) -> List[CarbonEnvironment]:
        return self.atom_environments

    @property
    def isheuristic(self) -> bool:
        return self.is_heuristic

    def summary(self) -> str:
        if not self.environments:
            return "No carbon environments predicted (HEURISTIC — approximate)."
        lines = [
            "13C NMR Prediction (HEURISTIC — approximate only)",
            f"SMILES: {self.smiles}",
            f"Signals: {self.n_signals}",
            f"Total carbons: {self.total_carbons}",
            "",
            f"{'Label':<28} {'Range (ppm)':<16} {'Count':<6} Annotation",
            "-" * 92,
        ]
        for env in self.environments:
            lo, hi = env.ppm_range
            lines.append(
                f"{env.label:<28} {lo:.1f}-{hi:.1f}     {env.carbon_count:<6} {env.annotation or env.description}"
            )
        if self.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f" - {w}" for w in self.warnings)
        return "\n".join(lines)

    def to_legacy_dict(self) -> Dict[str, float]:
        source = self.environments or self.atom_environments
        out: Dict[str, float] = {}
        for idx, env in enumerate(source, start=1):
            key = _legacy_cnmr_label(env)
            value = float(env.ppm_mid if env.ppm_mid else _safe_mid(env.ppm_range))
            if key in out:
                key = f"{key} [{idx}]"
            out[key] = round(value, 1)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smiles": self.smiles,
            "environments": [e.to_dict() for e in self.environments],
            "atom_environments": [e.to_dict() for e in self.atom_environments],
            "is_heuristic": self.is_heuristic,
            "warnings": list(self.warnings),
            "total_carbons": self.total_carbons,
            "n_signals": self.n_signals,
            "disclaimer": self.disclaimer,
            "totalcarbons": self.total_carbons,
            "nsignals": self.n_signals,
            "isheuristic": self.is_heuristic,
            "legacy": self.to_legacy_dict(),
        }

    def todict(self) -> Dict[str, Any]:
        return self.to_dict()


CarbonPrediction = CarbonNMRPrediction


class MLCarbonShiftModel:
    """Placeholder for future trained 13C models."""

    def is_available(self) -> bool:
        return False

    def predict(self, features: Dict[str, Any]) -> Optional[float]:
        logger.debug("MLCarbonShiftModel.predict called without a loaded model.")
        return None

    @classmethod
    def load(cls, path: str) -> "MLCarbonShiftModel":
        raise NotImplementedError("No trained ML carbon-shift model is available yet.")



def summary_text(environments: Iterable[CarbonEnvironment]) -> str:
    return "\n".join(
        f"{e.label}: {e.ppm_range[0]:.1f}-{e.ppm_range[1]:.1f} ppm ({e.carbon_count}C) — HEURISTIC"
        for e in environments
    )



def summarytext(environments: Iterable[CarbonEnvironment]) -> str:
    return summary_text(environments)



def predict_from_groups(groups: Dict[str, int]) -> List[CarbonEnvironment]:
    if not isinstance(groups, dict):
        raise TypeError("groups must be a dict[str, int]")

    envs: List[CarbonEnvironment] = []
    idx = 0
    for key, count in groups.items():
        try:
            n = int(count)
        except Exception:
            n = 1
        if n <= 0:
            continue

        lowered = str(key).lower()
        matched = None
        for token, payload in _GROUP_DEFAULTS.items():
            if token in lowered:
                matched = payload
                break
        if matched is None:
            matched = (str(key), (10.0, 60.0))

        label, ppm_range = matched
        for _ in range(n):
            envs.append(
                CarbonEnvironment(
                    label=label,
                    ppm_range=ppm_range,
                    description=f"{label} from group-only heuristic",
                    rationale=f"Group-only heuristic from input key: {key}",
                    atom_indices=(idx,),
                    carbon_count=1,
                    ppm_mid=_safe_mid(ppm_range),
                    annotation=f"{label} (group-derived)",
                    environment_class=label.lower().replace(" ", "_"),
                    confidence="low",
                    carbonyl_type=(label.split()[0].lower() if "c=o" in label.lower() else None),
                )
            )
            idx += 1
    return envs


class CarbonNMRPredictor:
    """Heuristic 13C NMR predictor using only local structural rules."""

    def __init__(
        self,
        aromatic_center: float = 128.0,
        sp3_center: float = 25.0,
        window: float = 6.0,
        aggregate_equivalent: bool = True,
        carbonyl_centers: Optional[Dict[str, float]] = None,
        ml_model: Optional[MLCarbonShiftModel] = None,
    ) -> None:
        self.aromatic_center = float(aromatic_center)
        self.sp3_center = float(sp3_center)
        self.window = float(window)
        self.aggregate_equivalent = bool(aggregate_equivalent)
        self.carbonyl_centers = {**_DEFAULT_CARBONYL_CENTERS, **(carbonyl_centers or {})}
        self._ml = ml_model or MLCarbonShiftModel()
        self.warnings: List[str] = []

    def predict_from_smiles(self, smiles: str) -> CarbonNMRPrediction:
        if not isinstance(smiles, str) or not smiles.strip():
            raise ValueError("smiles must be a non-empty string")
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            raise ValueError(f"Could not parse SMILES: {smiles}")
        return self.predict(mol)

    def predict(self, mol: Chem.Mol) -> CarbonNMRPrediction:
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
        atom_envs: List[CarbonEnvironment] = []
        for atom in mol_h.GetAtoms():
            if atom.GetAtomicNum() != 6:
                continue
            try:
                atom_envs.append(self._predict_atom(atom, mol_h))
            except Exception as exc:
                msg = f"Failed to classify carbon atom {atom.GetIdx()}: {exc}"
                logger.exception(msg)
                self.warnings.append(msg)

        atom_envs.sort(key=lambda e: e.ppm_range[0], reverse=True)
        environments = self._aggregate(atom_envs) if self.aggregate_equivalent else atom_envs

        if not atom_envs:
            self.warnings.append("No carbon environments detected.")
        if mol_h.GetNumHeavyAtoms() > 80:
            self.warnings.append("Large molecule detected; heuristic reliability may decrease.")

        return CarbonNMRPrediction(
            smiles=smiles,
            environments=environments,
            atom_environments=atom_envs,
            is_heuristic=True,
            warnings=list(self.warnings),
            total_carbons=len(atom_envs),
            n_signals=len(environments),
        )

    def _predict_atom(self, atom: Chem.Atom, mol: Chem.Mol) -> CarbonEnvironment:
        carbonyl_type = self._carbonyl_type(atom, mol)
        if carbonyl_type:
            center = self.carbonyl_centers.get(carbonyl_type, 170.0)
            return self._make_env(
                atom,
                center=center,
                label=f"{carbonyl_type} C=O carbon",
                annotation=f"{carbonyl_type.title()} carbonyl carbon",
                env_class=f"{carbonyl_type}_carbonyl",
                description="Carbonyl carbon environment",
                rationale=self._carbonyl_rationale(carbonyl_type),
                confidence="high",
                carbonyl_type=carbonyl_type,
                family=None,
                position=None,
                half_width=max(self.window, 5.0),
            )

        if self._is_nitrile_carbon(atom, mol):
            return self._make_env(
                atom,
                center=118.0,
                label="nitrile carbon",
                annotation="C≡N carbon",
                env_class="nitrile",
                description="Nitrile carbon",
                rationale="sp carbon triple-bonded to nitrogen",
                confidence="high",
                carbonyl_type=None,
                family=None,
                position=None,
                half_width=max(self.window - 1.0, 4.0),
            )

        family, position = self._heteroaromatic_context(atom, mol)
        if atom.GetIsAromatic():
            return self._predict_aromatic(atom, mol, family, position)

        hyb = atom.GetHybridization().name
        if hyb == "SP2":
            return self._predict_sp2(atom, mol)
        if hyb == "SP":
            return self._predict_sp(atom)
        return self._predict_sp3(atom, mol)

    def _predict_aromatic(
        self,
        atom: Chem.Atom,
        mol: Chem.Mol,
        family: Optional[str],
        position: Optional[str],
    ) -> CarbonEnvironment:
        n_h = self._hydrogen_count(atom)
        is_q = n_h == 0
        direct = self._direct_heteroatoms(atom)

        if family:
            base = _HETERO_FAMILY_BASES.get(family, self.aromatic_center + 8.0)
            pos_corr = {"alpha": 6.0, "beta": 0.0, "gamma": 2.0, "remote": -1.0, None: 0.0}[position]
            q_corr = 8.0 if is_q else 0.0
            if family in {"pyrrole", "indole"} and not is_q:
                q_corr -= 4.0
            center = base + pos_corr + q_corr + self._aromatic_substituent_correction(atom, mol)
            return self._make_env(
                atom,
                center=center,
                label=f"Ar {family} carbon",
                annotation=self._hetero_annotation(family, position, is_q),
                env_class=f"{family}_{'Cq' if is_q else 'CH'}",
                description="Heteroaromatic carbon",
                rationale=f"Heteroaromatic {family} carbon" + (f" at {position} position" if position else ""),
                confidence="medium",
                carbonyl_type=None,
                family=family,
                position=position,
                half_width=self.window,
            )

        if is_q and "O" in direct:
            center = 157.0
            label = "Ar C-O carbon"
            annotation = "Phenoxy / anisole-type ipso carbon"
            env_class = "aryl_C_O"
            rationale = "Aromatic quaternary carbon directly bonded to oxygen"
        elif is_q and "N" in direct:
            center = 146.0
            label = "Ar C-N carbon"
            annotation = "Aniline-type ipso carbon"
            env_class = "aryl_C_N"
            rationale = "Aromatic quaternary carbon directly bonded to nitrogen"
        elif is_q and any(x in direct for x in {"F", "Cl", "Br", "I"}):
            center = 132.0 + self._direct_hetero_correction(atom)
            label = "Ar C-X carbon"
            annotation = "Aryl halide ipso carbon"
            env_class = "aryl_C_X"
            rationale = "Aromatic quaternary carbon directly bonded to halogen"
        elif is_q:
            center = self.aromatic_center + 10.0 + self._aromatic_substituent_correction(atom, mol)
            label = "Ar quaternary carbon"
            annotation = "Quaternary aromatic carbon"
            env_class = "aromatic_Cq"
            rationale = "Benzenoid quaternary aromatic carbon"
        else:
            center = self.aromatic_center + self._aromatic_substituent_correction(atom, mol)
            label = "Ar CH carbon"
            annotation = "Benzenoid aromatic CH carbon"
            env_class = "aromatic_CH"
            rationale = "Benzenoid aromatic CH carbon"

        return self._make_env(
            atom,
            center=center,
            label=label,
            annotation=annotation,
            env_class=env_class,
            description="Aromatic carbon environment",
            rationale=rationale,
            confidence="high",
            carbonyl_type=None,
            family=family,
            position=position,
            half_width=self.window,
        )

    def _predict_sp2(self, atom: Chem.Atom, mol: Chem.Mol) -> CarbonEnvironment:
        n_h = self._hydrogen_count(atom)
        base = 126.0 if n_h > 0 else 138.0
        center = base + self._direct_hetero_correction(atom) + self._second_shell_correction(atom, mol)
        return self._make_env(
            atom,
            center=center,
            label="sp2 alkene carbon",
            annotation="Olefinic carbon",
            env_class="alkene_CH" if n_h > 0 else "alkene_Cq",
            description="sp2 carbon",
            rationale="sp2 alkene carbon with simple heteroatom correction",
            confidence="medium",
            carbonyl_type=None,
            family=None,
            position=None,
            half_width=self.window + 1.0,
        )

    def _predict_sp(self, atom: Chem.Atom) -> CarbonEnvironment:
        n_h = self._hydrogen_count(atom)
        center = 78.0 if n_h > 0 else 84.0
        return self._make_env(
            atom,
            center=center,
            label="sp alkyne carbon",
            annotation="sp carbon in alkyne",
            env_class="alkyne_CH" if n_h > 0 else "alkyne_C",
            description="sp carbon",
            rationale="sp carbon with heuristic alkyne range",
            confidence="medium",
            carbonyl_type=None,
            family=None,
            position=None,
            half_width=max(self.window - 1.0, 4.0),
        )

    def _predict_sp3(self, atom: Chem.Atom, mol: Chem.Mol) -> CarbonEnvironment:
        n_h = self._hydrogen_count(atom)
        if self._is_alpha_to_oxygen(atom):
            center = 63.0 + self._second_shell_correction(atom, mol)
            label = "sp3 alpha-oxygen carbon"
            annotation = "sp3 carbon alpha to oxygen"
            env_class = "alpha_oxygen"
            rationale = "Direct oxygen adjacency strongly deshields 13C"
        elif self._is_alpha_to_nitrogen(atom):
            center = 46.0 + self._second_shell_correction(atom, mol)
            label = "sp3 alpha-nitrogen carbon"
            annotation = "sp3 carbon alpha to nitrogen"
            env_class = "alpha_nitrogen"
            rationale = "Direct nitrogen adjacency deshields 13C"
        elif self._is_alpha_to_sulfur(atom):
            center = 34.0 + self._second_shell_correction(atom, mol)
            label = "sp3 alpha-sulfur carbon"
            annotation = "sp3 carbon alpha to sulfur"
            env_class = "alpha_sulfur"
            rationale = "Direct sulfur adjacency modestly deshields 13C"
        elif self._is_alpha_to_halogen(atom):
            center = 45.0 + self._direct_hetero_correction(atom)
            label = "sp3 alpha-halogen carbon"
            annotation = "sp3 carbon alpha to halogen"
            env_class = "alpha_halogen"
            rationale = "Direct halogen adjacency strongly alters 13C shielding"
        elif self._is_alpha_to_carbonyl(atom, mol):
            center = max(self.sp3_center + 11.0, 36.0) + self._second_shell_correction(atom, mol)
            label = "sp3 alpha-carbonyl carbon"
            annotation = "sp3 carbon alpha to carbonyl"
            env_class = "alpha_carbonyl"
            rationale = "Alpha-carbonyl carbons are downfield vs simple alkyl carbons"
        elif self._is_benzylic(atom):
            center = max(self.sp3_center + 6.0, 31.0) + self._second_shell_correction(atom, mol)
            label = "sp3 benzylic carbon"
            annotation = "Benzylic sp3 carbon"
            env_class = "benzylic"
            rationale = "Benzylic carbons are deshielded by adjacent aromatic systems"
        elif self._is_allylic(atom):
            center = max(self.sp3_center + 4.0, 28.0) + self._second_shell_correction(atom, mol)
            label = "sp3 allylic carbon"
            annotation = "Allylic sp3 carbon"
            env_class = "allylic"
            rationale = "Allylic carbons are moderately deshielded by adjacent sp2 systems"
        elif self._is_propargylic(atom):
            center = max(self.sp3_center + 2.0, 26.0) + self._second_shell_correction(atom, mol)
            label = "sp3 propargylic carbon"
            annotation = "Propargylic sp3 carbon"
            env_class = "propargylic"
            rationale = "Propargylic carbons are modestly deshielded by neighboring sp carbon"
        else:
            offset = -10.0 if n_h >= 3 else 0.0 if n_h == 2 else 10.0 if n_h == 1 else 15.0
            center = self.sp3_center + offset + self._second_shell_correction(atom, mol)
            label = "sp3 alkyl carbon"
            annotation = "Simple alkyl carbon"
            env_class = "alkyl_sp3"
            rationale = "Default sp3 alkyl assignment based on substitution level"

        return self._make_env(
            atom,
            center=center,
            label=label,
            annotation=annotation,
            env_class=env_class,
            description="sp3 carbon",
            rationale=rationale,
            confidence="high",
            carbonyl_type=None,
            family=None,
            position=None,
            half_width=self.window,
        )

    def _make_env(
        self,
        atom: Chem.Atom,
        center: float,
        label: str,
        annotation: str,
        env_class: str,
        description: str,
        rationale: str,
        confidence: str,
        carbonyl_type: Optional[str],
        family: Optional[str],
        position: Optional[str],
        half_width: float,
    ) -> CarbonEnvironment:
        n_h = self._hydrogen_count(atom)
        if self._ml.is_available():
            ml_val = self._ml.predict(
                {
                    "atom_idx": atom.GetIdx(),
                    "ppm_mid_heuristic": center,
                    "hybridization": atom.GetHybridization().name,
                    "is_aromatic": int(atom.GetIsAromatic()),
                    "n_attached_h": n_h,
                    "carbonyl_type": carbonyl_type or "",
                    "heterocycle_family": family or "",
                    "hetero_position": position or "",
                }
            )
            if ml_val is not None:
                center = float(ml_val)

        return CarbonEnvironment(
            label=label,
            ppm_range=_cap_range(center, half_width),
            description=description,
            rationale=rationale,
            atom_indices=(atom.GetIdx(),),
            carbon_count=1,
            ppm_mid=round(center, 1),
            annotation=annotation,
            environment_class=env_class,
            confidence=confidence,
            hybridization=atom.GetHybridization().name,
            is_aromatic=bool(atom.GetIsAromatic()),
            is_heteroaromatic=bool(atom.GetIsAromatic() and family is not None),
            heterocycle_family=family,
            hetero_position=position,
            ring_size=self._smallest_ring_size(atom),
            attached_elements=tuple(sorted(n.GetSymbol() for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)),
            n_attached_h=n_h,
            is_quaternary=(n_h == 0),
            carbonyl_type=carbonyl_type,
        )

    def _aggregate(self, atom_envs: List[CarbonEnvironment]) -> List[CarbonEnvironment]:
        if not atom_envs:
            return []

        groups: List[List[CarbonEnvironment]] = []
        for env in atom_envs:
            placed = False
            for grp in groups:
                head = grp[0]
                if (
                    env.environment_class == head.environment_class
                    and env.carbonyl_type == head.carbonyl_type
                    and env.heterocycle_family == head.heterocycle_family
                    and env.hetero_position == head.hetero_position
                    and env.attached_elements == head.attached_elements
                    and abs(env.ppm_mid - head.ppm_mid) <= 2.0
                ):
                    grp.append(env)
                    placed = True
                    break
            if not placed:
                groups.append([env])

        merged: List[CarbonEnvironment] = []
        rank = {"high": 2, "medium": 1, "low": 0}
        for grp in groups:
            head = grp[0]
            lo = min(e.ppm_range[0] for e in grp)
            hi = max(e.ppm_range[1] for e in grp)
            worst = min(grp, key=lambda e: rank.get(e.confidence, 0)).confidence
            merged.append(
                CarbonEnvironment(
                    label=head.label,
                    ppm_range=(round(lo, 1), round(hi, 1)),
                    description=head.description,
                    rationale=head.rationale,
                    atom_indices=tuple(i for e in grp for i in e.atom_indices),
                    carbon_count=sum(e.carbon_count for e in grp),
                    ppm_mid=_mean([e.ppm_mid for e in grp]),
                    annotation=head.annotation,
                    environment_class=head.environment_class,
                    confidence=worst,
                    hybridization=head.hybridization,
                    is_aromatic=head.is_aromatic,
                    is_heteroaromatic=head.is_heteroaromatic,
                    heterocycle_family=head.heterocycle_family,
                    hetero_position=head.hetero_position,
                    ring_size=head.ring_size,
                    attached_elements=head.attached_elements,
                    n_attached_h=head.n_attached_h,
                    is_quaternary=head.is_quaternary,
                    carbonyl_type=head.carbonyl_type,
                )
            )

        return sorted(merged, key=lambda e: e.ppm_range[0], reverse=True)

    def _hydrogen_count(self, atom: Chem.Atom) -> int:
        explicit_h = sum(1 for nbr in atom.GetNeighbors() if nbr.GetAtomicNum() == 1)
        implicit_h = int(atom.GetNumImplicitHs())
        total = explicit_h + implicit_h
        if total == 0:
            total = int(atom.GetTotalNumHs())
        return total

    def _direct_heteroatoms(self, atom: Chem.Atom) -> Tuple[str, ...]:
        return tuple(sorted(n.GetSymbol() for n in atom.GetNeighbors() if n.GetAtomicNum() not in {1, 6}))

    def _direct_hetero_correction(self, atom: Chem.Atom) -> float:
        return round(sum(_HETERO_CORR.get(sym, 0.0) for sym in self._direct_heteroatoms(atom)), 1)

    def _second_shell_correction(self, atom: Chem.Atom, mol: Chem.Mol) -> float:
        total = 0.0
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 1:
                continue
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetIdx() == atom.GetIdx() or nbr2.GetAtomicNum() in {1, 6}:
                    continue
                total += 0.35 * _HETERO_CORR.get(nbr2.GetSymbol(), 0.0)
        return round(total, 1)

    def _smallest_ring_size(self, atom: Chem.Atom) -> int:
        info = atom.GetOwningMol().GetRingInfo()
        sizes = [len(r) for r in info.AtomRings() if atom.GetIdx() in r]
        return min(sizes) if sizes else 0

    def _is_alpha_to_oxygen(self, atom: Chem.Atom) -> bool:
        return any(n.GetSymbol() == "O" for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)

    def _is_alpha_to_nitrogen(self, atom: Chem.Atom) -> bool:
        return any(n.GetSymbol() == "N" for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)

    def _is_alpha_to_sulfur(self, atom: Chem.Atom) -> bool:
        return any(n.GetSymbol() == "S" for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)

    def _is_alpha_to_halogen(self, atom: Chem.Atom) -> bool:
        return any(n.GetSymbol() in {"F", "Cl", "Br", "I"} for n in atom.GetNeighbors() if n.GetAtomicNum() != 1)

    def _is_alpha_to_carbonyl(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        return any(self._carbonyl_type(n, mol) is not None for n in atom.GetNeighbors() if n.GetAtomicNum() == 6)

    def _is_benzylic(self, atom: Chem.Atom) -> bool:
        return atom.GetAtomicNum() == 6 and not atom.GetIsAromatic() and any(
            n.GetAtomicNum() == 6 and n.GetIsAromatic() for n in atom.GetNeighbors()
        )

    def _is_allylic(self, atom: Chem.Atom) -> bool:
        return atom.GetAtomicNum() == 6 and not atom.GetIsAromatic() and any(
            n.GetAtomicNum() != 1 and n.GetHybridization().name == "SP2" and not n.GetIsAromatic()
            for n in atom.GetNeighbors()
        )

    def _is_propargylic(self, atom: Chem.Atom) -> bool:
        return atom.GetAtomicNum() == 6 and any(
            n.GetAtomicNum() != 1 and n.GetHybridization().name == "SP" for n in atom.GetNeighbors()
        )

    def _is_nitrile_carbon(self, atom: Chem.Atom, mol: Chem.Mol) -> bool:
        if atom.GetAtomicNum() != 6 or atom.GetHybridization().name != "SP":
            return False
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() != 7:
                continue
            bond = mol.GetBondBetweenAtoms(atom.GetIdx(), nbr.GetIdx())
            if bond and bond.GetBondTypeAsDouble() == 3.0:
                return True
        return False

    def _carbonyl_type(self, atom: Chem.Atom, mol: Chem.Mol) -> Optional[str]:
        if atom.GetAtomicNum() != 6:
            return None

        has_oxo = False
        hetero_single: List[Chem.Atom] = []
        carbon_single = 0
        for nbr in atom.GetNeighbors():
            bond = mol.GetBondBetweenAtoms(atom.GetIdx(), nbr.GetIdx())
            if nbr.GetAtomicNum() == 8 and bond and bond.GetBondTypeAsDouble() == 2.0:
                has_oxo = True
            elif bond and bond.GetBondTypeAsDouble() == 1.0 and nbr.GetAtomicNum() != 1:
                if nbr.GetAtomicNum() in {7, 8, 16}:
                    hetero_single.append(nbr)
                elif nbr.GetAtomicNum() == 6:
                    carbon_single += 1

        if not has_oxo:
            return None

        n_h = self._hydrogen_count(atom)
        symbols = [a.GetSymbol() for a in hetero_single]
        if n_h == 1:
            return "aldehyde"
        if symbols.count("N") >= 2:
            return "urea"
        if "N" in symbols:
            return "amide"
        oxy_single = [a for a in hetero_single if a.GetAtomicNum() == 8]
        if len(oxy_single) >= 2:
            return "carbonate"
        if oxy_single:
            if any(self._hydrogen_count(o) > 0 for o in oxy_single):
                return "acid"
            return "ester"
        if carbon_single >= 1:
            return "ketone"
        return "ketone"

    def _carbonyl_rationale(self, carbonyl_type: str) -> str:
        reasons = {
            "aldehyde": "Carbonyl carbon with one attached hydrogen",
            "ketone": "Carbonyl carbon flanked by carbon substituents",
            "ester": "Carbonyl carbon adjacent to single-bond oxygen",
            "amide": "Carbonyl carbon adjacent to nitrogen",
            "acid": "Carbonyl carbon adjacent to hydroxyl oxygen",
            "carboxylate": "Carboxylate-like carbonyl heuristic",
            "carbonate": "Carbonyl carbon adjacent to two oxygens",
            "urea": "Carbonyl carbon adjacent to multiple nitrogens",
        }
        return reasons.get(carbonyl_type, "Carbonyl carbon recognized from C=O motif")

    def _heteroaromatic_context(self, atom: Chem.Atom, mol: Chem.Mol) -> Tuple[Optional[str], Optional[str]]:
        if not atom.GetIsAromatic() or atom.GetAtomicNum() != 6:
            return (None, None)

        ring_sizes = sorted({len(r) for r in mol.GetRingInfo().AtomRings() if atom.GetIdx() in r})
        aromatic_n = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 7)
        aromatic_o = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 8)
        aromatic_s = sum(1 for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 16)
        fused_count = sum(1 for r in mol.GetRingInfo().AtomRings() if atom.GetIdx() in r)
        pos = self._hetero_position(atom, mol)

        if 6 in ring_sizes and aromatic_n == 1 and aromatic_o == 0 and aromatic_s == 0:
            return ("pyridine", pos)
        if 6 in ring_sizes and aromatic_n == 2 and fused_count <= 1:
            n_atoms = [a for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 7]
            if len(n_atoms) == 2:
                dist = len(Chem.GetShortestPath(mol, n_atoms[0].GetIdx(), n_atoms[1].GetIdx()))
                if dist <= 3:
                    return ("pyridazine", pos)
                if dist == 4:
                    return ("pyrimidine", pos)
                return ("pyrazine", pos)
        if 6 in ring_sizes and aromatic_n >= 3:
            return ("triazine", pos)
        if 5 in ring_sizes and 6 in ring_sizes and aromatic_n >= 1:
            return ("indole", pos)
        if 5 in ring_sizes and aromatic_n == 1 and aromatic_o == 0 and aromatic_s == 0:
            return ("pyrrole", None)
        if 5 in ring_sizes and aromatic_n >= 2:
            return ("imidazole", None)
        if fused_count >= 2 and aromatic_n == 1:
            return ("quinoline", pos)
        if fused_count >= 2 and aromatic_n == 2:
            n_atoms = [a for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() == 7]
            if len(n_atoms) == 2:
                dist = len(Chem.GetShortestPath(mol, n_atoms[0].GetIdx(), n_atoms[1].GetIdx()))
                if dist <= 3:
                    return ("quinazoline", pos)
            return ("quinoxaline", pos)
        return (None, None)

    def _hetero_position(self, atom: Chem.Atom, mol: Chem.Mol) -> Optional[str]:
        hetero = [a for a in mol.GetAtoms() if a.GetIsAromatic() and a.GetAtomicNum() in {7, 8, 16}]
        if not hetero:
            return None

        distances: List[int] = []
        for h in hetero:
            try:
                distances.append(len(Chem.GetShortestPath(mol, atom.GetIdx(), h.GetIdx())) - 1)
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

    def _hetero_annotation(self, family: str, position: Optional[str], is_quaternary: bool) -> str:
        kind = "quaternary" if is_quaternary else "CH"
        if position:
            return f"{family} {position}-position {kind} carbon"
        return f"{family} {kind} carbon"

    def _aromatic_substituent_correction(self, atom: Chem.Atom, mol: Chem.Mol) -> float:
        ewg = 0
        edg = 0
        for nbr in atom.GetNeighbors():
            if nbr.GetAtomicNum() == 1:
                continue
            if nbr.GetAtomicNum() in {7, 8, 16} and not nbr.GetIsAromatic():
                edg += 1
            if self._carbonyl_type(nbr, mol) is not None:
                ewg += 1
            for nbr2 in nbr.GetNeighbors():
                if nbr2.GetIdx() == atom.GetIdx() or nbr2.GetAtomicNum() == 1:
                    continue
                if nbr2.GetAtomicNum() in {7, 8, 16} and not nbr2.GetIsAromatic():
                    edg += 1
                if self._carbonyl_type(nbr2, mol) is not None:
                    ewg += 1
                if nbr2.GetAtomicNum() in {9, 17, 35, 53}:
                    ewg += 1
        return round(2.5 * ewg - 1.5 * edg, 1)



def predict_from_smiles(smiles: str, ml_model: Optional[MLCarbonShiftModel] = None) -> CarbonNMRPrediction:
    return CarbonNMRPredictor(ml_model=ml_model).predict_from_smiles(smiles)



def predictfromsmiles(smiles: str, ml_model: Optional[MLCarbonShiftModel] = None) -> CarbonNMRPrediction:
    return predict_from_smiles(smiles, ml_model=ml_model)



def predict_carbon_nmr(
    mol_or_smiles: Any,
    ml_model: Optional[MLCarbonShiftModel] = None,
) -> CarbonNMRPrediction:
    predictor = CarbonNMRPredictor(ml_model=ml_model)
    if isinstance(mol_or_smiles, str):
        return predictor.predict_from_smiles(mol_or_smiles)
    if mol_or_smiles is None:
        raise ValueError("predict_carbon_nmr received None")
    return predictor.predict(mol_or_smiles)



def predictcarbonnmr(
    mol_or_smiles: Any,
    ml_model: Optional[MLCarbonShiftModel] = None,
) -> CarbonNMRPrediction:
    return predict_carbon_nmr(mol_or_smiles, ml_model=ml_model)



def predictfromgroups(groups: Dict[str, int]) -> List[CarbonEnvironment]:
    return predict_from_groups(groups)


__all__ = [
    "CarbonEnvironment",
    "CarbonNMRPrediction",
    "CarbonNMRPredictor",
    "CarbonPrediction",
    "HEURISTIC_DISCLAIMER",
    "LegacyMappingMixin",
    "MLCarbonShiftModel",
    "PpmRange",
    "predict_carbon_nmr",
    "predict_from_groups",
    "predict_from_smiles",
    "predictcarbonnmr",
    "predictfromgroups",
    "predictfromsmiles",
    "summary_text",
    "summarytext",
]
