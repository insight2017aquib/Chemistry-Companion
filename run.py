from pathlib import Path
import pytest
from pydantic import ValidationError

from core.config import ChemistryCompanionSettings, get_settings, reset_settings_cache


def test_env_override(monkeypatch):
    reset_settings_cache()
    monkeypatch.setenv("CHEM_COMPANION_LOGGING__LEVEL", "DEBUG")
    s = get_settings()
    assert s.logging.level == "DEBUG"


def test_directory_creation(tmp_path):
    s = ChemistryCompanionSettings()
    s.directories.output_dir = tmp_path / "out"
    s.prepare_runtime()
    assert s.directories.output_dir.exists()


def test_invalid_image_width():
    with pytest.raises(ValidationError):
        ChemistryCompanionSettings(image={"width": 32})


def test_default_export_extension():
    s = ChemistryCompanionSettings(export={"default_format": "excel"})
    assert s.default_export_extension == ".xlsx"


def test_save_and_load(tmp_path):
    path = tmp_path / "config.json"
    s = ChemistryCompanionSettings()
    s.save_to_file(path)
    loaded = ChemistryCompanionSettings.load_from_file(path)
    assert loaded.app_name == s.app_name #how do i test this out using this script i pasted here