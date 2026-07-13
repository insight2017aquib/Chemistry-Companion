"""
chemistry_companion.py
======================
CLI entry point for Chemistry Companion v3.0.0.

Subcommands
-----------
  analyse     Full single-molecule pipeline
  batch       Batch analysis from CSV
  ir          IR band prediction (heuristic)
  hnmr        ¹H NMR shift estimation (heuristic)
  cnmr        ¹³C NMR shift estimation (heuristic)
  funcgroups  Functional group detection
  image       Export 2D structure PNG
  export      Export descriptors to CSV/JSON/XLSX
  demo        Run built-in demo molecules
  version     Print version info
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rdkit import __version__ as rdkit_version

from core.molecule_utils import load_molecule, MoleculeRecord
from core.descriptor_utils import compute_descriptors, summarise_descriptors
from core.visualization_utils import save_2d_image
from reports.export_utils import export_batch

logger = logging.getLogger("chemistry_companion")

VERSION = "3.0.0"

DEMO_MOLECULES = [
    ("Benzene",    "smiles", "c1ccccc1"),
    ("Aspirin",    "smiles", "CC(=O)Oc1ccccc1C(=O)O"),
    ("Caffeine",   "smiles", "Cn1cnc2c1c(=O)n(c(=O)n2C)C"),
    ("Ibuprofen",  "smiles", "CC(C)Cc1ccc(cc1)C(C)C(=O)O"),
]

_HR = "─" * 64


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def _banner() -> str:
    try:
        import pydantic
        pdv = pydantic.VERSION
    except ImportError:
        pdv = "not installed"
    try:
        import pandas as pd
        pav = pd.__version__
    except ImportError:
        pav = "not installed"
    return (
        "\n"
        "================================================================\n"
        f"  Chemistry Companion  v{VERSION}\n"
        "  Modular Cheminformatics and Spectroscopy Toolkit\n"
        f"  RDKit {rdkit_version} | Pydantic {pdv} | pandas {pav}\n"
        "================================================================"
    )


# ---------------------------------------------------------------------------
# Core analysis pipeline
# ---------------------------------------------------------------------------

def analyse(
    smiles: str | None = None,
    inchi: str | None = None,
    file_path: str | None = None,
    iupac_name: str | None = None,
    name: str | None = None,
    save_image: bool = False,
    export: list[str] | tuple = (),
    output_dir: str = "output",
) -> tuple[MoleculeRecord, object]:
    """Full Phase 1 pipeline: parse → descriptors → image → export."""
    os.makedirs(output_dir, exist_ok=True)

    mol_rec = load_molecule(
        smiles=smiles, inchi=inchi,
        file_path=file_path, iupac_name=iupac_name,
    )
    if name:
        mol_rec.name = name
    compound_name = mol_rec.name or "compound"

    desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)

    print(_banner())
    print()
    print(f"  {_HR}")
    print("  Molecular Identity")
    print(f"  {_HR}")
    print(f"  Compound   : {compound_name}")
    print(f"  Formula    : {mol_rec.formula}")
    print(f"  MW         : {mol_rec.mol_weight} Da  (average, gravimetric)")
    print(f"  Exact mass : {mol_rec.exact_mass} Da  (monoisotopic, EI-MS [M]\u207a)")
    print(f"  InChIKey   : {mol_rec.inchikey}")
    print(f"  SMILES     : {mol_rec.smiles}")
    print()
    print(f"  {_HR}")
    print("  Structural Counts")
    print(f"  {_HR}")
    print(f"  Total atoms  : {mol_rec.num_atoms}  (incl. H)")
    print(f"  Heavy atoms  : {mol_rec.num_heavy_atoms}")
    print(f"  Bonds        : {mol_rec.num_bonds}")
    print(f"  Rings        : {mol_rec.num_rings}")
    print(f"  Aromatic     : {mol_rec.is_aromatic}")
    print()
    print(f"  {_HR}")
    print("  Atom Composition")
    print(f"  {_HR}")
    for sym in sorted(mol_rec.atom_counts):
        print(f"  {sym:<4}: {mol_rec.atom_counts[sym]}")
    print()
    print(f"  {_HR}")
    print("  Lipinski / Drug-likeness Descriptors")
    print(f"  {_HR}")
    print(summarise_descriptors(desc_rec))

    if save_image:
        safe = compound_name.replace(" ", "_").replace("/", "-")
        ipath = os.path.join(output_dir, f"{safe}_2d.png")
        save_2d_image(mol_rec.rdkit_mol, ipath, title=compound_name)
        print(f"  \u2713 2D image      \u2192 {ipath}")

    if export:
        safe = compound_name.replace(" ", "_").replace("/", "-")
        epaths = export_batch(
            [(mol_rec, desc_rec)],
            output_dir=output_dir,
            base_name=safe,
            formats=list(export),
        )
        for fmt, path in epaths.items():
            label = fmt.upper().ljust(6)
            print(f"  \u2713 {label} export \u2192 {path}")

    return mol_rec, desc_rec


# ---------------------------------------------------------------------------
# Spectroscopy subcommands  (PATCHED)
# ---------------------------------------------------------------------------

def _resolve_mol(args):
    """Parse input flags into a MoleculeRecord."""
    mol_rec = load_molecule(
        smiles=getattr(args, "smiles", None),
        inchi=getattr(args, "inchi", None),
        file_path=getattr(args, "file", None),
        iupac_name=getattr(args, "iupac", None),
    )
    if getattr(args, "name", None):
        mol_rec.name = args.name
    return mol_rec


def _cmd_ir(args, settings: object | None = None) -> None:
    """IR band prediction subcommand."""
    try:
        from spectra.ir_predictor import IRPredictor

        mol_rec = _resolve_mol(args)
        compound_name = mol_rec.name or "compound"
        predictor = IRPredictor()
        result = predictor.predict(mol_rec.rdkit_mol)

        print(_banner())
        print()
        print(f"  {_HR}")
        print(f"  IR Prediction  \u26a0 APPROXIMATE \u2014 {compound_name}")
        print(f"  {_HR}")
        print("  Heuristic functional-group ranges. Not DFT-derived.  \u00b150 cm\u207b\u00b9.")
        print()

        # result.bands is a list of IRBand dataclass objects
        bands = getattr(result, "bands", None) or getattr(result, "peaks", None) or []
        if not bands:
            print("  No IR bands predicted for this structure.")
        else:
            print(f"  {'Functional Group':<35} {'Range (cm\u207b\u00b9)':<18} Intensity")
            print(f"  {'─'*35} {'─'*18} {'─'*10}")
            for band in bands:
                label    = getattr(band, "label", str(band))
                lo       = getattr(band, "wavenumber_low",  getattr(band, "wn_lo", "?"))
                hi       = getattr(band, "wavenumber_high", getattr(band, "wn_hi", "?"))
                intns    = getattr(band, "intensity", "")
                rng_str  = f"{lo}–{hi}" if lo != "?" else "?"
                print(f"  {label:<35} {rng_str:<18} {intns}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("ir — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("ir — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_hnmr(args, settings: object | None = None) -> None:
    """¹H NMR prediction subcommand."""
    try:
        from spectra.proton_nmr import predict_proton_nmr

        mol_rec = _resolve_mol(args)
        compound_name = mol_rec.name or "compound"
        result = predict_proton_nmr(mol_rec.smiles)

        print(_banner())
        print()
        print(f"  {_HR}")
        print(f"  \u00b9H NMR Prediction  \u26a0 APPROXIMATE \u2014 {compound_name}")
        print(f"  {_HR}")
        print("  Fragment heuristics only. Not DFT-derived.  \u00b10.5 ppm typical.")
        print()

        # result.environments is a list of ProtonEnvironment dataclass objects
        environments = getattr(result, "environments", [])
        if not environments:
            print("  No \u00b9H environments predicted for this structure.")
        else:
            print(f"  {'Environment':<30} {'\u03b4 (ppm)':<12} Count")
            print(f"  {'─'*30} {'─'*12} {'─'*6}")
            for env in environments:
                annotation = getattr(env, "annotation", None)
                label = getattr(env, "label", None)
                fallback = getattr(env, "environment_class", None)
                if annotation and label and annotation not in label:
                    label = f"{annotation} ({label})"
                else:
                    label = annotation or label or fallback or str(env)
                lo    = getattr(env, "ppm_low",  getattr(env, "shift_lo", "?"))
                hi    = getattr(env, "ppm_high", getattr(env, "shift_hi", "?"))
                mid   = getattr(env, "ppm_mid",  getattr(env, "shift",    None))
                count = getattr(env, "count", "")
                if mid is not None:
                    shift_str = f"{float(mid):.2f}"
                elif lo != "?" and hi != "?":
                    shift_str = f"{lo}–{hi}"
                else:
                    shift_str = "?"
                print(f"  {label:<30} {shift_str:<12} {count}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("hnmr — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("hnmr — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_cnmr(args, settings: object | None = None) -> None:
    """¹³C NMR prediction subcommand."""
    try:
        from spectra.carbon_nmr import predict_carbon_nmr

        mol_rec = _resolve_mol(args)
        compound_name = mol_rec.name or "compound"
        result = predict_carbon_nmr(mol_rec.smiles)

        print(_banner())
        print()
        print(f"  {_HR}")
        print(f"  \u00b9\u00b3C NMR Prediction  \u26a0 APPROXIMATE \u2014 {compound_name}")
        print(f"  {_HR}")
        print("  Fragment heuristics only. Not DFT-derived.  \u00b15 ppm typical.")
        print()

        # result.environments is a list of CarbonEnvironment dataclass objects
        environments = getattr(result, "environments", [])
        if not environments:
            print("  No \u00b9\u00b3C environments predicted for this structure.")
        else:
            print(f"  {'Environment':<30} {'\u03b4 (ppm)':<14} Count")
            print(f"  {'─'*30} {'─'*14} {'─'*6}")
            for env in environments:
                annotation = getattr(env, "annotation", None)
                label = getattr(env, "label", None)
                fallback = getattr(env, "environment_class", None)
                if annotation and label and annotation not in label:
                    label = f"{annotation} ({label})"
                else:
                    label = annotation or label or fallback or str(env)
                if isinstance(label, str) and getattr(env, "environment_class", "") == "acid_carbonyl":
                    label = f"Carboxylic {label}"
                lo    = getattr(env, "ppm_low",  getattr(env, "shift_lo", "?"))
                hi    = getattr(env, "ppm_high", getattr(env, "shift_hi", "?"))
                mid   = getattr(env, "ppm_mid",  getattr(env, "shift",    None))
                count = getattr(env, "count", "")
                if mid is not None:
                    shift_str = f"{float(mid):.1f}"
                elif lo != "?" and hi != "?":
                    shift_str = f"{lo}–{hi}"
                else:
                    shift_str = "?"
                print(f"  {label:<30} {shift_str:<14} {count}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("cnmr — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("cnmr — unexpected error: %s", exc)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Other subcommands
# ---------------------------------------------------------------------------

def _cmd_analyse(args, settings: object | None = None) -> None:
    try:
        mol_rec, desc_rec = run_analyse(
            smiles=args.smiles, inchi=args.inchi,
            file_path=args.file, iupac_name=args.iupac,
            name=args.name,
            save_image=args.save_image,
            export=args.export or [],
            output_dir=args.output_dir,
        )
        print(_banner())
        print()
        print(f"  Formula    : {mol_rec.formula}")
        print(f"  {summarise_descriptors(desc_rec)}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("analyse — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("analyse — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_batch(args, settings: object | None = None) -> None:
    try:
        import csv as _csv

        input_path = args.file
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)

        with open(input_path, newline="", encoding="utf-8") as fh:
            reader = _csv.DictReader(fh)
            rows = list(reader)

        n_total = len(rows)
        n_ok = 0
        failures: list[str] = []

        for idx, row in enumerate(rows, start=1):
            mol_name = row.get("name") or row.get("Name") or f"compound_{idx}"
            smi = (row.get("smiles") or row.get("SMILES") or "").strip()
            print(f"\n  ─── [{idx}/{n_total}]  {mol_name} ───")
            if not smi:
                failures.append(f"Row {idx} ('{mol_name}'): empty SMILES — skipped")
                continue
            try:
                analyse(
                    smiles=smi, name=mol_name,
                    export=args.export or [],
                    output_dir=output_dir,
                )
                n_ok += 1
            except Exception as exc:
                failures.append(f"Row {idx} ('{mol_name}'): {exc}")

        if failures:
            print(f"\n  \u26a0  {len(failures)} row(s) failed:")
            for f in failures:
                print(f"     \u2022 {f}")
        n_fail = n_total - n_ok
        print(f"\n  \u2713 Batch finished \u2014 {n_ok} succeeded / {n_fail} failed / {n_total} total")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("batch — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("batch — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_funcgroups(args, settings: object | None = None) -> None:
    try:
        mol_rec = _resolve_mol(args)
        desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)
        compound_name = mol_rec.name or "compound"
        print(_banner())
        print()
        print(f"  Functional groups — {compound_name}")
        print("  Detected functional groups:")
        fg = getattr(desc_rec, "functional_groups", {}) or {}
        if fg:
            for name_fg, count in fg.items():
                print(f"  - {name_fg}: {count}")
        else:
            print("  None detected.")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("funcgroups — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("funcgroups — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_image(args, settings: object | None = None) -> None:
    try:
        mol_rec = _resolve_mol(args)
        compound_name = mol_rec.name or "compound"
        os.makedirs(args.output_dir, exist_ok=True)
        safe = compound_name.replace(" ", "_").replace("/", "-")
        ipath = os.path.join(args.output_dir, f"{safe}_2d.png")
        save_2d_image(mol_rec.rdkit_mol, ipath, title=compound_name)
        print(f"  \u2713 2D image saved \u2192 {ipath}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("image — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("image — unexpected error: %s", exc)
        sys.exit(2)


def _safe_name(name: str) -> str:
    if name is None:
        return ""
    sanitized = re.sub(r"[\\/:*?\"<>| ]+", "_", str(name).strip())
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_.")


def _resolve_output_dir(output_dir: str, settings: object | None = None) -> str:
    if settings is not None:
        if hasattr(settings, "directories") and hasattr(settings.directories, "output_dir"):
            if output_dir == "output":
                return str(settings.directories.output_dir).replace("\\", "/")
    return output_dir


def _load_mol(args) -> MoleculeRecord:
    mol_rec = load_molecule(
        smiles=getattr(args, "smiles", None),
        inchi=getattr(args, "inchi", None),
        file_path=getattr(args, "file", None),
        iupac_name=getattr(args, "iupac", None),
    )
    if getattr(args, "name", None):
        mol_rec.name = args.name
    return mol_rec


def run_analyse(
    smiles: str | None = None,
    inchi: str | None = None,
    file_path: str | None = None,
    iupac_name: str | None = None,
    name: str | None = None,
    save_image: bool = False,
    export: list[str] | tuple[str, ...] = (),
    output_dir: str = "output",
) -> tuple[MoleculeRecord, object]:
    mol_rec = load_molecule(
        smiles=smiles,
        inchi=inchi,
        file_path=file_path,
        iupac_name=iupac_name,
    )
    if name:
        mol_rec.name = name
    desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)
    if save_image:
        os.makedirs(output_dir, exist_ok=True)
        safe = _safe_name(mol_rec.name or "compound")
        ipath = os.path.join(output_dir, f"{safe}_2d.png")
        save_2d_image(mol_rec.rdkit_mol, ipath, title=mol_rec.name or "compound")
    if export:
        safe = _safe_name(mol_rec.name or "compound")
        os.makedirs(output_dir, exist_ok=True)
        export_batch(
            [(mol_rec, desc_rec)],
            output_dir=output_dir,
            base_name=safe,
            formats=list(export),
        )
    return mol_rec, desc_rec


def run_funcgroups(mol_rec: MoleculeRecord) -> dict[str, bool]:
    desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)
    return {f"has_{k}": v > 0 for k, v in (desc_rec.functional_groups or {}).items()}


def run_ir(mol_rec: MoleculeRecord) -> dict[str, float | tuple[int, int]]:
    try:
        from spectra.ir_predictor import predict_ir

        result = predict_ir(mol_rec.rdkit_mol)
        peaks = getattr(result, "bands", None) or getattr(result, "peaks", [])
        output: dict[str, float | tuple[int, int]] = {}
        for idx, peak in enumerate(peaks, start=1):
            description = getattr(peak, "description", None)
            label = description or getattr(peak, "label", None) or str(peak)
            if label is None:
                label = str(peak)
            if hasattr(peak, "functional_group") and getattr(peak, "functional_group"):
                fg = getattr(peak, "functional_group")
                if fg not in label:
                    label = f"{fg} - {label}"
            label = label.replace("–", "=").replace("—", "=").replace("−", "=")
            label = f"{idx}_{label}" if label in output else label
            value = getattr(peak, "wavenumber_range", None)
            if value is None:
                value = getattr(peak, "mid_cm", None)
            output[label] = value
        return output
    except Exception:
        return {}


def run_hnmr(mol_rec: MoleculeRecord) -> dict[str, float]:
    try:
        from spectra.proton_nmr import predict_proton_nmr

        result = predict_proton_nmr(mol_rec.rdkit_mol)
        envs = getattr(result, "environments", None) or getattr(result, "signals", [])
        output: dict[str, float] = {}
        for idx, env in enumerate(envs, start=1):
            annotation = getattr(env, "annotation", None)
            label = getattr(env, "label", None)
            fallback = getattr(env, "environment_class", None)
            if annotation and label and annotation not in label:
                label = f"{annotation} ({label})"
            else:
                label = annotation or label or fallback or str(env)
            label = str(label).title()
            label = f"{idx}_{label}" if label in output else label
            ppm = getattr(env, "ppm_mid", None) or getattr(env, "shift", None)
            if ppm is not None:
                output[label] = float(ppm)
        return output
    except Exception:
        return {}


def run_cnmr(mol_rec: MoleculeRecord) -> dict[str, float]:
    try:
        from spectra.carbon_nmr import predict_carbon_nmr

        result = predict_carbon_nmr(mol_rec.smiles)
        envs = getattr(result, "environments", [])
        output: dict[str, float] = {}
        for idx, env in enumerate(envs, start=1):
            annotation = getattr(env, "annotation", None)
            label = annotation or getattr(env, "label", None) or getattr(env, "environment_class", None)
            if label is None:
                label = str(env)
            if isinstance(label, str) and getattr(env, "environment_class", "") == "acid_carbonyl":
                label = f"Carboxylic {label}"
            label = str(label).title()
            label = f"{idx}_{label}" if label in output else label
            ppm = getattr(env, "ppm_mid", None) or getattr(env, "shift", None)
            if ppm is not None:
                output[label] = float(ppm)
        return output
    except Exception:
        return {}


def run_batch(file_path: str, output_dir: str = "output") -> list[tuple[MoleculeRecord, object]]:
    import csv as _csv

    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    os.makedirs(output_dir, exist_ok=True)
    results: list[tuple[MoleculeRecord, object]] = []
    with open(file_path, newline="", encoding="utf-8") as fh:
        reader = _csv.DictReader(fh)
        for idx, row in enumerate(reader, start=1):
            mol_name = row.get("name") or row.get("Name") or f"compound_{idx}"
            smi = (row.get("smiles") or row.get("SMILES") or "").strip()
            if not smi:
                continue
            try:
                mol_rec, desc_rec = run_analyse(
                    smiles=smi,
                    name=mol_name,
                    export=[],
                    output_dir=output_dir,
                )
                results.append((mol_rec, desc_rec))
            except Exception:
                continue
    return results


def _cmd_export(args, settings: object | None = None) -> None:
    try:
        mol_rec = _resolve_mol(args)
        desc_rec = compute_descriptors(mol_rec.rdkit_mol, mw=mol_rec.mol_weight)
        compound_name = mol_rec.name or "compound"
        os.makedirs(args.output_dir, exist_ok=True)
        safe = compound_name.replace(" ", "_").replace("/", "-")
        epaths = export_batch(
            [(mol_rec, desc_rec)],
            output_dir=args.output_dir,
            base_name=safe,
            formats=args.formats or ["csv"],
        )
        for fmt, path in epaths.items():
            label = fmt.upper().ljust(6)
            print(f"  \u2713 {label} \u2192 {path}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("export — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("export — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_benchmark(args, settings: object | None = None) -> None:
    try:
        from core.descriptor_benchmark import (
            benchmark_from_csv,
            benchmark_molecule,
            benchmark_summary,
            export_benchmark_report,
        )

        comparisons = []
        if args.file:
            comparisons = benchmark_from_csv(
                args.file,
                smiles_column=args.smiles_column,
                name_column=args.name_column,
            )
        elif args.smiles:
            comparisons = [benchmark_molecule(args.smiles, name=args.name)]
        else:
            raise ValueError("Provide either --file or --smiles for benchmark input.")

        summary = benchmark_summary(comparisons)
        outputs = export_benchmark_report(
            comparisons,
            output_dir=args.output_dir,
            base_name=args.base_name,
        )

        print(_banner())
        print()
        print(f"  Benchmarked {summary.n_molecules} molecule(s)")
        print(f"  Formula accuracy        : {summary.formula_accuracy:.2f}%")
        print(f"  Rotatable bonds match   : {summary.rotatable_bonds_accuracy:.2f}%")
        print(f"  Ring count match        : {summary.ring_count_accuracy:.2f}%")
        print(f"  Full agreement          : {summary.full_agreement:.2f}%")
        print(f"  MW MAE                 : {summary.mw_mae:.4f}")
        print(f"  LogP MAE               : {summary.logp_mae:.4f}")
        print(f"  TPSA MAE               : {summary.tpsa_mae:.4f}")
        print()
        for key, path in outputs.items():
            print(f"  \u2713 {key.upper()} -> {path}")
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("benchmark — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("benchmark — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_demo(args, settings: object | None = None) -> None:
    try:
        output_dir = args.output_dir
        print(_banner())
        print(f"\n  === DEMO MODE \u2014 Benzene / Aspirin / Caffeine / Ibuprofen ===")
        for mol_name, _itype, smi in DEMO_MOLECULES:
            print(f"\n  {'='*62}\n  {mol_name}\n  {'='*62}")
            try:
                analyse(
                    smiles=smi, name=mol_name,
                    save_image=True, export=["csv"],
                    output_dir=output_dir,
                )
            except Exception as exc:
                logger.error("Demo failed for %s: %s", mol_name, exc)
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("demo — %s: %s", type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("demo — unexpected error: %s", exc)
        sys.exit(2)


def _cmd_version(_args, settings: object | None = None) -> None:
    try:
        import pydantic; pdv = pydantic.VERSION
    except ImportError:
        pdv = "not installed"
    try:
        import pandas as pd; pav = pd.__version__
    except ImportError:
        pav = "not installed"
    print(f"Chemistry Companion v{VERSION}")
    print(f"RDKit    : {rdkit_version}")
    print(f"Pydantic : {pdv}")
    print(f"pandas   : {pav}")
    print(f"Python   : {platform.python_version()}")
    print(f"Platform : {platform.system()} {platform.release()}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_input_group(parser: argparse.ArgumentParser) -> None:
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--smiles", metavar="SMILES")
    grp.add_argument("--inchi",  metavar="InChI")
    grp.add_argument("--file",   metavar="PATH")
    grp.add_argument("--iupac",  metavar="NAME")


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="chemistry_companion",
        description=(
            "Chemistry Companion \u2014 Modular Cheminformatics and Spectroscopy Toolkit\n\n"
            "Available subcommands:\n"
            "  analyse     Full single-molecule pipeline\n"
            "  batch       Batch analysis from CSV\n"
            "  ir          IR band prediction (heuristic)\n"
            "  hnmr        \u00b9H NMR shift estimation (heuristic)\n"
            "  cnmr        \u00b9\u00b3C NMR shift estimation (heuristic)\n"
            "  funcgroups  Functional group detection\n"
            "  image       Export 2D structure PNG\n"
            "  export      Export descriptors to CSV/JSON/XLSX\n"
            "  demo        Run built-in demo molecules\n"
            "  version     Print version info\n\n"
            "Run 'chemistry_companion <subcommand> --help' for options."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    root.add_argument("--verbose", "-v", action="store_true",
                      help="Enable DEBUG-level logging output.")

    sub = root.add_subparsers(dest="command", metavar="COMMAND")

    # analyse
    p_analyse = sub.add_parser("analyse",
        help="Full single-molecule analysis pipeline.")
    _add_input_group(p_analyse)
    p_analyse.add_argument("--name",       type=str, default=None)
    p_analyse.add_argument("--save-image", action="store_true")
    p_analyse.add_argument("--export",     nargs="+", metavar="FMT",
                            choices=["csv", "json", "xlsx"], default=[])
    p_analyse.add_argument("--output-dir", metavar="DIR", default="output")
    p_analyse.set_defaults(func=_cmd_analyse)

    # batch
    p_batch = sub.add_parser("batch",
        help="Batch analysis from a CSV file (columns: name, smiles).")
    p_batch.add_argument("--file",       required=True, metavar="CSV")
    p_batch.add_argument("--export",     nargs="+", metavar="FMT",
                          choices=["csv", "json", "xlsx"], default=[])
    p_batch.add_argument("--output-dir", metavar="DIR", default="output")
    p_batch.set_defaults(func=_cmd_batch)

    # ir
    p_ir = sub.add_parser("ir",
        help="Predict IR absorption bands (functional-group heuristics).")
    _add_input_group(p_ir)
    p_ir.add_argument("--name", type=str, default=None)
    p_ir.set_defaults(func=_cmd_ir)

    # hnmr
    p_hnmr = sub.add_parser("hnmr",
        help="Estimate \u00b9H NMR chemical shifts (heuristic, approximate).")
    _add_input_group(p_hnmr)
    p_hnmr.add_argument("--name", type=str, default=None)
    p_hnmr.set_defaults(func=_cmd_hnmr)

    # cnmr
    p_cnmr = sub.add_parser("cnmr",
        help="Estimate \u00b9\u00b3C NMR chemical shifts (heuristic, approximate).")
    _add_input_group(p_cnmr)
    p_cnmr.add_argument("--name", type=str, default=None)
    p_cnmr.set_defaults(func=_cmd_cnmr)

    # funcgroups
    p_fg = sub.add_parser("funcgroups",
        help="Detect functional groups via SMARTS matching.")
    _add_input_group(p_fg)
    p_fg.add_argument("--name", type=str, default=None)
    p_fg.set_defaults(func=_cmd_funcgroups)

    # image
    p_img = sub.add_parser("image",
        help="Export a 2D structure image as PNG.")
    _add_input_group(p_img)
    p_img.add_argument("--name",       type=str, default=None)
    p_img.add_argument("--output-dir", metavar="DIR", default="output")
    p_img.set_defaults(func=_cmd_image)

    # export
    p_exp = sub.add_parser("export",
        help="Export molecular descriptors to CSV, JSON, or XLSX.")
    _add_input_group(p_exp)
    p_exp.add_argument("--name",       type=str, default=None)
    p_exp.add_argument("--formats",    nargs="+", metavar="FMT",
                        choices=["csv", "json", "xlsx"], default=["csv"])
    p_exp.add_argument("--output-dir", metavar="DIR", default="output")
    p_exp.set_defaults(func=_cmd_export)

    # benchmark
    p_bench = sub.add_parser("benchmark",
        help="Benchmark descriptor outputs against RDKit reference.")
    group = p_bench.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", metavar="CSV",
                       help="CSV file with SMILES and optional name columns.")
    group.add_argument("--smiles", metavar="SMILES",
                       help="Single SMILES string to benchmark.")
    p_bench.add_argument("--name", type=str, default=None,
                         help="Optional name for the single SMILES benchmark.")
    p_bench.add_argument("--smiles-column", type=str, default="smiles",
                         help="Column name for SMILES in CSV input.")
    p_bench.add_argument("--name-column", type=str, default="name",
                         help="Column name for compound names in CSV input.")
    p_bench.add_argument("--output-dir", metavar="DIR", default="output")
    p_bench.add_argument("--base-name", type=str, default="descriptor_benchmark",
                         help="Base name for benchmark export files.")
    p_bench.set_defaults(func=_cmd_benchmark)

    # demo
    p_demo = sub.add_parser("demo",
        help="Run built-in demo (Benzene, Aspirin, Caffeine, Ibuprofen).")
    p_demo.add_argument("--output-dir", metavar="DIR", default="output")
    p_demo.set_defaults(func=_cmd_demo)

    # version
    p_ver = sub.add_parser("version",
        help="Print version and dependency info.")
    p_ver.set_defaults(func=_cmd_version)

    return root


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        args.func(args)
    except SystemExit:
        raise
    except (ValueError, FileNotFoundError, ImportError) as exc:
        logger.error("%s — %s: %s", args.command, type(exc).__name__, exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("%s — unexpected error: %s", args.command, exc)
        sys.exit(2)


if __name__ == "__main__":
    main()