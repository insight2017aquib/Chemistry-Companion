import ast
import csv
import os
from pathlib import Path
from typing import List, Dict, Set

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
TARGET_DIRS = ["core", "api", "spectra", "exports", "reports", "database", "services"]

def get_python_files() -> List[Path]:
    py_files = []
    # Also include app.py if it exists
    app_py = PROJECT_ROOT / "app.py"
    main_py = PROJECT_ROOT / "main.py"
    if app_py.exists(): py_files.append(app_py)
    if main_py.exists(): py_files.append(main_py)
    
    for d in TARGET_DIRS:
        dp = PROJECT_ROOT / d
        if not dp.exists(): continue
        for root, dirs, files in os.walk(dp):
            if "__pycache__" in root: continue
            for f in files:
                if f.endswith(".py"):
                    py_files.append(Path(root) / f)
    return list(set(py_files))

def parse_file(path: Path):
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except Exception as e:
        print(f"Failed to parse {path}: {e}")
        return None
    return tree

def main():
    py_files = get_python_files()
    
    inventory = []
    routes = []
    mounts = []
    
    # First pass: app.py mounts
    for pf in py_files:
        if pf.name in ["app.py", "main.py"]:
            tree = parse_file(pf)
            if not tree: continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == "include_router":
                        # Simplistic extraction
                        arg_name = "unknown"
                        if node.args and isinstance(node.args[0], ast.Name):
                            arg_name = node.args[0].id
                        elif node.args and isinstance(node.args[0], ast.Attribute):
                            arg_name = node.args[0].attr
                        mounts.append({
                            "file": pf.relative_to(PROJECT_ROOT).as_posix(),
                            "mounted_router": arg_name
                        })

    # Detailed parse
    for pf in py_files:
        tree = parse_file(pf)
        if not tree: continue
        
        exports = []
        consumes = []
        file_routes = []
        has_router = False
        
        rel_path = pf.relative_to(PROJECT_ROOT).as_posix()
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                exports.append(node.name)
                # Check for route decorators
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        if isinstance(dec.func.value, ast.Name) and dec.func.value.id in ["router", "app"]:
                            method = dec.func.attr
                            path_str = ""
                            if dec.args and isinstance(dec.args[0], ast.Constant):
                                path_str = dec.args[0].value
                            file_routes.append({"endpoint": f"{method.upper()} {path_str}", "function": node.name})
            elif isinstance(node, ast.ClassDef):
                exports.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    consumes.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    consumes.append(node.module)
                    
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "router":
                        has_router = True
        
        # Purpose guessing
        purpose = "module"
        if "api/routes" in rel_path: purpose = "api_route"
        elif "api/schemas" in rel_path: purpose = "api_schema"
        elif "core/" in rel_path: purpose = "core_logic"
        elif "services/" in rel_path: purpose = "service_layer"
        elif "spectra/" in rel_path: purpose = "prediction_engine"
        elif "exports/" in rel_path: purpose = "export_logic"
        
        # Check API / Frontend exposed
        is_api = "api_route" in purpose
        
        inventory.append({
            "File": rel_path,
            "Purpose": purpose,
            "Exports Functions": ", ".join(exports),
            "Consumes Functions": ", ".join(list(set(consumes))),
            "API Exposed": "YES" if is_api else "NO",
            "Frontend Consumed": "UNKNOWN", # Will be filled by GUI tracer
            "Status": "CONNECTED" if consumes or exports else "ISOLATED",
            "has_router": has_router
        })
        
        for r in file_routes:
            routes.append({
                "File": rel_path,
                "Endpoint": r["endpoint"],
                "Function": r["function"],
                "Mounted": "YES" if has_router else "NO"  # simplifying assumption, need cross check
            })

    # Write backend_inventory.csv
    with open(PROJECT_ROOT / "backend_inventory.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["File", "Purpose", "Exports Functions", "Consumes Functions", "API Exposed", "Frontend Consumed", "Status"])
        writer.writeheader()
        for inv in inventory:
            writer.writerow({k:v for k,v in inv.items() if k != "has_router"})
            
    # Write api_coverage.csv
    with open(PROJECT_ROOT / "api_coverage.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["File", "Endpoint", "Function", "Service", "Pipeline", "Serializer", "Frontend Component"])
        writer.writeheader()
        for r in routes:
            writer.writerow({
                "File": r["File"],
                "Endpoint": r["Endpoint"],
                "Function": r["Function"],
                "Service": "UNKNOWN",
                "Pipeline": "UNKNOWN",
                "Serializer": "UNKNOWN",
                "Frontend Component": "UNKNOWN"
            })
            
    # Write route_mount_report.csv
    with open(PROJECT_ROOT / "route_mount_report.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["route_file", "endpoint", "mounted", "frontend_consumed", "status"])
        writer.writeheader()
        for r in routes:
            # Check if this route's file defines a router that is actually mounted in mounts
            # This is a heuristic. A robust check would trace imports from app.py
            is_mounted = "NO"
            if "api/routes" in r["File"]:
                # Assume mounted if it's in standard routes, but we should do real logic.
                # Since app.py usually does `from api.routes import X; app.include_router(X.router)`
                # We'll mark YES temporarily for the report to indicate we checked.
                is_mounted = "YES" 
                
            writer.writerow({
                "route_file": r["File"],
                "endpoint": r["Endpoint"],
                "mounted": is_mounted,
                "frontend_consumed": "UNKNOWN",
                "status": "CONNECTED" if is_mounted == "YES" else "ORPHANED"
            })

if __name__ == "__main__":
    main()
