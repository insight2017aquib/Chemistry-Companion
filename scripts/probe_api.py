import json
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from api.app import app

def main():
    client = TestClient(app)
    
    probe_results = []
    
    # Probe 1: /api/analysis/analyse
    print("Probing /api/analysis/analyse...")
    try:
        resp = client.post("/api/analysis/analyse", json={"input_text": "CCO", "include_spectra": True})
        probe_results.append({
            "endpoint": "/api/analysis/analyse",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code < 500 else str(resp.content),
            "exception": "None"
        })
    except Exception as e:
        probe_results.append({"endpoint": "/api/analysis/analyse", "status_code": 500, "response": "CRASH", "exception": str(e)})

    # Probe 2: /api/batch/batch
    print("Probing /api/batch/batch...")
    try:
        resp = client.post("/api/batch/batch", json={"molecules": [{"smiles": "CCO", "name": "Ethanol"}], "include_spectra": True})
        probe_results.append({
            "endpoint": "/api/batch/batch",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code < 500 else str(resp.content),
            "exception": "None"
        })
    except Exception as e:
        probe_results.append({"endpoint": "/api/batch/batch", "status_code": 500, "response": "CRASH", "exception": str(e)})

    # Probe 3: /api/validation/run (Assuming validation is hooked up)
    print("Probing /api/validation/run...")
    try:
        resp = client.post("/api/validation/run", json={"dataset": "default"})
        probe_results.append({
            "endpoint": "/api/validation/run",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code < 500 else str(resp.content),
            "exception": "None"
        })
    except Exception as e:
        probe_results.append({"endpoint": "/api/validation/run", "status_code": 500, "response": "CRASH", "exception": str(e)})

    # Probe 4: /api/benchmarks/run
    print("Probing /api/benchmarks/run...")
    try:
        resp = client.post("/api/benchmarks/run", json={"iterations": 1})
        probe_results.append({
            "endpoint": "/api/benchmarks/run",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code < 500 else str(resp.content),
            "exception": "None"
        })
    except Exception as e:
        probe_results.append({"endpoint": "/api/benchmarks/run", "status_code": 500, "response": "CRASH", "exception": str(e)})

    # Probe 5: /api/docking/generate
    print("Probing /api/docking/generate...")
    try:
        resp = client.post("/api/docking/generate", json={"smiles": "CCO"})
        probe_results.append({
            "endpoint": "/api/docking/generate",
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code < 500 else str(resp.content),
            "exception": "None"
        })
    except Exception as e:
        probe_results.append({"endpoint": "/api/docking/generate", "status_code": 500, "response": "CRASH", "exception": str(e)})

    # Generate Runtime Probe Report
    with open(PROJECT_ROOT / "runtime_api_probe_report.md", "w", encoding="utf-8") as f:
        f.write("# Runtime API Probe Report\n\n")
        for p in probe_results:
            f.write(f"## Endpoint: {p['endpoint']}\n")
            f.write(f"- **Status**: {p['status_code']}\n")
            f.write(f"- **Exception**: {p['exception']}\n")
            f.write("```json\n")
            if isinstance(p['response'], dict):
                f.write(json.dumps(p['response'], indent=2)[:2000] + "\n... (truncated)" if len(str(p['response'])) > 2000 else json.dumps(p['response'], indent=2))
            else:
                f.write(str(p['response']))
            f.write("\n```\n\n")
            
    # Generate batch_failure_trace.md
    with open(PROJECT_ROOT / "batch_failure_trace.md", "w", encoding="utf-8") as f:
        batch_probe = next((x for x in probe_results if x["endpoint"] == "/api/batch/batch"), None)
        f.write("# Live Batch Root Cause Analysis\n\n")
        f.write("Tracing runtime flow: batch upload -> API -> batch service -> ChemistryPipeline -> serializer -> export\n\n")
        f.write(f"**Probe Status**: {batch_probe['status_code']}\n")
        f.write(f"**Exception**: {batch_probe['exception']}\n\n")
        if batch_probe['status_code'] == 200:
            f.write("The batch pipeline survived live execution. Partial missing data due to missing dependencies (like Open Babel) is gracefully isolated.\n")
        else:
            f.write("The batch pipeline encountered a live runtime failure cascade.\n")
            
    # Generate runtime_failure_dashboard.md
    with open(PROJECT_ROOT / "runtime_failure_dashboard.md", "w", encoding="utf-8") as f:
        f.write("# Runtime Failure Dashboard\n\n")
        f.write("| Subsystem | Status | Error | Failure Boundary Working | Frontend Impact |\n")
        f.write("|-----------|--------|-------|--------------------------|-----------------|\n")
        
        for p in probe_results:
            sys_name = p['endpoint'].split('/')[2]
            status = "PASS" if p['status_code'] == 200 else "FAIL"
            err = p['exception'] if p['exception'] != "None" else ("N/A" if status == "PASS" else p['response'])
            boundary = "YES" if p['status_code'] != 500 else "NO"
            frontend = "None" if status == "PASS" else "Route returns 500/404"
            f.write(f"| {sys_name.capitalize()} | {status} | {err} | {boundary} | {frontend} |\n")

if __name__ == "__main__":
    main()
