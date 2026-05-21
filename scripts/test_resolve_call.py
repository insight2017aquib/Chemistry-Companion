import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.resolver import resolve_name_to_smiles, _resolve_name_to_smiles_with_source

name = "N-(3-chloro-2-(naphthalen-1-yl)-4-oxoazetidin-1-yl)-3-hydroxyquinoxaline-2-carboxamide"

print("Resolving:", name)
try:
    smi, source = _resolve_name_to_smiles_with_source(name)
    print("Resolved SMILES:", smi)
    print("Resolver source:", source)
except Exception as e:
    print("Resolution failed:", e)
