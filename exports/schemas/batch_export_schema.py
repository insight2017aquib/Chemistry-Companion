"""Normalized intermediate export payload for all batch exporters."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCALAR_TYPES = (str, int, float, bool)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _plain(value: Any) -> Any:
    """Convert common app models into JSON-safe plain Python structures."""
    if value is None or isinstance(value, SCALAR_TYPES):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {f.name: _plain(getattr(value, f.name)) for f in fields(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    if hasattr(value, "todict") and callable(value.todict):
        return _plain(value.todict())
    if isinstance(value, Mapping):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(v) for v in value]
    return str(value)


def _as_dict(value: Any) -> dict[str, Any]:
    value = _plain(value)
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    value = _plain(value)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _coalesce(*values: Any, default: Any = "") -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        return value
    return default


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None


def _to_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "y", "1", "pass"}:
            return True
        if lowered in {"false", "no", "n", "0", "fail"}:
            return False
    return None


def _computed_ro5_violations(
    molecular_weight: float | None,
    logp: float | None,
    hbd: int | None,
    hba: int | None,
) -> int | None:
    if None in (molecular_weight, logp, hbd, hba):
        return None
    violations = 0
    if molecular_weight is not None and molecular_weight > 500:
        violations += 1
    if logp is not None and logp > 5:
        violations += 1
    if hbd is not None and hbd > 5:
        violations += 1
    if hba is not None and hba > 10:
        violations += 1
    return violations


def _is_truthy_failure(record: Mapping[str, Any]) -> bool:
    success = record.get("success")
    if success is False:
        return True
    status = str(record.get("status", "")).lower()
    if status in {"error", "failed", "failure"}:
        return True
    return bool(record.get("error")) and not record.get("molecule") and not record.get("descriptors")


def _record_id(position: int) -> str:
    return f"M{position:04d}"


def _normalise_counts(value: Any) -> dict[str, int]:
    value = _plain(value)
    if isinstance(value, str):
        if not value.strip():
            return {}
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            counts: dict[str, int] = {}
            for part in value.split(";"):
                if ":" not in part:
                    continue
                key, raw_count = part.split(":", 1)
                count = _to_int(raw_count.strip())
                if key.strip() and count is not None:
                    counts[key.strip()] = count
            return counts
    if not isinstance(value, Mapping):
        return {}
    counts = {}
    for key, count in value.items():
        numeric = _to_int(count)
        if numeric is not None and numeric > 0:
            counts[str(key)] = numeric
    return counts


def _title_from_key(key: str) -> str:
    return key.replace("_", " ").replace("-", " ").title()


def _format_atom_indices(value: Any) -> str:
    indices = _plain(value)
    if not indices:
        return ""
    if isinstance(indices, (int, float, str)):
        return str(indices)
    groups = []
    for item in indices:
        if isinstance(item, (list, tuple)):
            groups.append(",".join(str(v) for v in item))
        else:
            groups.append(str(item))
    return "; ".join(groups)


def _join_values(value: Any) -> str:
    value = _plain(value)
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _extract_records(data: Any) -> list[dict[str, Any]]:
    data = _plain(data)
    if data is None:
        return []
    if isinstance(data, Mapping):
        if "entries" in data:
            return [_as_dict(item) for item in _as_list(data.get("entries"))]
        if "results" in data:
            return [_as_dict(item) for item in _as_list(data.get("results"))]
        return [_as_dict(data)]
    if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
        return [_as_dict(item) for item in data]
    return []


@dataclass(slots=True)
class BatchExportPayload:
    """Normalized workbook-ready export model consumed by every exporter."""

    molecules: list[dict[str, Any]] = field(default_factory=list)
    descriptors: list[dict[str, Any]] = field(default_factory=list)
    functional_groups: list[dict[str, Any]] = field(default_factory=list)
    ir_predictions: list[dict[str, Any]] = field(default_factory=list)
    proton_nmr_predictions: list[dict[str, Any]] = field(default_factory=list)
    carbon_nmr_predictions: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "molecules": self.molecules,
            "descriptors": self.descriptors,
            "functional_groups": self.functional_groups,
            "ir_predictions": self.ir_predictions,
            "proton_nmr_predictions": self.proton_nmr_predictions,
            "carbon_nmr_predictions": self.carbon_nmr_predictions,
            "failures": self.failures,
            "metadata": self.metadata,
        }

    def summary_rows(self) -> list[dict[str, Any]]:
        descriptor_by_id = {row["record_id"]: row for row in self.descriptors}
        fg_counts = Counter(row["record_id"] for row in self.functional_groups)
        ir_counts = Counter(row["record_id"] for row in self.ir_predictions)
        proton_counts = Counter(row["record_id"] for row in self.proton_nmr_predictions)
        carbon_counts = Counter(row["record_id"] for row in self.carbon_nmr_predictions)

        rows: list[dict[str, Any]] = []
        for molecule in self.molecules:
            record_id = molecule["record_id"]
            descriptor = descriptor_by_id.get(record_id, {})
            rows.append({
                "record_id": record_id,
                "name": molecule.get("name", ""),
                "iupac": molecule.get("input_iupac", ""),
                "smiles": molecule.get("smiles", ""),
                "formula": molecule.get("formula", ""),
                "molecular_weight": molecule.get("molecular_weight"),
                "logp": descriptor.get("logp"),
                "tpsa": descriptor.get("tpsa"),
                "hbd": descriptor.get("hbd"),
                "hba": descriptor.get("hba"),
                "ro5_pass": descriptor.get("ro5_pass"),
                "functional_group_count": fg_counts[record_id],
                "ir_band_count": ir_counts[record_id],
                "proton_nmr_signal_count": proton_counts[record_id],
                "carbon_nmr_signal_count": carbon_counts[record_id],
                "status": "partial" if (
                    descriptor.get("logp") is None 
                    or fg_counts[record_id] == 0 
                    or ir_counts[record_id] == 0 
                    or proton_counts[record_id] == 0 
                    or carbon_counts[record_id] == 0
                ) else "success",
                "error": "Missing subsystems" if (
                    descriptor.get("logp") is None 
                    or fg_counts[record_id] == 0 
                    or ir_counts[record_id] == 0 
                    or proton_counts[record_id] == 0 
                    or carbon_counts[record_id] == 0
                ) else "",
            })

        for failure in self.failures:
            rows.append({
                "record_id": failure.get("record_id", ""),
                "name": failure.get("name", ""),
                "iupac": failure.get("input_iupac", ""),
                "smiles": failure.get("smiles", ""),
                "formula": "",
                "molecular_weight": None,
                "logp": None,
                "tpsa": None,
                "hbd": None,
                "hba": None,
                "ro5_pass": None,
                "functional_group_count": 0,
                "ir_band_count": 0,
                "proton_nmr_signal_count": 0,
                "carbon_nmr_signal_count": 0,
                "status": "failed",
                "error": failure.get("error", ""),
            })
        return rows


def _failure_row(raw: Mapping[str, Any], record_id: str, position: int) -> dict[str, Any]:
    input_block = _as_dict(raw.get("input"))
    return {
        "record_id": record_id,
        "row_index": _coalesce(raw.get("row_index"), input_block.get("row_index"), position),
        "input": _coalesce(raw.get("input_repr"), input_block.get("smiles"), input_block.get("iupac"), input_block.get("name")),
        "name": _coalesce(input_block.get("name"), raw.get("name")),
        "input_iupac": _coalesce(input_block.get("iupac"), input_block.get("iupac_name")),
        "smiles": _coalesce(input_block.get("smiles"), raw.get("smiles")),
        "error": _coalesce(raw.get("error"), "Unknown processing failure"),
        "stage": _coalesce(raw.get("stage"), "analysis"),
    }


def _success_sections(raw: Mapping[str, Any], record_id: str, position: int) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    input_block = _as_dict(raw.get("input"))
    molecule = _as_dict(raw.get("molecule"))
    descriptors = _as_dict(raw.get("descriptors"))

    flat = dict(raw)
    if not molecule:
        molecule = flat
    if not descriptors:
        descriptors = flat

    name = _coalesce(molecule.get("name"), input_block.get("name"), flat.get("name"))
    smiles = _coalesce(molecule.get("smiles"), input_block.get("smiles"), flat.get("smiles"), flat.get("input_repr"))
    formula = _coalesce(molecule.get("formula"), descriptors.get("formula"), flat.get("formula"))
    mol_weight = _coalesce(
        molecule.get("mol_weight"),
        molecule.get("molecular_weight"),
        descriptors.get("molecular_weight"),
        descriptors.get("mol_weight"),
        flat.get("mol_weight"),
    )
    exact_mass = _coalesce(molecule.get("exact_mass"), descriptors.get("exact_mass"), flat.get("exact_mass"))

    input_iupac = _coalesce(input_block.get("iupac"), input_block.get("iupac_name"))

    molecule_row = {
        "record_id": record_id,
        "row_index": _coalesce(flat.get("row_index"), input_block.get("row_index"), position),
        "name": name,
        "input_iupac": input_iupac,
        "smiles": smiles,
        "inchi": _coalesce(molecule.get("inchi"), flat.get("inchi")),
        "inchikey": _coalesce(molecule.get("inchikey"), flat.get("inchikey")),
        "formula": formula,
        "molecular_weight": _to_float(mol_weight),
        "exact_mass": _to_float(exact_mass),
        "num_atoms": _to_int(_coalesce(molecule.get("num_atoms"), flat.get("num_atoms"))),
        "num_heavy_atoms": _to_int(_coalesce(molecule.get("num_heavy_atoms"), flat.get("num_heavy_atoms"), descriptors.get("heavy_atom_count"))),
        "num_rings": _to_int(_coalesce(molecule.get("num_rings"), descriptors.get("ring_count"), flat.get("num_rings"))),
        "is_aromatic": _coalesce(molecule.get("is_aromatic"), flat.get("is_aromatic"), default=None),
    }

    mw_num = _to_float(mol_weight)
    exact_mass_num = _to_float(exact_mass)
    logp_num = _to_float(_coalesce(descriptors.get("logp"), flat.get("logp")))
    tpsa_num = _to_float(_coalesce(descriptors.get("tpsa"), flat.get("tpsa")))
    hbd_num = _to_int(_coalesce(descriptors.get("hbd"), flat.get("hbd")))
    hba_num = _to_int(_coalesce(descriptors.get("hba"), flat.get("hba")))
    ro5_pass = _to_bool(_coalesce(descriptors.get("ro5_pass"), descriptors.get("lipinski_pass"), flat.get("ro5_pass"), default=None))
    ro5_violations = _to_int(_coalesce(descriptors.get("ro5_violations"), descriptors.get("lipinski_violations"), flat.get("ro5_violations")))
    if ro5_violations is None:
        ro5_violations = _computed_ro5_violations(mw_num, logp_num, hbd_num, hba_num)
    if ro5_pass is None and ro5_violations is not None:
        ro5_pass = ro5_violations == 0

    descriptor_row = {
        "record_id": record_id,
        "name": name,
        "smiles": smiles,
        "formula": formula,
        "molecular_weight": mw_num,
        "exact_mass": exact_mass_num,
        "logp": logp_num,
        "tpsa": tpsa_num,
        "hbd": hbd_num,
        "hba": hba_num,
        "rotatable_bonds": _to_int(_coalesce(descriptors.get("rotatable_bonds"), flat.get("rotatable_bonds"))),
        "ring_count": _to_int(_coalesce(descriptors.get("ring_count"), molecule.get("num_rings"), flat.get("num_rings"))),
        "heavy_atom_count": _to_int(_coalesce(descriptors.get("heavy_atom_count"), molecule.get("num_heavy_atoms"), flat.get("num_heavy_atoms"))),
        "formal_charge": _to_int(descriptors.get("formal_charge")),
        "fraction_csp3": _to_float(descriptors.get("fraction_csp3")),
        "bertz_ct": _to_float(_coalesce(descriptors.get("bertz_ct"), flat.get("bertz_ct"))),
        "ro5_pass": ro5_pass,
        "ro5_violations": ro5_violations,
        "heterocycles_detected": _to_int(flat.get("heterocycles_detected")),
    }

    functional_group_rows = _functional_group_rows(raw, descriptors, record_id, name, smiles)
    ir_rows = _ir_rows(raw, record_id, name, smiles)
    proton_rows = _proton_rows(raw, record_id, name, smiles)
    carbon_rows = _carbon_rows(raw, record_id, name, smiles)

    return {
        "molecule": molecule_row,
        "descriptor": descriptor_row,
        "functional_groups": functional_group_rows,
        "ir": ir_rows,
        "proton": proton_rows,
        "carbon": carbon_rows,
    }


def _functional_group_rows(raw: Mapping[str, Any], descriptors: Mapping[str, Any], record_id: str, name: str, smiles: str) -> list[dict[str, Any]]:
    report = _as_dict(raw.get("functional_group_report"))
    matches = _as_list(report.get("matches"))
    rows: list[dict[str, Any]] = []

    if matches:
        for match in matches:
            item = _as_dict(match)
            rows.append({
                "record_id": record_id,
                "name": name,
                "smiles": smiles,
                "group_key": item.get("key", ""),
                "group_name": _coalesce(item.get("name"), _title_from_key(str(item.get("key", "")))),
                "category": item.get("category", ""),
                "count": _to_int(item.get("count")) or 1,
                "atom_indices": _format_atom_indices(item.get("atom_indices")),
            })
        return rows

    counts = _normalise_counts(report.get("counts"))
    if not counts:
        counts = _normalise_counts(raw.get("functional_groups"))
    if not counts:
        counts = _normalise_counts(descriptors.get("functional_groups"))

    for key, count in sorted(counts.items()):
        rows.append({
            "record_id": record_id,
            "name": name,
            "smiles": smiles,
            "group_key": key,
            "group_name": _title_from_key(key),
            "category": "",
            "count": count,
            "atom_indices": "",
        })
    return rows


def _ir_rows(raw: Mapping[str, Any], record_id: str, name: str, smiles: str) -> list[dict[str, Any]]:
    prediction = _as_dict(_coalesce(raw.get("ir_prediction"), raw.get("ir_predictions"), default={}))
    rows = []
    for band in _as_list(_coalesce(prediction.get("bands"), prediction.get("peaks"), default=[])):
        item = _as_dict(band)
        rows.append({
            "record_id": record_id,
            "name": name,
            "smiles": smiles,
            "assignment": item.get("label", ""),
            "lower_cm1": _to_int(_coalesce(item.get("lower_cm1"), item.get("low_cm"), item.get("low"))),
            "upper_cm1": _to_int(_coalesce(item.get("upper_cm1"), item.get("high_cm"), item.get("high"))),
            "intensity": item.get("intensity", ""),
            "confidence": _to_float(item.get("confidence")),
            "note": "heuristic prediction",
        })
    return rows


def _proton_rows(raw: Mapping[str, Any], record_id: str, name: str, smiles: str) -> list[dict[str, Any]]:
    prediction = _as_dict(_coalesce(raw.get("proton_nmr_prediction"), raw.get("proton_nmr_predictions"), raw.get("hnmr_prediction"), default={}))
    rows = []
    signals = _as_list(_coalesce(prediction.get("signals"), prediction.get("environments"), default=[]))
    for signal in signals:
        item = _as_dict(signal)
        rows.append({
            "record_id": record_id,
            "name": name,
            "smiles": smiles,
            "environment": item.get("label", ""),
            "shift_ppm": _to_float(item.get("shift_ppm")),
            "multiplicity": item.get("multiplicity", ""),
            "integration": _to_float(item.get("integration")),
            "atom_indices": _format_atom_indices(item.get("atom_indices")),
            "notes": item.get("notes", ""),
        })
    return rows


def _carbon_rows(raw: Mapping[str, Any], record_id: str, name: str, smiles: str) -> list[dict[str, Any]]:
    prediction = _as_dict(_coalesce(raw.get("carbon_nmr_prediction"), raw.get("carbon_nmr_predictions"), raw.get("cnmr_prediction"), default={}))
    rows = []
    for env in _as_list(_coalesce(prediction.get("environments"), prediction.get("atom_environments"), default=[])):
        item = _as_dict(env)
        ppm_range = _as_list(item.get("ppm_range"))
        rows.append({
            "record_id": record_id,
            "name": name,
            "smiles": smiles,
            "environment": item.get("label", ""),
            "shift_ppm": _to_float(item.get("shift_ppm")),
            "shift_low_ppm": _to_float(ppm_range[0]) if len(ppm_range) >= 1 else None,
            "shift_high_ppm": _to_float(ppm_range[1]) if len(ppm_range) >= 2 else None,
            "carbon_count": _to_int(item.get("carbon_count")) or 1,
            "attached_elements": _join_values(item.get("attached_elements")),
            "attached_hydrogens": _to_int(item.get("attached_hydrogens")),
            "is_quaternary": item.get("is_quaternary"),
            "notes": _coalesce(item.get("carbonyl_type"), item.get("heterocycle_family")),
        })
    return rows


def build_batch_export_payload(
    data: Any,
    *,
    metadata: Mapping[str, Any] | None = None,
    source: str = "Chemistry Companion",
) -> BatchExportPayload:
    """Normalize analysis or batch results into the shared export payload."""
    if isinstance(data, BatchExportPayload):
        payload = data
        if metadata:
            payload.metadata.update({str(k): _plain(v) for k, v in metadata.items()})
        return payload

    plain_data = _plain(data)
    if isinstance(plain_data, Mapping) and {"molecules", "descriptors", "metadata"}.issubset(plain_data.keys()):
        payload = BatchExportPayload(
            molecules=_as_list(plain_data.get("molecules")),
            descriptors=_as_list(plain_data.get("descriptors")),
            functional_groups=_as_list(plain_data.get("functional_groups")),
            ir_predictions=_as_list(plain_data.get("ir_predictions")),
            proton_nmr_predictions=_as_list(plain_data.get("proton_nmr_predictions")),
            carbon_nmr_predictions=_as_list(plain_data.get("carbon_nmr_predictions")),
            failures=_as_list(plain_data.get("failures")),
            metadata=_as_dict(plain_data.get("metadata")),
        )
        if metadata:
            payload.metadata.update({str(k): _plain(v) for k, v in metadata.items()})
        return payload

    payload = BatchExportPayload()
    records = _extract_records(plain_data)

    for position, raw in enumerate(records, start=1):
        record_id = _record_id(position)
        if _is_truthy_failure(raw):
            payload.failures.append(_failure_row(raw, record_id, position))
            continue

        sections = _success_sections(raw, record_id, position)
        payload.molecules.append(sections["molecule"])  # type: ignore[arg-type]
        payload.descriptors.append(sections["descriptor"])  # type: ignore[arg-type]
        payload.functional_groups.extend(sections["functional_groups"])  # type: ignore[arg-type]
        payload.ir_predictions.extend(sections["ir"])  # type: ignore[arg-type]
        payload.proton_nmr_predictions.extend(sections["proton"])  # type: ignore[arg-type]
        payload.carbon_nmr_predictions.extend(sections["carbon"])  # type: ignore[arg-type]

    payload.metadata = {
        "application": "Chemistry Companion",
        "source": source,
        "schema": "BatchExportPayload",
        "schema_version": "1.0",
        "generated_at_utc": _utc_now(),
        "total_records": len(records),
        "successful_records": len(payload.molecules),
        "failed_records": len(payload.failures),
        "molecule_rows": len(payload.molecules),
        "descriptor_rows": len(payload.descriptors),
        "functional_group_rows": len(payload.functional_groups),
        "ir_prediction_rows": len(payload.ir_predictions),
        "proton_nmr_rows": len(payload.proton_nmr_predictions),
        "carbon_nmr_rows": len(payload.carbon_nmr_predictions),
        "disclaimer": "Predictions are heuristic and intended for education and exploration, not experimental reporting.",
    }
    if metadata:
        payload.metadata.update({str(k): _plain(v) for k, v in metadata.items()})
    return payload
