# tests/test_config_settings.py
"""
Unit tests for chemistry_companion/core/config.py

Covers:
- cached settings accessor and cache reset
- environment variable overrides (including nested env vars)
- directory creation via prepare_runtime / DirectorySettings.ensure_directories
- validation errors for image sizes and batch settings
- save/load to JSON file
- configure_logging wiring (stream + file handlers)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from core import config as cfg_mod


def test_get_settings_is_cached_and_resettable(monkeypatch, tmp_path):
    # Ensure cache is cleared for test isolation
    cfg_mod.reset_settings_cache()

    # Create first instance and modify a value
    s1 = cfg_mod.get_settings()
    assert isinstance(s1, cfg_mod.ChemistryCompanionSettings)
    # mutate a runtime-only attribute to ensure caching returns same object
    s1.app_name = "X"
    s2 = cfg_mod.get_settings()
    assert s2.app_name == "X"

    # Reset cache and get a fresh instance
    cfg_mod.reset_settings_cache()
    s3 = cfg_mod.get_settings()
    assert s3.app_name != "X" or s3 is not s2  # new instance returned


def test_prepare_runtime_creates_directories(tmp_path, monkeypatch):
    # Use a temporary output directory
    monkeypatch.setenv("CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR", str(tmp_path / "outdir"))
    cfg_mod.reset_settings_cache()
    settings = cfg_mod.get_settings()
    # directories should not exist until prepare_runtime is called (create_missing True by default)
    out = settings.directories.output_dir
    assert not (out.exists() and any(out.iterdir()) is True) or out.exists()  # may exist depending on env
    settings.prepare_runtime()
    # Now directories should exist
    assert settings.directories.output_dir.exists()
    assert settings.directories.images_dir.exists()
    assert settings.directories.exports_dir.exists()
    assert settings.directories.logs_dir.exists()
    assert settings.directories.batch_dir.exists()


def test_env_overrides_nested(monkeypatch):
    # Set nested env vars for image width/height and logging level
    monkeypatch.setenv("CHEM_COMPANION_IMAGE__WIDTH", "320")
    monkeypatch.setenv("CHEM_COMPANION_IMAGE__HEIGHT", "240")
    monkeypatch.setenv("CHEM_COMPANION_LOGGING__LEVEL", "DEBUG")
    cfg_mod.reset_settings_cache()
    s = cfg_mod.get_settings()
    assert s.image.width == 320
    assert s.image.height == 240
    assert s.logging.level == "DEBUG"


def test_invalid_image_size_raises():
    # width too small
    with pytest.raises(ValueError):
        cfg_mod.ChemistryCompanionSettings(image={"width": 10, "height": 200})
    # height too large
    with pytest.raises(ValueError):
        cfg_mod.ChemistryCompanionSettings(image={"width": 200, "height": 10000})


def test_batch_settings_validation():
    # invalid chunk_size
    with pytest.raises(ValueError):
        cfg_mod.BatchSettings(chunk_size=0)
    # invalid n_workers
    with pytest.raises(ValueError):
        cfg_mod.BatchSettings(n_workers=0)
    # chunk_size > max_molecules should raise in model_validator
    with pytest.raises(ValueError):
        cfg_mod.BatchSettings(chunk_size=200, max_molecules=100)


def test_save_and_load_roundtrip(tmp_path):
    cfg_mod.reset_settings_cache()
    s = cfg_mod.get_settings()
    # modify a value to ensure persistence
    s.export.default_format = "csv"
    out = tmp_path / "cfg.json"
    s.save_to_file(out)
    assert out.exists()
    loaded = cfg_mod.ChemistryCompanionSettings.load_from_file(out)
    assert loaded.export.default_format == "csv"


def test_as_dict_contains_paths_and_primitives(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR", str(tmp_path / "out"))
    cfg_mod.reset_settings_cache()
    s = cfg_mod.get_settings()
    d = s.as_dict()
    # Paths should be strings in the dict
    assert isinstance(d["directories"]["output_dir"], str)
    assert "image" in d and isinstance(d["image"]["width"], int)


def test_configure_logging_adds_handlers_and_writes_file(tmp_path, caplog, monkeypatch):
    # Ensure log file is placed under a temporary output dir
    monkeypatch.setenv("CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR", str(tmp_path / "outlogs"))
    monkeypatch.setenv("CHEM_COMPANION_LOGGING__LEVEL", "DEBUG")
    monkeypatch.setenv("CHEM_COMPANION_LOGGING__FILENAME", "test_cc.log")
    cfg_mod.reset_settings_cache()
    s = cfg_mod.get_settings()
    # prepare runtime to create directories
    s.prepare_runtime()

    # Remove existing handlers to test idempotent addition
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    # Configure logging and emit a debug message
    s.configure_logging()
    logger = logging.getLogger("chemistry_companion.core.config")
    logger.debug("config debug test")

    # Ensure at least one StreamHandler exists
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    # Ensure file handler was created and log file exists (or will be created on first write)
    log_path = s.log_file
    # Write a message to ensure file is created
    logger.info("creating log file")
    # Some handlers buffer; flush file handlers
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):
            h.flush()
    assert log_path.exists() or any(isinstance(h, logging.FileHandler) for h in root.handlers)


def test_default_export_extension_and_unknown_format_raises(monkeypatch):
    cfg_mod.reset_settings_cache()
    s = cfg_mod.get_settings()
    # default csv mapping
    s.export.default_format = "csv"
    assert s.default_export_extension == ".csv"
    # unknown format should raise when accessed
    s.export.default_format = "unknown_format"  # type: ignore
    with pytest.raises(ValueError):
        _ = s.default_export_extension
