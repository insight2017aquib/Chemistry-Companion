"""
spectra/functional_group_detector.py
====================================
Structured functional-group detection using shared result models.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Iterable

from rdkit import Chem

from core.models import FunctionalGroupMatch, FunctionalGroupReport
from core.molecule_utils import load_molecule


@dataclass(frozen=True, slots=True)
class FGDefinition:
    key: str = ""
    name: str = ""
    smarts: str = ""
    category: str = "general"
    priority: int = 1
    description: str = ""
    ir_bands: tuple[tuple[str, int, int], ...] = field(default_factory=tuple)


FGMatch = FunctionalGroupMatch
FGReport = FunctionalGroupReport


def get_registry() -> dict[str, FGDefinition]:
    return {
        "alcohol": FGDefinition(
            key="alcohol",
            name="Alcohol",
            smarts="[OX2H]",
            category="oxygen",
            priority=10,
            description="Alcohol functional group",
            ir_bands=(("O-H stretch", 3200, 3600),),
        ),
        "phenol": FGDefinition(
            key="phenol",
            name="Phenol",
            smarts="c[OX2H]",
            category="oxygen",
            priority=11,
            description="Phenolic hydroxyl group",
            ir_bands=(("O-H stretch", 3100, 3500),),
        ),
        "carboxylic_acid": FGDefinition(
            key="carboxylic_acid",
            name="Carboxylic Acid",
            smarts="C(=O)[OX2H1]",
            category="oxygen",
            priority=12,
            description="Carboxylic acid group",
            ir_bands=(("O-H stretch", 2500, 3300),),
        ),
        "ester": FGDefinition(
            key="ester",
            name="Ester",
            smarts="[#6][CX3](=O)[OX2H0][#6]",
            category="oxygen",
            priority=13,
            description="Ester group",
            ir_bands=(("C=O stretch", 1735, 1750),),
        ),
        "ether": FGDefinition(
            key="ether",
            name="Ether",
            smarts="[OD2]([#6])[#6]",
            category="oxygen",
            priority=14,
            description="Ether group",
            ir_bands=(("C-O stretch", 1050, 1150),),
        ),
        "aldehyde": FGDefinition(
            key="aldehyde",
            name="Aldehyde",
            smarts="[CX3H1](=O)[#6]",
            category="oxygen",
            priority=15,
            description="Aldehyde group",
            ir_bands=(("C=O stretch", 1720, 1740),),
        ),
        "ketone": FGDefinition(
            key="ketone",
            name="Ketone",
            smarts="[#6][CX3](=O)[#6]",
            category="oxygen",
            priority=16,
            description="Ketone group",
            ir_bands=(("C=O stretch", 1710, 1725),),
        ),
        "epoxide": FGDefinition(
            key="epoxide",
            name="Epoxide",
            smarts="C1CO1",
            category="oxygen",
            priority=17,
            description="Epoxide ring",
            ir_bands=(("C-O stretch", 1250, 1300),),
        ),
        "primary_amine": FGDefinition(
            key="primary_amine",
            name="Primary Amine",
            smarts="[NX3;H2][CX4]",
            category="nitrogen",
            priority=20,
            description="Primary amine group",
            ir_bands=(("N-H stretch", 3300, 3500),),
        ),
        "secondary_amine": FGDefinition(
            key="secondary_amine",
            name="Secondary Amine",
            smarts="[NX3;H1]([CX4])[CX4]",
            category="nitrogen",
            priority=21,
            description="Secondary amine group",
            ir_bands=(("N-H stretch", 3300, 3450),),
        ),
        "tertiary_amine": FGDefinition(
            key="tertiary_amine",
            name="Tertiary Amine",
            smarts="[NX3;H0]([CX4])([CX4])[CX4]",
            category="nitrogen",
            priority=22,
            description="Tertiary amine group",
            ir_bands=(("C-N stretch", 1200, 1360),),
        ),
        "amide": FGDefinition(
            key="amide",
            name="Amide",
            smarts="[NX3][CX3](=O)[#6]",
            category="nitrogen",
            priority=23,
            description="Amide group",
            ir_bands=(("C=O stretch", 1630, 1690),),
        ),
        "nitrile": FGDefinition(
            key="nitrile",
            name="Nitrile",
            smarts="[CX2]#N",
            category="nitrogen",
            priority=24,
            description="Nitrile group",
            ir_bands=(("C#N stretch", 2210, 2260),),
        ),
        "nitro": FGDefinition(
            key="nitro",
            name="Nitro",
            smarts="[$([NX3](=O)=O),$([N+](=O)[O-])]",
            category="nitrogen",
            priority=25,
            description="Nitro group",
            ir_bands=(("N-O stretch", 1500, 1600),),
        ),
        "imine": FGDefinition(
            key="imine",
            name="Imine",
            smarts="[NX2]=C",
            category="nitrogen",
            priority=26,
            description="Imine group",
            ir_bands=(("C=N stretch", 1640, 1690),),
        ),
        "guanidine": FGDefinition(
            key="guanidine",
            name="Guanidine",
            smarts="NC(=N)N",
            category="nitrogen",
            priority=27,
            description="Guanidine group",
            ir_bands=(("C=N stretch", 1620, 1690),),
        ),
        "thiol": FGDefinition(
            key="thiol",
            name="Thiol",
            smarts="[#16X2H]",
            category="sulfur",
            priority=30,
            description="Thiol group",
            ir_bands=(("S-H stretch", 2550, 2600),),
        ),
        "thioether": FGDefinition(
            key="thioether",
            name="Thioether",
            smarts="[SX2][#6]",
            category="sulfur",
            priority=31,
            description="Thioether group",
            ir_bands=(("C-S stretch", 700, 740),),
        ),
        "sulfonamide": FGDefinition(
            key="sulfonamide",
            name="Sulfonamide",
            smarts="[NX3][SX4](=O)(=O)[#6]",
            category="sulfur",
            priority=32,
            description="Sulfonamide group",
            ir_bands=(("S=O stretch", 1320, 1360),),
        ),
        "fluoride": FGDefinition(
            key="fluoride",
            name="Fluoride",
            smarts="[F]",
            category="halogen",
            priority=40,
            description="Fluoride substituent",
            ir_bands=(("C-F stretch", 1000, 1400),),
        ),
        "chloride": FGDefinition(
            key="chloride",
            name="Chloride",
            smarts="[Cl]",
            category="halogen",
            priority=41,
            description="Chloride substituent",
            ir_bands=(("C-Cl stretch", 600, 800),),
        ),
        "bromide": FGDefinition(
            key="bromide",
            name="Bromide",
            smarts="[Br]",
            category="halogen",
            priority=42,
            description="Bromide substituent",
            ir_bands=(("C-Br stretch", 500, 650),),
        ),
        "iodide": FGDefinition(
            key="iodide",
            name="Iodide",
            smarts="[I]",
            category="halogen",
            priority=43,
            description="Iodide substituent",
            ir_bands=(("C-I stretch", 500, 650),),
        ),
        "aromatic_ring": FGDefinition(
            key="aromatic_ring",
            name="Aromatic Ring",
            smarts="a1aaaaa1",
            category="aromatic",
            priority=50,
            description="Aromatic ring system",
            ir_bands=(("C=C stretch", 1450, 1600),),
        ),
        "alkene": FGDefinition(
            key="alkene",
            name="Alkene",
            smarts="C=C",
            category="aromatic",
            priority=51,
            description="Alkene double bond",
            ir_bands=(("C=C stretch", 1620, 1680),),
        ),
        "alkyne": FGDefinition(
            key="alkyne",
            name="Alkyne",
            smarts="C#C",
            category="aromatic",
            priority=52,
            description="Alkyne triple bond",
            ir_bands=(("C#C stretch", 2100, 2260),),
        ),
        "phosphate": FGDefinition(
            key="phosphate",
            name="Phosphate",
            smarts="P(=O)(O)(O)",
            category="phosphorus",
            priority=60,
            description="Phosphate ester",
            ir_bands=(("P=O stretch", 1150, 1250),),
        ),
    }

FUNCTIONAL_GROUP_REGISTRY = get_registry()


def register_custom_group(
    key: str,
    definition: FGDefinition,
    registry: dict[str, FGDefinition] | None = None,
) -> dict[str, FGDefinition]:
    registry = registry or FUNCTIONAL_GROUP_REGISTRY
    updated = dict(registry)
    if key in registry:
        logging.getLogger(__name__).warning(
            "Existing functional group registry key %r already exists and will be overwritten.",
            key,
        )
    updated[key] = replace(definition, key=key)
    return updated


class FunctionalGroupDetector:
    def __init__(self, registry: dict[str, FGDefinition] | None = None) -> None:
        self._registry = registry or get_registry()
        self._compiled, self._failed_patterns = self._compile_registry(self._registry)

    def _compile_registry(self, registry: dict[str, FGDefinition]):
        compiled: dict[str, tuple[FGDefinition, Chem.Mol]] = {}
        failed: list[str] = []
        for key, definition in registry.items():
            patt = Chem.MolFromSmarts(definition.smarts)
            if patt is not None:
                compiled[key] = (definition, patt)
            else:
                failed.append(key)
        return compiled, failed

    def detect(self, mol, use_chirality: bool = False) -> FunctionalGroupReport:
        if mol is None:
            raise ValueError("Cannot detect functional groups for None molecule.")

        # The current functional-group rules are not stereochemistry-sensitive,
        # but the flag is accepted for compatibility with callers that may
        # request chirality-aware processing.
        _ = use_chirality

        smiles = Chem.MolToSmiles(mol)
        found_matches: list[FunctionalGroupMatch] = []

        for key, (definition, patt) in self._compiled.items():
            submatches = mol.GetSubstructMatches(patt)
            if not submatches:
                continue

            for atom_tuple in submatches:
                found_matches.append(
                    FunctionalGroupMatch(
                        key=definition.key,
                        name=definition.name,
                        atom_indices=(tuple(atom_tuple),),
                        count=1,
                        category=definition.category,
                        ir_bands=definition.ir_bands,
                    )
                )

        counts = Counter(match.key for match in found_matches)

        name_by_key = {definition.key: definition.name for definition, _ in self._compiled.values()}
        category_by_key = {definition.key: definition.category for definition, _ in self._compiled.values()}

        keys = sorted(counts.keys())
        names = [name_by_key[key] for key in keys if key in name_by_key]
        categories = sorted({category_by_key[key] for key in keys if key in category_by_key})
        summary_text = (
            ", ".join(f"{name_by_key[key]} ({counts[key]})" for key in keys)
            if keys
            else "No functional groups detected."
        )

        return FunctionalGroupReport(
            smiles=smiles,
            counts=dict(counts),
            matches=found_matches,
            names=names,
            keys=keys,
            categories=categories,
            summary_text=summary_text,
            failed_patterns=self._failed_patterns,
        )

    def detect_from_smiles(self, smiles: str) -> FunctionalGroupReport:
        try:
            record = load_molecule(smiles=smiles)
        except ValueError as exc:
            raise ValueError("could not parse SMILES") from exc
        return self.detect(record.rdkit_mol)

    @property
    def registry_size(self) -> int:
        return len(self._registry)

    @property
    def available_categories(self) -> list[str]:
        return sorted({definition.category for definition in self._registry.values()})

    def registry_summary(self) -> str:
        return f"{self.registry_size} functional-group definitions across {len(self.available_categories)} categories."


def detect_functional_groups(smiles_or_mol: str | Chem.Mol) -> FunctionalGroupReport:
    if isinstance(smiles_or_mol, Chem.Mol):
        return FunctionalGroupDetector().detect(smiles_or_mol)
    return FunctionalGroupDetector().detect_from_smiles(smiles_or_mol)


__all__ = [
    "FGDefinition",
    "FGMatch",
    "FGReport",
    "FunctionalGroupDetector",
    "detect_functional_groups",
    "get_registry",
    "register_custom_group",
]