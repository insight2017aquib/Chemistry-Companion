# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller onedir spec for Chemistry Companion (portable build).

Build:
    .venv\\Scripts\\pyinstaller.exe --noconfirm --clean chemistry_companion.spec

Output:
    dist/ChemistryCompanion/ChemistryCompanion.exe
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

SPECPATH = Path(SPECPATH).resolve()  # noqa: F821 — injected by PyInstaller
ROOT = SPECPATH

# ---------------------------------------------------------------------------
# Application package data (templates, static, sample data, config samples)
# ---------------------------------------------------------------------------
datas: list[tuple[str, str]] = [
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "static"), "static"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / ".env.example"), "."),
]

# Sample / benchmark data (exclude runtime pams store)
for name in ("benchmark_molecules.csv", "spectra_benchmark.csv", "smiles_input.txt", "__init__.py"):
    src = ROOT / "data" / name
    if src.exists():
        datas.append((str(src), "data"))

binaries: list[tuple[str, str]] = []
hiddenimports: list[str] = []

# ---------------------------------------------------------------------------
# collect_all for heavy / binary-rich third-party packages
# ---------------------------------------------------------------------------
_COLLECT_ALL = (
    "rdkit",
    "openbabel",
    "meeko",
    "fastapi",
    "starlette",
    "uvicorn",
    "sqlalchemy",
    "pydantic",
    "pydantic_settings",
    "anyio",
    "multipart",
    "jinja2",
    "matplotlib",
    "seaborn",
    "PIL",
    "numpy",
    "pandas",
    "scipy",
    "gemmi",
    "py3Dmol",
    "pubchempy",
    "py2opsin",
    "openpyxl",
    "aiofiles",
    "certifi",
    "colorama",
)

for pkg in _COLLECT_ALL:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_all({pkg!r}) skipped: {exc}")

# Explicit data / libs that collect_all sometimes misses on Windows wheels
for pkg in ("rdkit", "openbabel", "numpy", "pandas", "scipy", "matplotlib"):
    try:
        datas += collect_data_files(pkg, include_py_files=False)
    except Exception:
        pass
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

# rdkit.libs / openbabel_wheel.libs / numpy.libs sit as sibling packages
_SITE = ROOT / ".venv" / "Lib" / "site-packages"
for lib_dir_name in (
    "rdkit.libs",
    "openbabel_wheel.libs",
    "numpy.libs",
    "pandas.libs",
    "scipy.libs",
):
    lib_dir = _SITE / lib_dir_name
    if lib_dir.is_dir():
        for dll in lib_dir.glob("*.dll"):
            binaries.append((str(dll), lib_dir_name))
        for dll in lib_dir.glob("*.so*"):
            binaries.append((str(dll), lib_dir_name))

# Open Babel native tools + format plugins + data (critical for docking prep)
_ob_bin = _SITE / "openbabel" / "bin"
if _ob_bin.is_dir():
    datas.append((str(_ob_bin), "openbabel/bin"))

# py2opsin ships a Java JAR required at runtime (needs system JRE)
_opsin = _SITE / "py2opsin"
if _opsin.is_dir():
    for jar in _opsin.glob("*.jar"):
        datas.append((str(jar), "py2opsin"))

# ---------------------------------------------------------------------------
# AutoDock Vina + obabel executables (placed into _internal; entry sets env)
# ---------------------------------------------------------------------------
for exe_name in ("vina.exe", "vina", "obabel.exe", "obabel"):
    for candidate in (
        ROOT / ".venv" / "Scripts" / exe_name,
        _ob_bin / exe_name,
    ):
        if candidate.is_file():
            binaries.append((str(candidate), "."))
            break

# ---------------------------------------------------------------------------
# First-party package submodules (dynamic FastAPI routes, services, spectra)
# ---------------------------------------------------------------------------
for pkg in (
    "api",
    "core",
    "database",
    "docking_workflow",
    "exports",
    "llm",
    "reports",
    "services",
    "spectra",
    "visualization",
    "data",
    "static",
    "templates",
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception as exc:  # pragma: no cover
        print(f"[spec] collect_submodules({pkg!r}) skipped: {exc}")

# Explicit critical / commonly missed hidden imports
hiddenimports += [
    # Uvicorn stack (string-free run still needs protocol workers)
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "h11",
    "httptools",
    "websockets",
    "watchfiles",
    "click",
    # SQLAlchemy / DB
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.dialects.sqlite.pysqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
    "aiosqlite",
    "pysqlite2",
    "sqlite3",
    # FastAPI / Starlette / multipart
    "fastapi",
    "starlette",
    "starlette.routing",
    "starlette.staticfiles",
    "starlette.templating",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.responses",
    "multipart",
    "python_multipart",
    "email.mime.multipart",
    "email.mime.text",
    # Pydantic
    "pydantic",
    "pydantic_settings",
    "pydantic.deprecated.decorator",
    # RDKit common entry points
    "rdkit",
    "rdkit.Chem",
    "rdkit.Chem.AllChem",
    "rdkit.Chem.Descriptors",
    "rdkit.Chem.rdMolDescriptors",
    "rdkit.Chem.Draw",
    "rdkit.Chem.rdDepictor",
    "rdkit.Chem.rdchem",
    "rdkit.Chem.rdMolTransforms",
    "rdkit.Chem.rdForceFieldHelpers",
    "rdkit.Chem.rdDistGeom",
    "rdkit.DataStructs",
    "rdkit.Geometry",
    # Open Babel
    "openbabel",
    "openbabel.openbabel",
    "openbabel.pybel",
    # Meeko / docking prep
    "meeko",
    "meeko.molecule_preparation",
    "meeko.writer",
    # Spectra dynamic imports
    "spectra.ir_predictor",
    "spectra.proton_nmr",
    "spectra.carbon_nmr",
    "spectra.functional_group_detector",
    # Matplotlib non-interactive backend
    "matplotlib.backends.backend_agg",
    # dotenv / requests
    "dotenv",
    "requests",
    "urllib3",
    "charset_normalizer",
    "idna",
    "certifi",
    # Optional protonation (graceful if absent)
    "dimorphite_dl",
    # py2opsin
    "py2opsin",
]

# Deduplicate while preserving order
_seen: set[str] = set()
_dedup_hidden: list[str] = []
for name in hiddenimports:
    if name and name not in _seen:
        _seen.add(name)
        _dedup_hidden.append(name)
hiddenimports = _dedup_hidden

_seen_d: set[tuple[str, str]] = set()
_dedup_datas: list[tuple[str, str]] = []
for item in datas:
    key = (str(item[0]), str(item[1]))
    if key not in _seen_d:
        _seen_d.add(key)
        _dedup_datas.append(item)
datas = _dedup_datas

_seen_b: set[tuple[str, str]] = set()
_dedup_bin: list[tuple[str, str]] = []
for item in binaries:
    key = (str(item[0]), str(item[1]))
    if key not in _seen_b:
        _seen_b.add(key)
        _dedup_bin.append(item)
binaries = _dedup_bin

# ---------------------------------------------------------------------------
# Analysis / PYZ / EXE / COLLECT (onedir only)
# ---------------------------------------------------------------------------
a = Analysis(
    [str(ROOT / "portable_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "tests",
        "pytest",
        "IPython",
        "jupyter",
        "notebook",
        "AutoDock_Vina",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binaries collected separately
    name="ChemistryCompanion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # scientific DLLs often break under UPX
    console=True,  # keep console for logs / troubleshooting
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # no app icon asset present yet
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ChemistryCompanion",
)
