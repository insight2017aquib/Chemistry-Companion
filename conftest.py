"""
conftest.py  (project root)
Adds the project root and the spectra package to sys.path so pytest can
resolve `from spectra.proton_nmr import ...` from any working directory.
"""
import sys
from pathlib import Path

# Root = directory that contains this conftest.py
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
