"""
api/serializers.py
==================
Convert pipeline/service results into JSON- and template-friendly dicts.
"""

from __future__ import annotations

from typing import Any

from core.models import (
    AnalysisResult,
    CarbonNMRPrediction,
    DescriptorRecord,
    FunctionalGroupReport,
    IRPrediction,
    MoleculeRecord,
    ProtonNMRPrediction,
)


def _safe_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {}


def serialize_molecule(mol: MoleculeRecord | None) -> dict[str, Any]:
    if mol is None:
        return {}
    return {
        "smiles": mol.smiles,
        "inchi": mol.inchi,
        "inchikey": mol.inchikey,
        "name": mol.name,
        "formula": mol.formula,
        "mol_weight": mol.mol_weight,
        "exact_mass": mol.exact_mass,
        "atom_counts": mol.atom_counts,
        "num_atoms": mol.num_atoms,
        "num_heavy_atoms": mol.num_heavy_atoms,
        "num_bonds": mol.num_bonds,
        "num_rings": mol.num_rings,
        "is_aromatic": mol.is_aromatic,
    }


def serialize_descriptors(desc: DescriptorRecord | dict | None) -> dict[str, Any]:
    if desc is None:
        return {}
    if isinstance(desc, dict):
        return desc
    aromatic_rings = desc.functional_groups.get("aromatic_ring", 0) if desc.functional_groups else 0
    return {
        "formula": desc.formula,
        "molecular_weight": desc.molecular_weight,
        "exact_mass": desc.exact_mass,
        "logp": desc.logp,
        "tpsa": desc.tpsa,
        "hbd": desc.hbd,
        "hba": desc.hba,
        "rotatable_bonds": desc.rotatable_bonds,
        "ring_count": desc.ring_count,
        "aromatic_ring_count": aromatic_rings,
        "heavy_atom_count": desc.heavy_atom_count,
        "formal_charge": desc.formal_charge,
        "fraction_csp3": desc.fraction_csp3,
        "functional_groups": dict(desc.functional_groups),
        "bertz_ct": desc.bertz_ct,
    }


def serialize_functional_groups(
    fg_report: FunctionalGroupReport | None,
    fg_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    if fg_report is None:
        return {
            "keys": list((fg_counts or {}).keys()),
            "names": [],
            "counts": fg_counts or {},
            "categories": [],
            "matches": [],
            "by_category": {},
            "summary_text": "",
        }
    matches = []
    for match in fg_report.matches:
        matches.append({
            "key": match.key,
            "name": match.name,
            "count": match.count,
            "category": match.category or "other",
            "atom_indices": [list(idx) for idx in match.atom_indices],
        })
    return {
        "keys": fg_report.keys,
        "names": fg_report.names,
        "counts": fg_report.counts,
        "categories": fg_report.categories,
        "matches": matches,
        "by_category": {
            cat: [m for m in matches if m["category"] == cat]
            for cat in {m["category"] for m in matches}
        },
        "summary_text": fg_report.summary_text,
        "total_groups": fg_report.total_groups,
    }


def serialize_ir(pred: IRPrediction | Any | None) -> dict[str, Any] | None:
    if pred is None:
        return None
    if hasattr(pred, "to_dict"):
        data = pred.to_dict()
    else:
        data = _safe_dict(pred)
    data["is_heuristic"] = True
    data.setdefault(
        "disclaimer",
        "Heuristic IR prediction — approximate peak ranges, not experimental data.",
    )
    return data


def serialize_proton_nmr(pred: ProtonNMRPrediction | Any | None) -> dict[str, Any] | None:
    if pred is None:
        return None
    data = pred.to_dict() if hasattr(pred, "to_dict") else _safe_dict(pred)
    data["is_heuristic"] = True
    data.setdefault(
        "disclaimer",
        "Approximate ¹H NMR prediction — estimated ppm ranges and multiplicities.",
    )
    return data


def serialize_carbon_nmr(pred: CarbonNMRPrediction | Any | None) -> dict[str, Any] | None:
    if pred is None:
        return None
    data = pred.to_dict() if hasattr(pred, "to_dict") else _safe_dict(pred)
    data["is_heuristic"] = True
    data.setdefault(
        "disclaimer",
        "Heuristic ¹³C NMR prediction — approximate chemical shift ranges.",
    )
    return data


def serialize_analysis_result(result: AnalysisResult) -> dict[str, Any]:
    """Full analysis payload for API and templates."""
    mol = result.molecule
    descriptors = serialize_descriptors(result.descriptors)
    fg = serialize_functional_groups(result.functional_group_report, result.functional_groups)

    errors = []
    if result.metadata.get("error"):
        errors.append(str(result.metadata["error"]))

    return {
        "molecule": serialize_molecule(mol),
        "descriptors": descriptors,
        "descriptor_summary": result.descriptor_summary or "",
        "functional_groups": result.functional_groups or {},
        "functional_group_report": fg,
        "ir_prediction": serialize_ir(result.ir_prediction),
        "proton_nmr_prediction": serialize_proton_nmr(result.proton_nmr_prediction),
        "carbon_nmr_prediction": serialize_carbon_nmr(result.carbon_nmr_prediction),
        "visualization_path": str(result.visualization_path) if result.visualization_path else None,
        "export_paths": result.metadata.get("export_paths", {}),
        "metadata": dict(result.metadata),
        "warnings": result.metadata.get("warnings", []),
        "errors": errors,
        "status": "error" if errors else "success",
    }
