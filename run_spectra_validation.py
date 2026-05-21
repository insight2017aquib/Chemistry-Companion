"""
run_spectra_validation.py
=========================
Spectra Validation Workflow — Main Entry Point

Compares HEURISTIC spectral predictions (IR, 1H NMR, 13C NMR) against
EXPERIMENTAL reference values from a benchmark CSV and exports:

  outputs/spectra/
    validation_summary.xlsx        <- 7-sheet styled workbook
    validation_report.md           <- Markdown report
    publication_plots/             <- 8 publication-quality PNG figures

Usage
-----
  python run_spectra_validation.py
  python run_spectra_validation.py --input spectra_benchmark.csv
  python run_spectra_validation.py --input data.csv --output my_results/
  python run_spectra_validation.py --ir-tol 40 --proton-tol 0.4 --carbon-tol 4.0
  python run_spectra_validation.py --no-plots
  python run_spectra_validation.py --regen-benchmark
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

# ── Path setup ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("spectra_validation")

DEFAULT_INPUT  = ROOT / "spectra_benchmark.csv" if (ROOT / "spectra_benchmark.csv").exists() else ROOT / "data" / "spectra_benchmark.csv"
DEFAULT_OUTPUT = ROOT / "outputs" / "spectra"


# ── CLI ────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Spectra Validation Workflow: Heuristic vs Experimental",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input",          type=Path, default=DEFAULT_INPUT,
                   help="Path to spectra_benchmark.csv")
    p.add_argument("--output",         type=Path, default=DEFAULT_OUTPUT,
                   help="Output directory")
    p.add_argument("--ir-tol",         type=float, default=50.0,
                   help="IR matching tolerance (cm⁻¹)")
    p.add_argument("--proton-tol",     type=float, default=0.5,
                   help="1H NMR matching tolerance (ppm)")
    p.add_argument("--carbon-tol",     type=float, default=5.0,
                   help="13C NMR matching tolerance (ppm)")
    p.add_argument("--no-plots",       action="store_true",
                   help="Skip publication plot generation")
    p.add_argument("--no-xlsx",        action="store_true",
                   help="Skip XLSX export")
    p.add_argument("--no-markdown",    action="store_true",
                   help="Skip Markdown report")
    p.add_argument("--regen-benchmark", action="store_true",
                   help="Re-generate spectra_benchmark.csv before validation")
    return p.parse_args()


# ── Dataset loader ─────────────────────────────────────────────────────────────

def _parse_peaks(raw: str | float | None) -> list[float]:
    """Parse a JSON list column into a Python list of floats."""
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    try:
        parsed = json.loads(str(raw))
        return [float(x) for x in parsed]
    except (json.JSONDecodeError, TypeError, ValueError):
        return []


def load_benchmark(csv_path: Path) -> list[dict]:
    """Load spectra_benchmark.csv into validation input records."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Benchmark CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["smiles"])
    df = df[df["smiles"].str.strip() != ""]
    logger.info("Loaded %d molecules from %s", len(df), csv_path.name)

    records = []
    for _, row in df.iterrows():
        records.append({
            "smiles":              str(row["smiles"]).strip(),
            "molecule_name":       str(row.get("molecule_name", "")),
            "experimental_ir":     _parse_peaks(row.get("experimental_ir")),
            "experimental_proton": _parse_peaks(row.get("experimental_proton")),
            "experimental_carbon": _parse_peaks(row.get("experimental_carbon")),
            # Provenance flags — passed through for audit
            "ir_is_heuristic":     bool(row.get("ir_is_heuristic", True)),
            "proton_is_heuristic": bool(row.get("proton_is_heuristic", True)),
            "carbon_is_heuristic": bool(row.get("carbon_is_heuristic", True)),
            "source_notes":        str(row.get("source_notes", "HEURISTIC-DERIVED")),
        })
    return records


# ── Console table ──────────────────────────────────────────────────────────────

