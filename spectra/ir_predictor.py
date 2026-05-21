"""
chemistry_companion/spectra/ir_predictor.py
============================================
Heuristic IR absorption predictor — Phase 2, v4.1 (Fixed & Enhanced)

Key Improvements in this version:
- IRPrediction now exposes BOTH .bands and .peaks
- Significantly improved heterocyclic C=N detection (1500-1620 cm⁻¹)
- Better support for quinoxaline, quinazoline, imidazole, purine, etc.
- Full backward compatibility + cleaner API
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from spectra.functional_group_detector import FunctionalGroupDetector, FGReport

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _BandSpec:
    label: str
    low_cm: int
    high_cm: int
    intensity: str
    description: str


_IR_BAND_LIBRARY: Dict[str, List[_BandSpec]] = {
    "alcohol": [
        _BandSpec("O–H stretch", 3200, 3550, "broad", "Broad O–H; position shifts with H-bonding"),
        _BandSpec("C–O stretch", 950, 1260, "strong", "C–O single-bond; varies with substitution"),
        _BandSpec("O–H bend", 650, 900, "medium", "Out-of-plane O–H deformation"),
    ],
    "phenol": [
        _BandSpec("O–H stretch", 3200, 3550, "broad", "Often broader than aliphatic alcohol"),
        _BandSpec("C–O stretch", 1150, 1260, "strong", "Ar–O; higher freq than aliphatic"),
        _BandSpec("Ar–OH bend", 750, 900, "medium", "Out-of-plane deformation"),
    ],
    "carboxylic_acid": [
        _BandSpec("O–H stretch", 2500, 3300, "broad", "Very broad; highly characteristic"),
        _BandSpec("C=O stretch", 1700, 1725, "strong", "Strongest band in spectrum"),
        _BandSpec("C–O stretch", 1210, 1320, "strong", "C–O single-bond stretch"),
        _BandSpec("O–H bend", 875, 930, "medium", "Broad out-of-plane O–H bend"),
    ],
    "ester": [
        _BandSpec("C=O stretch", 1735, 1750, "strong", "Higher freq than ketone/acid"),
        _BandSpec("C–O–C stretch (asym)", 1150, 1300, "strong", "Often two bands"),
        _BandSpec("C–O–C stretch (sym)", 1000, 1150, "medium", "Symmetric C–O–C"),
    ],
    "ether": [
        _BandSpec("C–O–C stretch (asym)", 1070, 1150, "strong", "Most diagnostic ether band"),
        _BandSpec("C–O–C stretch (sym)", 800, 970, "weak", "Often weak or absent"),
    ],
    "aldehyde": [
        _BandSpec("C=O stretch", 1720, 1740, "strong", "Slightly higher than ketone"),
        _BandSpec("C–H stretch (aldehyde)", 2700, 2850, "medium", "Fermi resonance doublet"),
    ],
    "ketone": [
        _BandSpec("C=O stretch", 1705, 1725, "strong", "Most diagnostic ketone band"),
        _BandSpec("C–C(=O)–C stretch", 1000, 1300, "medium", "C–C bonds flanking carbonyl"),
    ],
    "epoxide": [
        _BandSpec("C–O–C stretch (epoxide)", 800, 950, "strong", "Two bands ~830 & ~910 cm⁻¹"),
        _BandSpec("Ring breathing", 750, 840, "medium", "Symmetric ring breathing"),
    ],
    "primary_amine": [
        _BandSpec("N–H stretch", 3300, 3500, "medium", "Doublet (asym + sym)"),
        _BandSpec("N–H bend", 1560, 1650, "strong", "Scissoring; very diagnostic"),
        _BandSpec("C–N stretch", 1000, 1250, "medium", "Aliphatic C–N stretch"),
    ],
    "secondary_amine": [
        _BandSpec("N–H stretch", 3300, 3350, "medium", "Single band; weaker than primary"),
        _BandSpec("N–H bend", 1500, 1600, "weak", "Often weak"),
        _BandSpec("C–N stretch", 1100, 1200, "medium", "C–N single-bond stretch"),
    ],
    "tertiary_amine": [
        _BandSpec("C–N stretch", 1030, 1230, "medium", "No N–H bands present"),
    ],
    "amide": [
        _BandSpec("N–H stretch", 3100, 3500, "broad", "Primary: doublet ~3350 & ~3180"),
        _BandSpec("C=O stretch (Amide I)", 1630, 1690, "strong", "Lower freq than ester/ketone"),
        _BandSpec("N–H bend (Amide II)", 1510, 1570, "strong", "Very diagnostic for 2° amide"),
        _BandSpec("C–N stretch (Amide III)", 1200, 1400, "medium", "Less diagnostic"),
    ],
    "nitrile": [
        _BandSpec("C≡N stretch", 2200, 2260, "medium", "Sharp band in triple-bond region"),
    ],
    "nitro": [
        _BandSpec("N=O stretch (asym)", 1500, 1570, "strong", "Strongest nitro band"),
        _BandSpec("N=O stretch (sym)", 1300, 1370, "strong", "Symmetric N=O stretch"),
    ],
    "imine": [
        _BandSpec("C=N stretch", 1620, 1690, "medium", "Similar region to C=O"),
        _BandSpec("N–H stretch", 3280, 3380, "medium", "Present only in primary imines"),
    ],
    "guanidine": [
        _BandSpec("C=N stretch", 1580, 1700, "strong", "Strong C=N in guanidinium"),
        _BandSpec("N–H stretch", 3200, 3450, "broad", "Multiple N–H bands"),
    ],
    "thiol": [
        _BandSpec("S–H stretch", 2550, 2600, "weak", "Characteristic weak S–H"),
        _BandSpec("C–S stretch", 600, 700, "weak", "Very weak"),
    ],
    "thioether": [
        _BandSpec("C–S stretch", 600, 700, "weak", "C–S single bond; weak"),
    ],
    "sulfonamide": [
        _BandSpec("S=O stretch (asym)", 1300, 1370, "strong", "Very strong"),
        _BandSpec("S=O stretch (sym)", 1140, 1200, "strong", "Symmetric S=O"),
        _BandSpec("N–H stretch", 3200, 3380, "medium", "Sulfonamide N–H"),
        _BandSpec("S–N stretch", 870, 930, "medium", "S–N linkage"),
    ],
    "fluoride": [
        _BandSpec("C–F stretch", 1000, 1400, "strong", "Very strong; broad region"),
    ],
    "chloride": [
        _BandSpec("C–Cl stretch", 600, 800, "strong", "Position depends on substitution"),
    ],
    "bromide": [
        _BandSpec("C–Br stretch", 500, 700, "strong", "Below 700 cm⁻¹"),
    ],
    "iodide": [
        _BandSpec("C–I stretch", 480, 620, "strong", "Lowest of C–halogen series"),
    ],
    "aromatic_ring": [
        _BandSpec("Ar C–H stretch", 3000, 3100, "medium", "Aromatic C–H above 3000 cm⁻¹"),
        _BandSpec("Ar C=C stretch", 1450, 1600, "medium", "Two bands ~1500 and ~1600"),
        _BandSpec("Ar C–H oop bend", 690, 900, "strong", "Substitution pattern indicator"),
    ],
    "alkene": [
        _BandSpec("=C–H stretch", 3000, 3100, "medium", "Vinylic C–H"),
        _BandSpec("C=C stretch", 1620, 1680, "variable", "Conjugation affects intensity"),
        _BandSpec("=C–H oop bend", 650, 990, "strong", "Geometry-sensitive position"),
    ],
    "alkyne": [
        _BandSpec("≡C–H stretch", 3250, 3350, "strong", "Terminal alkyne; sharp"),
        _BandSpec("C≡C stretch", 2100, 2260, "variable", "Internal may be absent"),
    ],
    "phosphate": [
        _BandSpec("P=O stretch", 1100, 1300, "strong", "Very strong P=O"),
        _BandSpec("P–O stretch", 900, 1050, "strong", "P–O–C linkage"),
    ],
}

_HETEROCYCLE_IR_BANDS: Dict[str, List[Tuple[Tuple[int, int], str, str]]] = {
    "quinoxaline": [
        ((1580, 1620), "medium", "C=N stretch (quinoxaline)"),
        ((1490, 1540), "medium", "Ring C=C/C=N coupled stretch"),
        ((720, 760), "strong", "Ring oop bend"),
    ],
    "quinazoline": [
        ((1580, 1620), "medium", "C=N stretch (quinazoline)"),
        ((1490, 1540), "medium", "Ring C=C/C=N coupled stretch"),
        ((720, 760), "strong", "Ring oop bend"),
    ],
    "imidazole": [
        ((1500, 1580), "medium", "C=N / ring stretch"),
        ((3100, 3300), "broad", "N–H stretch (imidazole NH)"),
    ],
    "pyridine": [
        ((1580, 1600), "medium", "C=N stretch (pyridine ring)"),
        ((1470, 1500), "medium", "Ring C=C/C=N coupled stretch"),
    ],
    "pyrimidine": [
        ((1560, 1600), "medium", "C=N stretch (pyrimidine)"),
    ],
    "purine": [
        ((1580, 1620), "medium", "C=N stretch (purine)"),
    ],
    "benzimidazole": [
        ((1500, 1570), "medium", "C=N ring stretch"),
        ((3050, 3200), "broad", "N–H / Ar C–H stretch"),
    ],
    "indole": [
        ((3400, 3470), "medium", "N–H stretch (indole NH)"),
        ((1450, 1500), "medium", "Ring stretch"),
    ],
    "oxazole": [
        ((1560, 1610), "medium", "C=N stretch (oxazole)"),
    ],
    "thiazole": [
        ((1540, 1580), "medium", "C=N stretch (thiazole)"),
    ],
    "piperidine": [
        ((2800, 2950), "medium", "N–CH₂ stretch (ring)"),
    ],
    "morpholine": [
        ((2800, 2860), "medium", "N–CH₂ stretch"),
        ((1110, 1150), "strong", "C–O–C stretch (morpholine)"),
    ],
    "piperazine": [
        ((2800, 2950), "medium", "N–CH₂ stretch (ring)"),
    ],
}

_INTENSITY_MAP: Dict[str, str] = {
    "carboxylic_acid": "strong",
    "ester": "strong",
    "amide": "strong",
    "aldehyde": "strong",
    "ketone": "strong",
    "nitro": "strong",
    "alcohol": "medium",
    "phenol": "medium",
    "primary_amine": "medium",
    "secondary_amine": "medium",
    "nitrile": "medium",
    "aromatic_ring": "medium",
    "alkene": "medium",
}


def _intensity_for(key: str) -> str:
    return _INTENSITY_MAP.get(key, "weak")


def _normalise_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


@dataclass(frozen=True)
class IRBand:
    fg_key: str
    fg_name: str
    label: str
    low_cm: int
    high_cm: int
    mid_cm: int
    intensity: str
    description: str
    is_heuristic: bool = field(default=True)

    @property
    def lowcm(self) -> int:
        return self.low_cm

    @property
    def highcm(self) -> int:
        return self.high_cm

    @property
    def midcm(self) -> int:
        return self.mid_cm

    @property
    def fgkey(self) -> str:
        return self.fg_key

    @property
    def fgname(self) -> str:
        return self.fg_name

    def __str__(self) -> str:
        return f"{self.low_cm:>5}–{self.high_cm:<5} cm⁻¹ [{self.intensity:>8}] {self.label} ← {self.fg_name}"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "lowcm": self.low_cm,
                "highcm": self.high_cm,
                "midcm": self.mid_cm,
                "fgkey": self.fg_key,
                "fgname": self.fg_name,
            }
        )
        return data


@dataclass(frozen=True)
class IRPeak:
    functional_group: str
    wavenumber_range: Tuple[int, int]
    intensity: str
    description: str
    heuristic_note: str = "HEURISTIC: approximate, functional-group based prediction"

    @property
    def functionalgroup(self) -> str:
        return self.functional_group

    @property
    def wavenumberrange(self) -> Tuple[int, int]:
        return self.wavenumber_range

    def __str__(self) -> str:
        lo, hi = self.wavenumber_range
        return f"{lo}–{hi} cm⁻¹ [{self.intensity:>8}] {self.description} ← {self.functional_group}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "functional_group": self.functional_group,
            "wavenumber_range": list(self.wavenumber_range),
            "intensity": self.intensity,
            "description": self.description,
            "heuristic_note": self.heuristic_note,
            "functionalgroup": self.functional_group,
            "wavenumberrange": list(self.wavenumber_range),
        }


class _LegacyMappingMixin(Mapping):
    def _legacy_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def __getitem__(self, key: str) -> Any:
        return self._legacy_dict()[key]

    def __iter__(self):
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


@dataclass
class IRPrediction(_LegacyMappingMixin):
    smiles: str
    bands: List[IRBand]
    fg_keys: List[str]
    fg_names: List[str]
    n_bands: int
    warnings: List[str]
    is_heuristic: bool = field(default=True)

    _REGIONS: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: {
            "X–H stretch (3000–3600)": (3000, 3600),
            "Triple bonds  (2000–3000)": (2000, 3000),
            "Double bonds  (1500–2000)": (1500, 2000),
            "Fingerprint   (600–1500)": (600, 1500),
        },
        repr=False,
    )

    @property
    def fgkeys(self) -> List[str]:
        return self.fg_keys

    @property
    def fgnames(self) -> List[str]:
        return self.fg_names

    @property
    def nbands(self) -> int:
        return self.n_bands

    @property
    def isheuristic(self) -> bool:
        return self.is_heuristic

    @property
    def peaks(self) -> List[IRPeak]:
        return [
            IRPeak(
                functional_group=b.fg_name,
                wavenumber_range=(b.low_cm, b.high_cm),
                intensity=b.intensity,
                description=b.description,
            )
            for b in self.bands
        ]

    def _legacy_dict(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for band in self.sorted_bands():
            base = band.fg_name
            key = base
            counter = 2
            while key in out:
                key = f"{base} ({counter})"
                counter += 1
            out[key] = {
                "range_cm1": (band.low_cm, band.high_cm),
                "intensity": band.intensity,
                "label": band.label,
                "description": band.description,
            }
        return out

    def sorted_bands(self) -> List[IRBand]:
        return sorted(self.bands, key=lambda b: b.mid_cm, reverse=True)

    def bands_by_region(self) -> Dict[str, List[IRBand]]:
        groups: Dict[str, List[IRBand]] = {k: [] for k in self._REGIONS}
        for band in self.bands:
            for rname, (lo, hi) in self._REGIONS.items():
                if lo <= band.mid_cm <= hi:
                    groups[rname].append(band)
                    break
        return groups

    def bands_by_fg(self) -> Dict[str, List[IRBand]]:
        result: Dict[str, List[IRBand]] = {}
        for band in self.bands:
            result.setdefault(band.fg_key, []).append(band)
        return result

    def summary(self) -> str:
        lines = [
            "=" * 68,
            " Chemistry Companion — Heuristic IR Prediction",
            " ⚠ All ranges approximate (±20–50 cm⁻¹). HEURISTIC ONLY.",
            "=" * 68,
            f" SMILES : {self.smiles}",
            f" Groups : {', '.join(self.fg_names) or 'none detected'}",
            f" Bands : {self.n_bands}",
            "-" * 68,
        ]
        if self.warnings:
            lines.append(" WARNINGS:")
            for w in self.warnings:
                lines.append(f" ⚠ {w}")
            lines.append("-" * 68)

        for region, rbands in self.bands_by_region().items():
            if rbands:
                lines.append(f"\n [{region}]")
                for b in sorted(rbands, key=lambda x: x.mid_cm, reverse=True):
                    lines.append(f" {b}")
                    lines.append(f"   → {b.description}")
        lines.append("=" * 68)
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smiles": self.smiles,
            "fg_keys": self.fg_keys,
            "fg_names": self.fg_names,
            "n_bands": self.n_bands,
            "is_heuristic": self.is_heuristic,
            "warnings": self.warnings,
            "bands": [b.to_dict() for b in self.sorted_bands()],
            "peaks": [p.to_dict() for p in self.peaks],
            "fgkeys": self.fg_keys,
            "fgnames": self.fg_names,
            "nbands": self.n_bands,
            "isheuristic": self.is_heuristic,
            "legacy": self._legacy_dict(),
        }


IRPredictionReport = IRPrediction


class IRPredictor:
    _ALIPHATIC_CH = _BandSpec(
        "C–H stretch (sp³)",
        2850,
        2960,
        "strong",
        "Aliphatic C–H; nearly universal in organic molecules",
    )

    def __init__(
        self,
        detector: Optional[FunctionalGroupDetector] = None,
        custom_bands: Optional[Dict[str, List]] = None,
    ) -> None:
        self._detector = detector or FunctionalGroupDetector()
        self._extra_bands: Dict[str, List[Tuple]] = {
            **_HETEROCYCLE_IR_BANDS,
            **(custom_bands or {}),
        }

    def predict(self, mol, use_chirality: bool = False) -> IRPrediction:
        if mol is None:
            raise ValueError("IRPredictor.predict() received None.")

        from rdkit import Chem

        smiles = Chem.MolToSmiles(mol)
        warnings: List[str] = []
        bands: List[IRBand] = []

        fg_report: FGReport = self._detector.detect(mol, use_chirality=use_chirality)

        if getattr(fg_report, "failed_patterns", None):
            warnings.append(f"SMARTS compile failures: {fg_report.failed_patterns}")

        for match in fg_report.matches:
            specs = _IR_BAND_LIBRARY.get(match.key)
            if specs:
                for spec in specs:
                    bands.append(
                        IRBand(
                            fg_key=match.key,
                            fg_name=match.name,
                            label=spec.label,
                            low_cm=spec.low_cm,
                            high_cm=spec.high_cm,
                            mid_cm=(spec.low_cm + spec.high_cm) // 2,
                            intensity=spec.intensity,
                            description=spec.description,
                        )
                    )
            else:
                extra = self._extra_bands.get(match.key) or self._extra_bands.get(_normalise_key(match.key))
                if extra:
                    for (w_range, intensity, label) in extra:
                        lo, hi = w_range
                        bands.append(
                            IRBand(
                                fg_key=match.key,
                                fg_name=match.name,
                                label=label,
                                low_cm=lo,
                                high_cm=hi,
                                mid_cm=(lo + hi) // 2,
                                intensity=intensity,
                                description=label,
                            )
                        )

        has_sp3 = any(a.GetHybridization().name == "SP3" and a.GetAtomicNum() == 6 for a in mol.GetAtoms())
        if has_sp3:
            sp = self._ALIPHATIC_CH
            bands.append(
                IRBand(
                    fg_key="aliphatic_ch",
                    fg_name="Aliphatic C–H",
                    label=sp.label,
                    low_cm=sp.low_cm,
                    high_cm=sp.high_cm,
                    mid_cm=(sp.low_cm + sp.high_cm) // 2,
                    intensity=sp.intensity,
                    description=sp.description,
                )
            )

        if not fg_report.matches:
            warnings.append("No functional groups detected.")

        n_heavy = mol.GetNumHeavyAtoms()
        if n_heavy > 80:
            warnings.append(f"Large molecule ({n_heavy} heavy atoms). Bands are fragment contributions only.")

        return IRPrediction(
            smiles=smiles,
            bands=bands,
            fg_keys=list(getattr(fg_report, "keys", [])),
            fg_names=list(getattr(fg_report, "names", [])),
            n_bands=len(bands),
            warnings=warnings,
        )

    def predict_from_smiles(self, smiles: str) -> IRPrediction:
        from rdkit import Chem

        if not smiles or not smiles.strip():
            raise ValueError("Empty SMILES string.")
        mol = Chem.MolFromSmiles(smiles.strip())
        if mol is None:
            raise ValueError(f"could not parse SMILES: {smiles!r}")
        return self.predict(mol)

    def predict_from_groups(self, groups: Dict[str, int]) -> List[IRPeak]:
        return predict_from_groups(groups, custom_bands=self._extra_bands)


def predict_ir(
    mol_or_smiles: Any,
    detector: Optional[FunctionalGroupDetector] = None,
    custom_bands: Optional[Dict[str, List]] = None,
) -> IRPrediction:
    predictor = IRPredictor(detector=detector, custom_bands=custom_bands)
    if isinstance(mol_or_smiles, str):
        return predictor.predict_from_smiles(mol_or_smiles)
    if mol_or_smiles is None:
        raise ValueError("predict_ir: received None.")
    return predictor.predict(mol_or_smiles)


def predict_from_groups(
    groups: Dict[str, int],
    custom_bands: Optional[Dict[str, List]] = None,
) -> List[IRPeak]:
    if not isinstance(groups, dict):
        raise TypeError(f"predict_from_groups: expected dict, got {type(groups).__name__}")

    extra = {**_HETEROCYCLE_IR_BANDS, **(custom_bands or {})}
    peaks: List[IRPeak] = []

    for fg_key, count in groups.items():
        if not fg_key or count <= 0:
            continue

        normalised = _normalise_key(fg_key)

        lib_specs = _IR_BAND_LIBRARY.get(fg_key) or _IR_BAND_LIBRARY.get(normalised)
        if lib_specs:
            intensity = _intensity_for(normalised)
            for spec in lib_specs:
                peaks.append(
                    IRPeak(
                        functional_group=fg_key,
                        wavenumber_range=(spec.low_cm, spec.high_cm),
                        intensity=intensity,
                        description=spec.label,
                    )
                )
            continue

        het_specs = extra.get(fg_key) or extra.get(normalised)
        if het_specs:
            for (w_range, intensity_label, label) in het_specs:
                peaks.append(
                    IRPeak(
                        functional_group=fg_key,
                        wavenumber_range=w_range,
                        intensity=intensity_label,
                        description=label,
                    )
                )
            continue

        peaks.append(
            IRPeak(
                functional_group=fg_key,
                wavenumber_range=(0, 0),
                intensity="unknown",
                description="No reference IR data available (heuristic)",
            )
        )

    peaks.sort(key=lambda p: p.wavenumber_range[0], reverse=True)
    return peaks


def summary_text(predictions: Iterable[IRPeak]) -> str:
    lines = []
    for p in predictions:
        lo, hi = p.wavenumber_range
        if lo == 0 and hi == 0:
            lines.append(f" {p.functional_group}: {p.description}")
        else:
            lines.append(f" {lo}–{hi} cm⁻¹ [{p.intensity:>8}] {p.description} ← {p.functional_group}")
    return "\n".join(lines) if lines else "(no IR bands predicted)"


__all__ = [
    "IRBand",
    "IRPeak",
    "IRPrediction",
    "IRPredictionReport",
    "IRPredictor",
    "predict_from_groups",
    "predict_ir",
    "summary_text",
]