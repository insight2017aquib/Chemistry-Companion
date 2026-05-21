"""Cell-safe formatting helpers for workbook rendering."""

from __future__ import annotations

from typing import Any


EMPTY_DISPLAY = ""


def safe_cell_value(value: Any) -> Any:
    """Return a scalar value suitable for an Excel cell."""
    if value is None:
        return EMPTY_DISPLAY
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    return str(value)


def display_header(key: str) -> str:
    special = {
        "record_id": "Record ID",
        "row_index": "Input Row",
        "smiles": "SMILES",
        "inchi": "InChI",
        "inchikey": "InChIKey",
        "molecular_weight": "Mol. Weight",
        "exact_mass": "Exact Mass",
        "num_atoms": "Atoms",
        "num_heavy_atoms": "Heavy Atoms",
        "num_rings": "Rings",
        "is_aromatic": "Aromatic",
        "logp": "LogP",
        "tpsa": "TPSA",
        "hbd": "HBD",
        "hba": "HBA",
        "rotatable_bonds": "Rot. Bonds",
        "ring_count": "Ring Count",
        "heavy_atom_count": "Heavy Atoms",
        "formal_charge": "Charge",
        "fraction_csp3": "Fraction Csp3",
        "bertz_ct": "Bertz CT",
        "ro5_pass": "Ro5 Pass",
        "ro5_violations": "Ro5 Violations",
        "heterocycles_detected": "Heterocycles",
        "group_key": "Group Key",
        "group_name": "Functional Group",
        "atom_indices": "Atom Indices",
        "lower_cm1": "Lower cm^-1",
        "upper_cm1": "Upper cm^-1",
        "shift_ppm": "Shift ppm",
        "shift_low_ppm": "Low ppm",
        "shift_high_ppm": "High ppm",
        "carbon_count": "Carbon Count",
        "attached_elements": "Attached Elements",
        "attached_hydrogens": "Attached H",
        "is_quaternary": "Quaternary",
        "generated_at_utc": "Generated UTC",
    }
    if key in special:
        return special[key]
    return key.replace("_", " ").title()


def number_format_for(key: str) -> str | None:
    lowered = key.lower()
    if lowered in {"lower_cm1", "upper_cm1", "row_index", "num_atoms", "num_heavy_atoms", "num_rings", "hbd", "hba", "ring_count", "heavy_atom_count", "formal_charge", "ro5_violations", "heterocycles_detected", "count", "carbon_count", "attached_hydrogens"}:
        return "0"
    if lowered in {"molecular_weight", "exact_mass", "bertz_ct"}:
        return "0.000"
    if lowered in {"logp", "tpsa", "fraction_csp3", "shift_ppm", "shift_low_ppm", "shift_high_ppm", "integration", "confidence"}:
        return "0.00"
    return None
