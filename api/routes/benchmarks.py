"""
api/routes/benchmarks.py
========================
Benchmarks workflow execution API.
"""

import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent.parent

_benchmark_cache = {
    "timestamp": 0,
    "file_mtime": 0,
    "data": None
}

@router.post("/benchmarks/run")
async def run_benchmarks() -> dict[str, Any]:
    """Run the descriptor benchmark and return cached metrics if within 24h TTL."""
    try:
        csv_path = ROOT / "data" / "benchmark_molecules.csv"
        if not csv_path.exists():
            return {"success": False, "error": "Benchmark CSV not found", "status": "failed"}

        file_mtime = os.path.getmtime(csv_path)
        current_time = time.time()
        
        # TTL: 24 hours (86400 seconds)
        if (
            _benchmark_cache["data"] is not None 
            and _benchmark_cache["file_mtime"] == file_mtime 
            and (current_time - _benchmark_cache["timestamp"]) < 86400
        ):
            logger.info("Returning cached benchmark results")
            return {
                "success": True,
                "cached": True,
                "data": _benchmark_cache["data"],
                "status": "completed"
            }
            
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
            
        from core.descriptor_benchmark import benchmark_from_csv, export_benchmark_report, benchmark_summary
        from scripts.run_tool_comparison import main as run_tool_comparison
        
        # 1. Run Descriptor Benchmark
        comparisons = benchmark_from_csv(csv_path)
        summary = benchmark_summary(comparisons)
        
        output_dir = ROOT / "outputs" / "descriptor_benchmarks"
        export_paths = export_benchmark_report(comparisons, output_dir=output_dir)
        
        # 2. Run Tool Comparison to regenerate the static SVGs displayed in the GUI
        # This keeps the visuals up to date without redesigning them.
        run_tool_comparison()
        
        result_data = {
            "n_molecules": summary.n_molecules,
            "full_agreement": summary.full_agreement,
            "mw_mae": summary.mw_mae,
            "logp_mae": summary.logp_mae,
            "tpsa_mae": summary.tpsa_mae
        }
        
        _benchmark_cache["timestamp"] = current_time
        _benchmark_cache["file_mtime"] = file_mtime
        _benchmark_cache["data"] = result_data
        
        return {
            "success": True,
            "cached": False,
            "data": result_data,
            "status": "completed"
        }
    except Exception as exc:
        logger.error("Benchmark failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc), "status": "failed"}
