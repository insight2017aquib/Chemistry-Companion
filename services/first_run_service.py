"""
services/first_run_service.py
=============================
First Run Experience (FRE) helpers for Chemistry Companion.

Handles:
- detecting whether setup is required
- default workspace paths
- scientific tool detection
- AI connection tests (friendly errors, no stack traces)
- .env creation / merge without silent overwrite
- optional sample dataset copy
- setup completion marker

Does not change scientific workflows; only configuration and UX.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

from core.paths import (
    database_path,
    docking_workspace_root,
    install_root,
    is_frozen,
    outputs_dir,
    package_root,
    runtime_root,
    sample_data_dir,
)

logger = logging.getLogger(__name__)

# Never log secret values
_SECRET_KEY_FRAGMENTS = ("API_KEY", "SECRET", "TOKEN", "PASSWORD")

APP_VERSION = "3.0.0"

PROVIDER_CATALOG: List[Dict[str, str]] = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "blurb": "Recommended for most users. Aggregates many models with free tiers.",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "blurb": "Highest compatibility with standard Chat Completions APIs.",
    },
    {
        "id": "groq",
        "name": "Groq",
        "blurb": "Very fast inference on supported open models.",
    },
    {
        "id": "ollama",
        "name": "Ollama (Local)",
        "blurb": "Runs completely locally on your machine — no cloud key required.",
    },
    {
        "id": "disabled",
        "name": "Disable AI",
        "blurb": "Chemistry Companion continues to work without AI assistance.",
    },
]

DEFAULT_MODELS = {
    "openrouter": "deepseek/deepseek-v4-flash:free",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3.2",
}


def config_root() -> Path:
    """Directory where .env and setup markers live (install/runtime root).

    * Frozen: directory of the executable (``install_root()``).
    * Override: ``CHEM_COMPANION_RUNTIME_DIR`` when set (portable bootstrap).
    * Dev: repository / package root (same place as historical ``.env``).
    """
    override = os.environ.get("CHEM_COMPANION_RUNTIME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return install_root()
    return package_root()


def env_path() -> Path:
    return config_root() / ".env"


def setup_marker_path() -> Path:
    return config_root() / ".cc_setup_complete"


def logs_dir() -> Path:
    override = os.environ.get("CHEM_COMPANION_LOG_PATH") or os.environ.get("LOG_PATH")
    if override:
        p = Path(override).expanduser()
        return p if p.suffix == "" else p.parent
    return runtime_root() / "logs" if not is_frozen() else (install_root() / "logs")


def workspace_dir() -> Path:
    """User-facing workspace root (docking / screening artefacts under outputs)."""
    return docking_workspace_root().parent


def _read_env_file(path: Path) -> Dict[str, str]:
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return data
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            data[key] = val
    return data


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return value[:4] + "•" * min(12, len(value) - 8) + value[-4:]


def needs_first_run() -> bool:
    """
    True when FRE should auto-launch.

    - No .env, or
    - Setup never completed (no marker and no SETUP_COMPLETE flag), or
    - Configuration incomplete (setup claimed complete but paths invalid)
    """
    env_file = env_path()
    marker = setup_marker_path()
    env = _read_env_file(env_file) if env_file.exists() else {}

    complete_flag = (
        env.get("CHEM_COMPANION_SETUP_COMPLETE", "").strip().lower() in ("1", "true", "yes")
        or marker.exists()
    )

    if not env_file.exists() and not complete_flag:
        return True
    if not complete_flag:
        return True

    # Incomplete: AI enabled but required key blank (treat as incomplete only if they never finished)
    provider = (env.get("AI_PROVIDER") or env.get("LLM_PROVIDER") or "").strip().lower()
    if provider and provider not in ("disabled", "none", "off", "template"):
        key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        key_name = key_map.get(provider)
        if key_name and not env.get(key_name) and provider != "ollama":
            # If setup was marked complete with empty key, respect skip/disable intent only when provider=disabled
            if not complete_flag:
                return True

    return False


def default_paths() -> Dict[str, str]:
    root = config_root()
    db = database_path()
    out = outputs_dir()
    logs = root / "logs"
    workspace = out  # docking/screening under outputs
    return {
        "database_path": str(db),
        "output_path": str(out),
        "log_path": str(logs),
        "workspace_path": str(workspace),
        "config_root": str(root),
        "env_path": str(env_path()),
        "env_exists": env_path().exists(),
        "setup_complete": not needs_first_run(),
    }


def ensure_dirs(paths: Dict[str, str]) -> List[str]:
    """Create missing directories; return list of created paths."""
    created: List[str] = []
    for key in ("output_path", "log_path", "workspace_path"):
        p = Path(paths[key]).expanduser()
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created.append(str(p))
        else:
            p.mkdir(parents=True, exist_ok=True)
    # DB parent
    db = Path(paths["database_path"]).expanduser()
    if db.suffix:
        db.parent.mkdir(parents=True, exist_ok=True)
    else:
        db.mkdir(parents=True, exist_ok=True)
    # docking workspace under outputs
    (Path(paths["output_path"]) / "docking_workspace").mkdir(parents=True, exist_ok=True)
    (Path(paths.get("workspace_path", paths["output_path"])) / "docking_workspace").mkdir(
        parents=True, exist_ok=True
    )
    return created


def _tool_version_cmd(cmd: List[str]) -> Tuple[bool, str, str]:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=12,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        out = (r.stdout or "") + (r.stderr or "")
        out = out.strip().splitlines()[0] if out.strip() else ""
        return (r.returncode == 0 or bool(out), out[:200], cmd[0])
    except FileNotFoundError:
        return False, "", cmd[0]
    except Exception as exc:  # noqa: BLE001 — friendly surface only
        logger.debug("tool detect failed for %s: %s", cmd, type(exc).__name__)
        return False, "", cmd[0]


def detect_scientific_tools() -> List[Dict[str, Any]]:
    """Detect RDKit, Open Babel, Vina, Java, OPSIN — never raises."""
    tools: List[Dict[str, Any]] = []

    # RDKit
    try:
        import rdkit
        from rdkit import Chem  # noqa: F401

        ver = getattr(rdkit, "__version__", "unknown")
        loc = getattr(rdkit, "__file__", "") or ""
        tools.append(
            {
                "id": "rdkit",
                "name": "RDKit",
                "status": "installed",
                "version": ver,
                "location": loc,
                "impact_if_missing": "Molecular analysis, descriptors, and 2D depiction would be unavailable.",
            }
        )
    except Exception:
        tools.append(
            {
                "id": "rdkit",
                "name": "RDKit",
                "status": "missing",
                "version": "",
                "location": "",
                "impact_if_missing": "Molecular analysis, descriptors, and structure rendering will not work.",
            }
        )

    # Open Babel
    try:
        import openbabel  # noqa: F401

        ok, ver, loc = _tool_version_cmd(
            [os.environ.get("OBABEL_BINARY") or os.environ.get("OBABEL_EXE") or "obabel", "-V"]
        )
        if not ok:
            # package present even if CLI not on PATH
            loc = getattr(openbabel, "__file__", "") or "python package"
            ver = ver or "python package"
            ok = True
        tools.append(
            {
                "id": "openbabel",
                "name": "Open Babel",
                "status": "installed" if ok else "missing",
                "version": ver or "unknown",
                "location": loc,
                "impact_if_missing": "Docking preparation (PDBQT export) and some 3D conversions may fail.",
            }
        )
    except Exception:
        ok, ver, loc = _tool_version_cmd(
            [os.environ.get("OBABEL_BINARY") or "obabel", "-V"]
        )
        tools.append(
            {
                "id": "openbabel",
                "name": "Open Babel",
                "status": "installed" if ok else "missing",
                "version": ver,
                "location": loc if ok else "",
                "impact_if_missing": "Docking preparation (PDBQT export) and some 3D conversions may fail.",
            }
        )

    # AutoDock Vina
    vina = os.environ.get("VINA_BINARY") or os.environ.get("VINA_EXE") or "vina"
    ok, ver, loc = _tool_version_cmd([vina, "--version"])
    if not ok and sys.platform == "win32":
        ok, ver, loc = _tool_version_cmd(["vina.exe", "--version"])
    tools.append(
        {
            "id": "vina",
            "name": "AutoDock Vina",
            "status": "installed" if ok else "missing",
            "version": ver or ("found" if ok else ""),
            "location": loc if ok else "",
            "impact_if_missing": "Docking runs and virtual screening will not execute until Vina is available.",
        }
    )

    # Java
    ok, ver, loc = _tool_version_cmd(["java", "-version"])
    tools.append(
        {
            "id": "java",
            "name": "Java Runtime (JRE)",
            "status": "installed" if ok else "missing",
            "version": ver,
            "location": "java on PATH" if ok else "",
            "impact_if_missing": "IUPAC name → SMILES via OPSIN may be unavailable.",
        }
    )

    # OPSIN (py2opsin package + jar)
    opsin_status = "missing"
    opsin_ver = ""
    opsin_loc = ""
    try:
        import py2opsin
        from pathlib import Path as P

        pkg = P(py2opsin.__file__).parent
        jars = list(pkg.glob("*.jar"))
        opsin_loc = str(pkg)
        if jars:
            opsin_status = "installed"
            opsin_ver = jars[0].name
        else:
            opsin_status = "partial"
            opsin_ver = "package present, JAR missing"
    except Exception:
        pass
    tools.append(
        {
            "id": "opsin",
            "name": "OPSIN (py2opsin)",
            "status": opsin_status if opsin_status != "partial" else "missing",
            "version": opsin_ver,
            "location": opsin_loc,
            "impact_if_missing": "Resolving chemical names to structures may fall back to online services only.",
        }
    )

    return tools


def test_ai_connection(
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    ollama_host: str = "127.0.0.1",
    ollama_port: int = 11434,
) -> Dict[str, Any]:
    """
    Validate provider connectivity. Returns friendly status — never secrets or tracebacks.
    """
    provider = (provider or "").strip().lower()
    if provider in ("disabled", "none", "off"):
        return {
            "ok": True,
            "message": "AI assistance is disabled. Chemistry Companion will work without AI features.",
        }

    model = model or DEFAULT_MODELS.get(provider, "")
    try:
        if provider == "ollama":
            host = (ollama_host or "127.0.0.1").strip()
            port = int(ollama_port or 11434)
            url = f"http://{host}:{port}/api/tags"
            r = requests.get(url, timeout=5)
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": "Could not reach Ollama. Confirm the app is running and the host/port are correct.",
                }
            return {
                "ok": True,
                "message": f"Connected to Ollama at {host}:{port}.",
            }

        if provider == "openrouter":
            if not api_key.strip():
                return {"ok": False, "message": "Please enter an OpenRouter API key."}
            url = (base_url or "https://openrouter.ai/api/v1/chat/completions").strip()
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/aquibbelal/chemistry-companion",
                "X-Title": "Chemistry Companion",
            }
            payload = {
                "model": model or DEFAULT_MODELS["openrouter"],
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                "max_tokens": 8,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            if r.status_code in (401, 403):
                return {"ok": False, "message": "API key was rejected. Check the key and try again."}
            if r.status_code == 429:
                return {"ok": False, "message": "Rate limited. Wait a moment and try again."}
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": "OpenRouter did not accept the test request. Check model name and key permissions.",
                }
            return {"ok": True, "message": "OpenRouter connection successful."}

        if provider == "openai":
            if not api_key.strip():
                return {"ok": False, "message": "Please enter an OpenAI API key."}
            url = (base_url or "https://api.openai.com/v1/chat/completions").strip()
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or DEFAULT_MODELS["openai"],
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                "max_tokens": 8,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            if r.status_code in (401, 403):
                return {"ok": False, "message": "API key was rejected. Check the key and try again."}
            if r.status_code == 429:
                return {"ok": False, "message": "Rate limited or quota exceeded. Try again later."}
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": "OpenAI did not accept the test request. Check the model name and account access.",
                }
            return {"ok": True, "message": "OpenAI connection successful."}

        if provider == "groq":
            if not api_key.strip():
                return {"ok": False, "message": "Please enter a Groq API key."}
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model or DEFAULT_MODELS["groq"],
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                "max_tokens": 8,
            }
            r = requests.post(url, headers=headers, json=payload, timeout=25)
            if r.status_code in (401, 403):
                return {"ok": False, "message": "API key was rejected. Check the key and try again."}
            if r.status_code == 429:
                return {"ok": False, "message": "Rate limited. Wait a moment and try again."}
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "message": "Groq did not accept the test request. Check the model name and key.",
                }
            return {"ok": True, "message": "Groq connection successful."}

        return {
            "ok": False,
            "message": "Unknown AI provider. Choose OpenRouter, OpenAI, Groq, Ollama, or Disable AI.",
        }
    except requests.exceptions.Timeout:
        return {"ok": False, "message": "The provider did not respond in time. Check your network and try again."}
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "message": "Could not connect to the provider. Check your network or local service (Ollama).",
        }
    except Exception:
        logger.exception("AI test failed (details not shown to user)")
        return {
            "ok": False,
            "message": "Connection test failed. Check your settings and try again.",
        }


def validate_paths(paths: Dict[str, str]) -> Dict[str, Any]:
    checks = []
    all_ok = True
    for label, key in (
        ("Database directory", "database_path"),
        ("Outputs", "output_path"),
        ("Logs", "log_path"),
        ("Workspace", "workspace_path"),
    ):
        raw = paths.get(key, "")
        p = Path(raw).expanduser()
        target = p.parent if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"} else p
        ok = False
        detail = ""
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / ".cc_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            ok = True
            detail = "Writable"
        except Exception:
            ok = False
            detail = "Not writable — choose another folder"
            all_ok = False
        checks.append({"name": label, "ok": ok, "detail": detail, "path": str(p)})
    return {"ok": all_ok, "checks": checks}


def _merge_env_lines(existing: Dict[str, str], updates: Dict[str, str]) -> str:
    """Build .env content: preserve unknown keys, update known keys."""
    merged = dict(existing)
    for k, v in updates.items():
        if v is None:
            continue
        merged[k] = str(v)

    # Preferred order for readability
    preferred = [
        "APP_VERSION",
        "CHEM_COMPANION_SETUP_COMPLETE",
        "AI_PROVIDER",
        "LLM_PROVIDER",
        "DEFAULT_FAST_PROVIDER",
        "OPENROUTER_API_KEY",
        "OPENROUTER_BASE_URL",
        "OPENROUTER_MODEL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "OLLAMA_HOST",
        "OLLAMA_PORT",
        "OLLAMA_MODEL",
        "DATABASE_PATH",
        "OUTPUT_PATH",
        "LOG_PATH",
        "WORKSPACE_PATH",
        "CHEM_COMPANION_DB_PATH",
        "CHEM_COMPANION_OUTPUTS_DIR",
        "CHEM_COMPANION_LOG_PATH",
        "CHEM_COMPANION_RUNTIME_DIR",
        "CHEM_COMPANION_DOCKING_WORKSPACE_DIR",
    ]
    lines = [
        "# Chemistry Companion configuration",
        "# Generated by the Setup Wizard. API keys are stored only on this machine.",
        "",
    ]
    seen = set()
    for key in preferred:
        if key in merged:
            lines.append(f"{key}={merged[key]}")
            seen.add(key)
    for key in sorted(merged.keys()):
        if key not in seen:
            lines.append(f"{key}={merged[key]}")
    lines.append("")
    return "\n".join(lines)


def write_env_config(
    *,
    paths: Dict[str, str],
    provider: str,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
    ollama_host: str = "127.0.0.1",
    ollama_port: int = 11434,
    force: bool = False,
    confirm_overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Create or update .env. Never overwrites an existing file without confirm_overwrite=True
    when force is False and file exists with content we would replace wholesale —
    we always merge keys, but still require confirm if file exists and confirm_overwrite is False
    for the first creation path... User said: Never overwrite existing .env without confirmation.

    Policy:
    - If .env does not exist: create
    - If .env exists and confirm_overwrite is False: return needs_confirmation
    - If confirm_overwrite True: merge updates into existing
    """
    path = env_path()
    existing = _read_env_file(path) if path.exists() else {}

    if path.exists() and not confirm_overwrite and not force:
        return {
            "ok": False,
            "needs_confirmation": True,
            "message": "A configuration file already exists. Confirm to update it with your wizard choices.",
            "path": str(path),
        }

    provider = (provider or "disabled").strip().lower()
    model = model or DEFAULT_MODELS.get(provider, "")

    updates: Dict[str, str] = {
        "APP_VERSION": APP_VERSION,
        "CHEM_COMPANION_SETUP_COMPLETE": "1",
        "AI_PROVIDER": provider,
        "LLM_PROVIDER": provider if provider != "disabled" else "template",
        "DATABASE_PATH": paths.get("database_path", ""),
        "OUTPUT_PATH": paths.get("output_path", ""),
        "LOG_PATH": paths.get("log_path", ""),
        "WORKSPACE_PATH": paths.get("workspace_path", ""),
        "CHEM_COMPANION_DB_PATH": paths.get("database_path", ""),
        "CHEM_COMPANION_OUTPUTS_DIR": paths.get("output_path", ""),
        "CHEM_COMPANION_LOG_PATH": paths.get("log_path", ""),
        "CHEM_COMPANION_RUNTIME_DIR": str(config_root()),
        "CHEM_COMPANION_DOCKING_WORKSPACE_DIR": str(
            Path(paths.get("output_path", "outputs")) / "docking_workspace"
        ),
        # Ensure key fields exist even when empty
        "OPENROUTER_API_KEY": existing.get("OPENROUTER_API_KEY", ""),
        "OPENAI_API_KEY": existing.get("OPENAI_API_KEY", ""),
        "GROQ_API_KEY": existing.get("GROQ_API_KEY", ""),
        "OLLAMA_HOST": ollama_host or existing.get("OLLAMA_HOST", "127.0.0.1"),
        "OLLAMA_PORT": str(ollama_port or existing.get("OLLAMA_PORT", "11434")),
        "OLLAMA_MODEL": existing.get("OLLAMA_MODEL", DEFAULT_MODELS["ollama"]),
        "OPENROUTER_BASE_URL": base_url or existing.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
        "OPENROUTER_MODEL": existing.get("OPENROUTER_MODEL", DEFAULT_MODELS["openrouter"]),
        "OPENAI_MODEL": existing.get("OPENAI_MODEL", DEFAULT_MODELS["openai"]),
        "GROQ_MODEL": existing.get("GROQ_MODEL", DEFAULT_MODELS["groq"]),
    }

    if provider == "openrouter":
        if api_key:
            updates["OPENROUTER_API_KEY"] = api_key.strip()
        if model:
            updates["OPENROUTER_MODEL"] = model
        if base_url:
            updates["OPENROUTER_BASE_URL"] = base_url
        updates["DEFAULT_FAST_PROVIDER"] = "openrouter"
    elif provider == "openai":
        if api_key:
            updates["OPENAI_API_KEY"] = api_key.strip()
        if model:
            updates["OPENAI_MODEL"] = model
        updates["DEFAULT_FAST_PROVIDER"] = "openai"
    elif provider == "groq":
        if api_key:
            updates["GROQ_API_KEY"] = api_key.strip()
        if model:
            updates["GROQ_MODEL"] = model
        updates["DEFAULT_FAST_PROVIDER"] = "groq"
    elif provider == "ollama":
        updates["OLLAMA_HOST"] = ollama_host or "127.0.0.1"
        updates["OLLAMA_PORT"] = str(ollama_port or 11434)
        if model:
            updates["OLLAMA_MODEL"] = model
        updates["DEFAULT_FAST_PROVIDER"] = "ollama"
    elif provider == "disabled":
        updates["LLM_PROVIDER"] = "template"
        updates["DEFAULT_FAST_PROVIDER"] = "template"

    content = _merge_env_lines(existing, updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    # Marker file
    try:
        setup_marker_path().write_text(
            f"setup_complete=1\nversion={APP_VERSION}\n", encoding="utf-8"
        )
    except OSError:
        logger.debug("Could not write setup marker", exc_info=True)

    # Apply to current process (no secret logging)
    for k, v in updates.items():
        if any(s in k.upper() for s in _SECRET_KEY_FRAGMENTS):
            if v:
                os.environ[k] = v
            continue
        os.environ[k] = v

    try:
        load_dotenv(path, override=True)
    except Exception:
        pass

    logger.info("Setup wizard wrote configuration to %s (provider=%s)", path, provider)
    return {
        "ok": True,
        "message": "Configuration saved.",
        "path": str(path),
        "provider": provider,
    }


def copy_sample_datasets() -> Dict[str, Any]:
    """Copy bundled sample CSVs into outputs/samples for the user."""
    dest = outputs_dir() / "samples"
    dest.mkdir(parents=True, exist_ok=True)
    src = sample_data_dir()
    copied = []
    for name in ("benchmark_molecules.csv", "spectra_benchmark.csv", "smiles_input.txt"):
        s = src / name
        if s.exists():
            d = dest / name
            shutil.copy2(s, d)
            copied.append(str(d))
    return {
        "ok": True,
        "copied": copied,
        "message": f"Copied {len(copied)} sample file(s) to {dest}."
        if copied
        else "No sample files found in the installation package.",
    }


def current_config_public() -> Dict[str, Any]:
    """Public (masked) view of current config for the wizard."""
    env = _read_env_file(env_path()) if env_path().exists() else {}
    provider = (env.get("AI_PROVIDER") or env.get("LLM_PROVIDER") or "disabled").lower()
    if provider in ("template", "none", "off"):
        provider = "disabled"
    paths = default_paths()
    # Prefer env overrides for paths
    if env.get("DATABASE_PATH") or env.get("CHEM_COMPANION_DB_PATH"):
        paths["database_path"] = env.get("DATABASE_PATH") or env.get("CHEM_COMPANION_DB_PATH")
    if env.get("OUTPUT_PATH") or env.get("CHEM_COMPANION_OUTPUTS_DIR"):
        paths["output_path"] = env.get("OUTPUT_PATH") or env.get("CHEM_COMPANION_OUTPUTS_DIR")
    if env.get("LOG_PATH") or env.get("CHEM_COMPANION_LOG_PATH"):
        paths["log_path"] = env.get("LOG_PATH") or env.get("CHEM_COMPANION_LOG_PATH")
    if env.get("WORKSPACE_PATH"):
        paths["workspace_path"] = env.get("WORKSPACE_PATH")

    return {
        "version": APP_VERSION,
        "needs_setup": needs_first_run(),
        "paths": paths,
        "provider": provider,
        "providers": PROVIDER_CATALOG,
        "defaults": {
            "models": DEFAULT_MODELS,
            "openrouter_base_url": "https://openrouter.ai/api/v1/chat/completions",
            "ollama_host": env.get("OLLAMA_HOST", "127.0.0.1"),
            "ollama_port": int(env.get("OLLAMA_PORT") or 11434),
        },
        "keys_present": {
            "openrouter": bool(env.get("OPENROUTER_API_KEY")),
            "openai": bool(env.get("OPENAI_API_KEY")),
            "groq": bool(env.get("GROQ_API_KEY")),
        },
        "masked": {
            "openrouter": _mask_secret(env.get("OPENROUTER_API_KEY", "")),
            "openai": _mask_secret(env.get("OPENAI_API_KEY", "")),
            "groq": _mask_secret(env.get("GROQ_API_KEY", "")),
        },
        "models": {
            "openrouter": env.get("OPENROUTER_MODEL", DEFAULT_MODELS["openrouter"]),
            "openai": env.get("OPENAI_MODEL", DEFAULT_MODELS["openai"]),
            "groq": env.get("GROQ_MODEL", DEFAULT_MODELS["groq"]),
            "ollama": env.get("OLLAMA_MODEL", DEFAULT_MODELS["ollama"]),
        },
    }


def final_validation(paths: Dict[str, str], provider: str) -> Dict[str, Any]:
    path_result = validate_paths(paths)
    items = list(path_result["checks"])
    env_ok = env_path().exists()
    items.append(
        {
            "name": "Configuration file",
            "ok": env_ok,
            "detail": "Readable" if env_ok else "Not found",
            "path": str(env_path()),
        }
    )
    prov = (provider or "disabled").lower()
    ai_ok = True
    if prov in ("disabled", "none", "off", ""):
        ai_detail = "AI intentionally disabled"
    elif prov == "ollama":
        ai_detail = "Ollama selected (local)"
    else:
        env = _read_env_file(env_path()) if env_path().exists() else {}
        key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        k = key_map.get(prov)
        ai_ok = bool(k and env.get(k))
        ai_detail = "API key configured" if ai_ok else "API key not set"
    items.append(
        {
            "name": "AI provider",
            "ok": ai_ok or prov in ("disabled", "ollama"),
            "detail": ai_detail,
            "path": prov or "disabled",
        }
    )
    ready = all(i["ok"] for i in items)
    return {
        "ok": ready,
        "ready_message": "Ready to use" if ready else "Setup needs attention",
        "checks": items,
    }