def print_results_table(report) -> None:
    from core.spectra_validation import DOMAIN_LABELS
    sep = "-" * 85
    header = (f"{'Domain':<14} {'Avg MAE':>10} {'Avg RMSE':>10} "
              f"{'Cov(pred)':>10} {'Cov(exp)':>10} {'Matches':>8} {'FN':>5}")
    print(f"\n{sep}\n{header}\n{sep}")
    for domain in ("ir", "proton", "carbon"):
        mae  = report.average_mae(domain)
        rmse = report.average_rmse(domain)
        cp   = report.average_coverage_predicted(domain)
        ce   = report.average_coverage_experimental(domain)
        tm   = report.total_matches(domain)
        total_fn = sum(
            m.missing_experimental
            for rec in report.records
            if (m := getattr(rec, f"{domain}_metrics")) is not None
        )
        print(
            f"{DOMAIN_LABELS[domain]:<14} "
            f"{mae:>10.4f} " if mae is not None else f"{'N/A':>11} "
            f"{rmse:>10.4f} " if rmse is not None else f"{'N/A':>11} "
            f"{cp*100:>9.1f}% " if cp is not None else f"{'N/A':>11} "
            f"{ce*100:>9.1f}% " if ce is not None else f"{'N/A':>11} "
            f"{tm:>8d} "
            f"{total_fn:>5d}"
        )
    print(sep)
    print(f"  Total molecules: {report.total()}  |  OK: {report.successes()}  |  Failed: {report.failures()}")
    print(sep + "\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    print("=" * 72)
    print("  Spectra Validation Workflow  v1.0")
    print("  HEURISTIC Predictions vs EXPERIMENTAL Reference")
    print("=" * 72)

    # 0. Optionally regenerate benchmark
    if args.regen_benchmark or not args.input.exists():
        logger.info("Generating spectra_benchmark.csv ...")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_spectra_benchmark.py")],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            logger.error("Benchmark generation failed:\n%s", result.stderr)
            sys.exit(1)
        logger.info(result.stdout.strip())

    # 1. Load benchmark
    records = load_benchmark(args.input)

    tolerances = {
        "ir":     args.ir_tol,
        "proton": args.proton_tol,
        "carbon": args.carbon_tol,
    }
    logger.info("Tolerances — IR: ±%g cm⁻¹  |  1H: ±%g ppm  |  13C: ±%g ppm",
                args.ir_tol, args.proton_tol, args.carbon_tol)

    # 2. Run validation
    logger.info("Running spectra validation workflow ...")
    from core.spectra_validation import validate_spectra_workflow
    report = validate_spectra_workflow(
        records,
        ir_tolerance     = args.ir_tol,
        proton_tolerance = args.proton_tol,
        carbon_tolerance = args.carbon_tol,
    )

    # 3. Print table
    print_results_table(report)

    args.output.mkdir(parents=True, exist_ok=True)

    # 4. XLSX
    if not args.no_xlsx:
        logger.info("Exporting styled XLSX ...")
        from core.spectra_exporter import export_xlsx_styled
        xlsx_path = args.output / "validation_summary.xlsx"
        export_xlsx_styled(report, xlsx_path, csv_path=str(args.input),
                           tolerances=tolerances)
        print(f"  [OK] XLSX  : {xlsx_path}")

    # 5. Plots
    plot_dir = args.output / "publication_plots"
    if not args.no_plots:
        logger.info("Generating publication plots ...")
        from core.spectra_exporter import build_publication_plots
        figures = build_publication_plots(report, plot_dir)
        print(f"  [OK] Plots : {plot_dir}  ({len(figures)} figures)")

    # 6. Markdown
    if not args.no_markdown:
        logger.info("Writing Markdown report ...")
        from core.spectra_exporter import build_markdown_report_enhanced
        md = build_markdown_report_enhanced(
            report,
            tolerances=tolerances,
            plot_dir=plot_dir if not args.no_plots else None,
        )
        md_path = args.output / "validation_report.md"
        md_path.write_text(md, encoding="utf-8")
        print(f"  [OK] MD    : {md_path}")

    # 7. Summary
    print("\n" + "=" * 72)
    print("  Validation Complete")
    print(f"  Molecules  : {report.total()}  (OK: {report.successes()}, Failed: {report.failures()})")
    for domain in ("ir", "proton", "carbon"):
        from core.spectra_validation import DOMAIN_LABELS
        mae = report.average_mae(domain)
        print(f"  {DOMAIN_LABELS[domain]:<12} MAE: {mae:.4f}" if mae is not None
              else f"  {DOMAIN_LABELS[domain]:<12} MAE: N/A")
    print(f"  Outputs    : {args.output}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    main()
