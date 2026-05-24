import csv
import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def main():
    # Load backend inventory
    backend_inv_path = PROJECT_ROOT / "backend_inventory.csv"
    if not backend_inv_path.exists():
        print("Run audit_backend.py first.")
        return

    exports = set()
    consumes = set()
    
    with open(backend_inv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip fastapi dependency injection or config modules
            if "config" in row["File"].lower() or "models" in row["File"].lower():
                continue
                
            if row["Exports Functions"]:
                for exp in row["Exports Functions"].split(", "):
                    exports.add(exp.strip())
            if row["Consumes Functions"]:
                for con in row["Consumes Functions"].split(", "):
                    consumes.add(con.strip())

    # Dead code: exported but never consumed, and not an API router
    # Heuristic filter for false positives (dependency injection, etc)
    false_positives = [
        "get_db", "get_settings", "router", "app", "Base", "engine", "SessionLocal"
    ]
    
    dead_code = []
    for exp in exports:
        if exp not in consumes and exp not in false_positives:
            # Check if it's a pytest
            if exp.startswith("test_") or "Test" in exp:
                continue
            dead_code.append(exp)

    # Output dead code report
    with open(PROJECT_ROOT / "dead_code_report.md", "w", encoding="utf-8") as f:
        f.write("# Dead Code Report\n\n")
        f.write("Functions or classes that are exported but never explicitly consumed by any internal module:\n\n")
        for dc in sorted(dead_code):
            f.write(f"- `{dc}`\n")
            
        f.write("\n> Note: False positive filters applied for FastAPI dependencies, routing, and pytest functions.\n")

if __name__ == "__main__":
    main()
