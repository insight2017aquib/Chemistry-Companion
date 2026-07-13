"""
PyInstaller entry point for the Chemistry Companion portable onedir build.

Boots the FastAPI application via Uvicorn. Ensures:

* freeze-aware resource paths (templates/static/data under sys._MEIPASS)
* writable DB / outputs / logs next to the executable
* Open Babel data directory and native tool binary discovery
* AutoDock Vina binary discovery from the bundle
* logging to console + install-root log file
"""

from __future__ import annotations

import logging
import os
import sys
import webbrowser
from pathlib import Path


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def _install_root() -> Path:
    if _frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _meipass() -> Path | None:
    if _frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return None


def _bootstrap_environment() -> Path:
    """Configure env vars and working directory before importing the app."""
    root = _install_root()
    # Keep relative .env / user files next to the executable in portable mode.
    try:
        os.chdir(root)
    except OSError:
        pass

    os.environ.setdefault("CHEM_COMPANION_RUNTIME_DIR", str(root))
    os.environ.setdefault("CHEM_COMPANION_DB_PATH", str(root / "chemistry_companion.db"))
    os.environ.setdefault("CHEM_COMPANION_OUTPUTS_DIR", str(root / "outputs"))
    os.environ.setdefault("CHEM_COMPANION_PAMS_DIR", str(root / "data" / "pams"))
    os.environ.setdefault(
        "CHEM_COMPANION_DOCKING_WORKSPACE_DIR",
        str(root / "outputs" / "docking_workspace"),
    )

    meipass = _meipass()
    search_roots = [root]
    if meipass is not None:
        search_roots.append(meipass)
        search_roots.append(meipass / "openbabel" / "bin")
        search_roots.append(meipass / "bin")

    # Open Babel data files (atom types, force fields, format plugins)
    for base in search_roots:
        babel_data = base / "data" if (base / "data" / "atomtyp.txt").exists() else base / "openbabel" / "bin" / "data"
        if babel_data.is_dir() and (babel_data / "atomtyp.txt").exists():
            os.environ.setdefault("BABEL_DATADIR", str(babel_data))
            os.environ.setdefault("BABEL_LIBDIR", str(babel_data.parent))
            break

    # AutoDock Vina native CLI
    for base in search_roots:
        for name in ("vina.exe", "vina"):
            candidate = base / name
            if candidate.is_file():
                os.environ.setdefault("VINA_BINARY", str(candidate))
                os.environ.setdefault("VINA_EXE", str(candidate))
                break
        if os.environ.get("VINA_BINARY"):
            break

    # Open Babel CLI (obabel)
    for base in search_roots:
        for name in ("obabel.exe", "obabel"):
            candidate = base / name
            if candidate.is_file():
                os.environ.setdefault("OBABEL_BINARY", str(candidate))
                os.environ.setdefault("OBABEL_EXE", str(candidate))
                break
        if os.environ.get("OBABEL_BINARY"):
            break
        # openbabel package layout
        nested = base / "openbabel" / "bin" / ("obabel.exe" if os.name == "nt" else "obabel")
        if nested.is_file():
            os.environ.setdefault("OBABEL_BINARY", str(nested))
            os.environ.setdefault("OBABEL_EXE", str(nested))
            break

    return root


def _configure_logging(install_root: Path) -> None:
    log_dir = install_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "chemistry_companion.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root.handlers):
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)

    logging.getLogger(__name__).info("Logging to %s", log_path)


def main() -> None:
    install = _bootstrap_environment()
    _configure_logging(install)

    # Create writable dirs *before* importing api.app so StaticFiles can mount /outputs.
    from core.paths import (
        database_path,
        ensure_runtime_directories,
        is_frozen,
        outputs_dir,
        package_root,
        static_dir,
        templates_dir,
    )

    ensure_runtime_directories()

    logger = logging.getLogger("chemistry_companion.portable")
    logger.info("Frozen=%s", is_frozen())
    logger.info("Package root (resources)=%s", package_root())
    logger.info("Install root=%s", install)
    logger.info("Templates=%s exists=%s", templates_dir(), templates_dir().exists())
    logger.info("Static=%s exists=%s", static_dir(), static_dir().exists())
    logger.info("Outputs=%s", outputs_dir())
    logger.info("Database=%s", database_path())
    logger.info("VINA_BINARY=%s", os.environ.get("VINA_BINARY", "<unset>"))
    logger.info("OBABEL_BINARY=%s", os.environ.get("OBABEL_BINARY", "<unset>"))
    logger.info("BABEL_DATADIR=%s", os.environ.get("BABEL_DATADIR", "<unset>"))

    if not templates_dir().exists():
        logger.error("Templates directory missing — bundle is incomplete.")
        sys.exit(2)
    if not static_dir().exists():
        logger.warning("Static directory missing — UI assets may not load.")

    import uvicorn

    from api.app import app

    host = os.environ.get("CHEM_COMPANION_HOST", "127.0.0.1")
    port = int(os.environ.get("CHEM_COMPANION_PORT", "8000"))
    open_browser = os.environ.get("CHEM_COMPANION_OPEN_BROWSER", "1").strip() not in (
        "0",
        "false",
        "False",
        "no",
        "NO",
    )

    url = f"http://{host}:{port}"
    logger.info("Starting Chemistry Companion at %s", url)

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception as exc:  # pragma: no cover
            logger.debug("Could not open browser: %s", exc)

    # Pass the app object directly — string imports break under PyInstaller.
    uvicorn.run(app, host=host, port=port, log_level="info", reload=False)


if __name__ == "__main__":
    main()
