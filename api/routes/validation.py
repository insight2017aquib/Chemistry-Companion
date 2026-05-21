"""
api/routes/validation.py
========================
Validation workflow execution API.
"""

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent.parent

@router.post("/validation/run")
async def run_validation() -> dict[str, Any]:
    """Run the spectra validation workflow and regenerate plots."""
    try:
        # Import dynamically to avoid top-level circular dependencies or heavy lifting on startup
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
            
        from run_spectra_validation import load_benchmark
        from core.spectra_validation import validate_spectra_workflow
        from core.spectra_exporter import build_publication_plots

        benchmark_csv = ROOT / "spectra_benchmark.csv"
        if not benchmark_csv.exists():
            fallback_csv = ROOT / "data" / "spectra_benchmark.csv"
            if fallback_csv.exists():
                benchmark_csv = fallback_csv
            else:
                raise FileNotFoundError(
                    f"Benchmark CSV not found at {benchmark_csv} or {fallback_csv}"
                )
        records = load_benchmark(benchmark_csv)
        
        report = validate_spectra_workflow(records)
        
        output_dir = ROOT / "outputs" / "spectra"
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_dir = output_dir / "publication_plots"
        
        # This regenerates the static plots the frontend is pointing to
        build_publication_plots(report, plot_dir)
        
        return {
            "success": True,
            "metrics": {
                "total": report.total(),
                "successes": report.successes(),
                "failures": report.failures()
            },
            "status": "completed"
        }
    except Exception as exc:
        logger.error("Validation failed: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "status": "failed"
        }
