"""
Package-safe path resolution for Chemistry Companion.

Separates:

* **Package resources** (templates, static assets, bundled sample data) —
  resolved relative to the installed/source package tree via ``__file__``,
  never via absolute machine-specific paths.
* **Runtime writable locations** (SQLite DB, outputs, PAMS store, docking
  workspaces) — overridable via environment variables; defaults preserve
  existing development behaviour.

Environment overrides
---------------------
CHEM_COMPANION_RUNTIME_DIR
    Base directory for user-writable data (default: process cwd).
CHEM_COMPANION_DB_PATH
    Full path to the SQLite database file.
CHEM_COMPANION_OUTPUTS_DIR
    Directory mounted/served as ``/outputs`` and used for generated artifacts.
CHEM_COMPANION_PAMS_DIR
    Protein Asset Management System store root.
CHEM_COMPANION_DOCKING_WORKSPACE_DIR
    Docking workspace job directories.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


@lru_cache(maxsize=1)
def package_root() -> Path:
    """
    Root directory that contains the top-level packages
    (``api``, ``core``, ``templates``, ``static``, …).

    * Source / editable install: repository / site-packages parent of ``core``.
    * PyInstaller: ``sys._MEIPASS`` (the extracted/bundled ``_internal`` tree).
    """
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def install_root() -> Path:
    """
    Writable install directory for portable builds.

    * PyInstaller onedir: directory containing the executable.
    * Dev / pip install: same as ``package_root()``.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return package_root()


def resource_dir(*parts: str) -> Path:
    """Resolve a path under the package root (read-mostly resources)."""
    return package_root().joinpath(*parts)


def templates_dir() -> Path:
    """Jinja2 HTML templates directory."""
    return resource_dir("templates")


def static_dir() -> Path:
    """Static CSS / JS / image assets directory."""
    return resource_dir("static")


def sample_data_dir() -> Path:
    """Bundled sample / benchmark data directory."""
    return resource_dir("data")


def runtime_root() -> Path:
    """
    Writable base for user data.

    Defaults to the process current working directory so behaviour matches
    historical ``os.getcwd()`` usage for PAMS and docking workspaces.

    Frozen builds default to ``install_root()`` so portable runs are
    self-contained next to the executable.
    """
    override = os.environ.get("CHEM_COMPANION_RUNTIME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return install_root()
    return Path.cwd()


def database_path() -> Path:
    """
    SQLite database file path.

    * Dev default: ``<package_root>/chemistry_companion.db``
    * Frozen default: ``<install_root>/chemistry_companion.db`` (writable)
    """
    override = os.environ.get("CHEM_COMPANION_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return install_root() / "chemistry_companion.db"
    return package_root() / "chemistry_companion.db"


def database_url() -> str:
    """SQLAlchemy URL for the default SQLite database."""
    path = database_path()
    # SQLAlchemy on Windows accepts forward slashes in sqlite URLs.
    return f"sqlite:///{path.as_posix()}"


def outputs_dir() -> Path:
    """
    Generated outputs directory (descriptor benchmarks, spectra plots, docking).

    * Dev default: ``<package_root>/outputs``
    * Frozen default: ``<install_root>/outputs``
    """
    override = os.environ.get("CHEM_COMPANION_OUTPUTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return install_root() / "outputs"
    return package_root() / "outputs"


def pams_root() -> Path:
    """Protein asset store root (default: ``<runtime_root>/data/pams``)."""
    override = os.environ.get("CHEM_COMPANION_PAMS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return runtime_root() / "data" / "pams"


def docking_workspace_root() -> Path:
    """Docking job workspace root (default: ``<runtime_root>/outputs/docking_workspace``)."""
    override = os.environ.get("CHEM_COMPANION_DOCKING_WORKSPACE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return runtime_root() / "outputs" / "docking_workspace"


def ensure_runtime_directories() -> None:
    """Create common writable directories if missing (idempotent)."""
    for path in (
        outputs_dir(),
        docking_workspace_root(),
        pams_root(),
        database_path().parent,
        runtime_root() / "logs",
    ):
        path.mkdir(parents=True, exist_ok=True)


__all__ = [
    "is_frozen",
    "package_root",
    "install_root",
    "resource_dir",
    "templates_dir",
    "static_dir",
    "sample_data_dir",
    "runtime_root",
    "database_path",
    "database_url",
    "outputs_dir",
    "pams_root",
    "docking_workspace_root",
    "ensure_runtime_directories",
]
