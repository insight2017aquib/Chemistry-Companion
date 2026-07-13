"""
chemistry_companion/core/config.py

Centralized, production-ready configuration module for Chemistry Companion.

Features
--------
- Nested settings models (directories, logging, image, export, batch)
- Pydantic v2 / pydantic-settings BaseSettings usage with environment variable support
- env_prefix and env_nested_delimiter for nested env vars
- Validation and cross-field checks
- Convenience helpers: get_settings (cached), reset_settings_cache, as_dict,
  save_to_file, load_from_file
- Logging configuration helper that safely wires stream + file handlers
- Type hints, docstrings, and defensive error handling
- Designed for modular growth across cheminformatics, spectroscopy, export,
  and batch-processing workflows

Environment variables
---------------------
The top-level settings class uses:

env_prefix = "CHEM_COMPANION_"
env_nested_delimiter = "__"

Examples:
CHEM_COMPANION_LOGGING__LEVEL=DEBUG
CHEM_COMPANION_IMAGE__WIDTH=800
CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR=/tmp/results
CHEM_COMPANION_LLM__PROVIDER=deepseek
CHEM_COMPANION_LLM__ENABLE_LLM=true
CHEM_COMPANION_LLM__MAX_RETRIES=3
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
ExportFormat = Literal["csv", "excel", "pdf"]
ImageFormat = Literal["png", "svg"]
LLMProvider = Literal["deepseek", "openrouter", "groq", "gemini"]
BatchErrorMode = Literal["continue", "stop"]


class DirectorySettings(BaseModel):
    """
    Output directory configuration.

    Attributes
    ----------
    output_dir:
        Root directory for generated outputs.
    images_dir_name:
        Subdirectory name for structure images.
    exports_dir_name:
        Subdirectory name for CSV/Excel/PDF exports.
    logs_dir_name:
        Subdirectory name for log files.
    batch_dir_name:
        Subdirectory name for batch-processing artifacts.
    create_missing:
        If True, create directories on demand.
    """

    output_dir: Path = Field(default=Path("output"), description="Root directory for generated outputs")
    images_dir_name: str = Field(default="images", description="Subdirectory name for images")
    exports_dir_name: str = Field(default="exports", description="Subdirectory name for exports")
    logs_dir_name: str = Field(default="logs", description="Subdirectory name for logs")
    batch_dir_name: str = Field(default="batch", description="Subdirectory name for batch artifacts")
    create_missing: bool = Field(default=True, description="Create directories on demand")

    @field_validator("output_dir", mode="before")
    @classmethod
    def _coerce_output_dir(cls, v: Union[str, Path]) -> Path:
        if isinstance(v, Path):
            return v.expanduser()
        if not isinstance(v, str) or not v.strip():
            raise ValueError("output_dir must be a non-empty path")
        return Path(v).expanduser()

    @field_validator("images_dir_name", "exports_dir_name", "logs_dir_name", "batch_dir_name")
    @classmethod
    def _validate_dir_name(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("directory name must be a non-empty string")
        cleaned = v.strip().strip("/\\")
        if not cleaned:
            raise ValueError("directory name cannot be only path separators")
        if Path(cleaned).name != cleaned:
            raise ValueError("directory name must be a simple name, not a nested path")
        return cleaned

    @property
    def images_dir(self) -> Path:
        return self.output_dir / self.images_dir_name

    @property
    def exports_dir(self) -> Path:
        return self.output_dir / self.exports_dir_name

    @property
    def logs_dir(self) -> Path:
        return self.output_dir / self.logs_dir_name

    @property
    def batch_dir(self) -> Path:
        return self.output_dir / self.batch_dir_name

    def ensure_directories(self) -> None:
        """
        Create configured directories if create_missing is enabled.
        """
        if not self.create_missing:
            return
        for p in (self.output_dir, self.images_dir, self.exports_dir, self.logs_dir, self.batch_dir):
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                raise RuntimeError(f"Could not create directory {p}: {exc}") from exc


class LoggingSettings(BaseModel):
    """
    Logging configuration.

    Attributes
    ----------
    level:
        Global logging level.
    log_to_file:
        Whether file logging is enabled.
    filename:
        Log filename placed under directories.logs_dir.
    fmt:
        Logging message format.
    datefmt:
        Datetime format for logging.
    """

    level: LogLevel = Field(default="INFO", description="Global logging level")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    filename: str = Field(default="chemistry_companion.log", description="Log filename")
    fmt: str = Field(
        default="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        description="Log format",
    )
    datefmt: str = Field(default="%Y-%m-%d %H:%M:%S", description="Datetime format for logs")

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("log filename must be a non-empty string")
        cleaned = v.strip()
        if Path(cleaned).name != cleaned:
            raise ValueError("log filename must not include directories")
        return cleaned


class ImageSettings(BaseModel):
    """
    Image/rendering defaults.

    Attributes
    ----------
    width:
        Image width in pixels.
    height:
        Image height in pixels.
    dpi:
        Raster DPI for saved figures.
    background_color:
        Background color where supported by renderer backends.
    image_format:
        Default image format.
    fit_image:
        Whether renderers should fit output tightly to the molecule.
    """

    width: int = Field(default=500, description="Image width in pixels")
    height: int = Field(default=500, description="Image height in pixels")
    dpi: int = Field(default=200, description="Raster DPI for saved figures")
    background_color: str = Field(default="white", description="Background color for renders")
    image_format: ImageFormat = Field(default="png", description="Default image format")
    fit_image: bool = Field(default=True, description="Fit output tightly to the molecule")

    @field_validator("width", "height")
    @classmethod
    def _validate_size(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("image dimensions must be integers")
        if v < 128 or v > 4096:
            raise ValueError("image dimensions must be between 128 and 4096 pixels")
        return v

    @field_validator("dpi")
    @classmethod
    def _validate_dpi(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("dpi must be an integer")
        if v < 72 or v > 1200:
            raise ValueError("dpi must be between 72 and 1200")
        return v

    @property
    def size(self) -> Tuple[int, int]:
        return (self.width, self.height)


class ExportSettings(BaseModel):
    """
    Export defaults.

    Attributes
    ----------
    default_format:
        Default tabular/report export format.
    include_timestamp:
        Whether timestamps are added to generated filenames.
    include_index:
        Whether DataFrame index is included in tabular exports.
    excel_sheet_name:
        Default Excel worksheet name.
    pdf_title:
        Default PDF report title.
    csv_encoding:
        Default CSV encoding.
    """

    default_format: ExportFormat = Field(default="csv", description="Default export format")
    include_timestamp: bool = Field(default=True, description="Include timestamp in filenames")
    include_index: bool = Field(default=False, description="Include DataFrame index in tabular exports")
    excel_sheet_name: str = Field(default="ChemistryCompanion", description="Default Excel sheet name")
    pdf_title: str = Field(default="Chemistry Companion Report", description="Default PDF title")
    csv_encoding: str = Field(default="utf-8", description="CSV encoding")

    @field_validator("excel_sheet_name")
    @classmethod
    def _validate_sheet_name(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("excel_sheet_name must be a non-empty string")
        cleaned = v.strip()
        if len(cleaned) > 31:
            raise ValueError("excel_sheet_name must be 31 characters or fewer")
        invalid = set('[]:*?/\\')
        if any(ch in invalid for ch in cleaned):
            raise ValueError("excel_sheet_name contains invalid Excel characters")
        return cleaned

    @field_validator("pdf_title", "csv_encoding")
    @classmethod
    def _validate_nonempty_text(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("value must be a non-empty string")
        return v.strip()


class BatchSettings(BaseModel):
    """
    Batch-processing configuration.

    Attributes
    ----------
    enabled:
        Enable batch mode by default.
    chunk_size:
        Number of molecules processed per chunk.
    max_molecules:
        Optional upper bound for a batch job.
    error_mode:
        Whether batch processing continues or stops on per-record failure.
    save_intermediate:
        Whether intermediate chunk outputs are persisted.
    n_workers:
        Number of worker threads/processes requested.
    """

    enabled: bool = Field(default=False, description="Enable batch mode by default")
    chunk_size: int = Field(default=100, description="Number of molecules processed per chunk")
    max_molecules: Optional[int] = Field(default=None, description="Optional upper bound for a batch job")
    error_mode: BatchErrorMode = Field(default="continue", description="continue or stop on failure")
    save_intermediate: bool = Field(default=False, description="Persist intermediate outputs")
    n_workers: int = Field(default=1, description="Number of worker processes/threads requested")

    @field_validator("chunk_size")
    @classmethod
    def _validate_chunk_size(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("chunk_size must be an integer")
        if v < 1 or v > 100_000:
            raise ValueError("chunk_size must be between 1 and 100000")
        return v

    @field_validator("max_molecules")
    @classmethod
    def _validate_max_molecules(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return v
        if not isinstance(v, int):
            raise TypeError("max_molecules must be an integer or None")
        if v < 1:
            raise ValueError("max_molecules must be positive")
        return v

    @field_validator("n_workers")
    @classmethod
    def _validate_workers(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("n_workers must be an integer")
        if v < 1 or v > 256:
            raise ValueError("n_workers must be between 1 and 256")
        return v

    @model_validator(mode="after")
    def _validate_consistency(self) -> "BatchSettings":
        if self.max_molecules is not None and self.chunk_size > self.max_molecules:
            raise ValueError("chunk_size cannot exceed max_molecules when max_molecules is set")
        return self


class LLMSettings(BaseModel):
    """
    LLM explanation configuration.

    Controls which provider is used for AI-powered explanations, the
    automatic fallback chain, retry behaviour, caching, and the
    deterministic template fallback.

    Supported providers: ``"groq"``, ``"deepseek"``, ``"openrouter"``.

    Fallback strategy
    -----------------
    1. Try ``primary_provider`` first.
    2. On failure, iterate through ``fallback_providers`` in order.
    3. If *all* LLM providers fail and ``enable_fallback`` is ``True``,
       return a deterministic template-based explanation (zero API calls).

    Rate-limit notes (free tiers)
    -----------------------------
    - **Groq free tier**: ~30 requests/min, 14 400 tokens/min for most
      models.  Ideal for short chemistry explanations.
    - **DeepSeek**: Pay-per-token; watch for "Insufficient Balance".
    - **OpenRouter free models**: Generous but may queue under load.

    Attributes
    ----------
    primary_provider:
        First provider to try (``"groq"``, ``"deepseek"``,
        ``"openrouter"``).
    fallback_providers:
        Ordered list of providers to try when ``primary_provider`` fails.
        Providers without a configured API key are silently skipped.
    enable_llm:
        Master switch.  When ``False``, all requests immediately use the
        deterministic template fallback (zero API calls).
    enable_fallback:
        If ``True``, the system silently degrades to templates when *all*
        LLM providers fail.  When ``False``, failures are surfaced.
    cache_enabled:
        If ``True``, explanations are cached in-memory to reduce repeated
        API calls for identical inputs.
    max_retries:
        Number of attempts (with exponential back-off) for retryable
        errors such as rate-limits or transient network failures.

    Examples
    --------
    Via environment variables::

        CHEM_COMPANION_LLM__PRIMARY_PROVIDER=groq
        CHEM_COMPANION_LLM__ENABLE_LLM=true
        CHEM_COMPANION_LLM__MAX_RETRIES=3

    Via Python::

        settings.llm.primary_provider = "deepseek"
        settings.llm.fallback_providers = ["groq", "openrouter"]
    """

    primary_provider: LLMProvider = Field(
        default="groq",
        description="Primary LLM provider to try first",
    )
    fallback_providers: list[str] = Field(
        default_factory=lambda: ["groq", "deepseek"],
        description="Ordered list of fallback providers when primary fails",
    )
    enable_llm: bool = Field(
        default=True,
        description="Master switch for LLM-powered explanations",
    )
    enable_fallback: bool = Field(
        default=True,
        description="Allow silent degradation to template-based explanations",
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable in-memory explanation cache",
    )
    max_retries: int = Field(
        default=2,
        description="Retry count for transient LLM errors",
    )

    @field_validator("max_retries")
    @classmethod
    def _validate_max_retries(cls, v: int) -> int:
        if not isinstance(v, int):
            raise TypeError("max_retries must be an integer")
        if v < 1 or v > 10:
            raise ValueError("max_retries must be between 1 and 10")
        return v

    @field_validator("fallback_providers", mode="before")
    @classmethod
    def _validate_fallback_providers(cls, v: Any) -> list[str]:
        """Accept comma-separated string from env vars or a list."""
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        if isinstance(v, list):
            return [str(p).strip() for p in v if str(p).strip()]
        raise TypeError("fallback_providers must be a list or comma-separated string")


class ExternalToolsSettings(BaseModel):
    """
    Configuration for external scientific tools (ChimeraX, etc.).

    These tools are treated as optional power features, similar to how
    optional LLM providers are handled.
    """

    chimera_executable: Optional[str] = Field(
        default=None,
        description="Full path to ChimeraX (or classic Chimera) executable. "
                    "Example: C:\\\\Program Files\\\\ChimeraX\\\\bin\\\\ChimeraX.exe"
    )
    prefer_chimerax: bool = Field(
        default=True,
        description="Prefer ChimeraX over classic Chimera when both are configured"
    )
    auto_launch: bool = Field(
        default=False,
        description="Attempt to automatically launch ChimeraX when 'Open in ChimeraX' is clicked"
    )


class ChemistryCompanionSettings(BaseSettings):
    """
    Top-level application settings.

    Environment variables are read with prefix `CHEM_COMPANION_` and nested keys
    use the delimiter `__`.

    Examples
    --------
    CHEM_COMPANION_LOGGING__LEVEL=DEBUG
    CHEM_COMPANION_IMAGE__WIDTH=800
    CHEM_COMPANION_LLM__PRIMARY_PROVIDER=groq
    CHEM_COMPANION_LLM__FALLBACK_PROVIDERS=groq,deepseek
    CHEM_COMPANION_DIRECTORIES__OUTPUT_DIR=/tmp/results
    """

    model_config = SettingsConfigDict(
        env_prefix="CHEM_COMPANION_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="Chemistry Companion", description="Application name")
    version: str = Field(default="3.0.0", description="Application version (align with pyproject.toml)")
    directories: DirectorySettings = Field(default_factory=DirectorySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    image: ImageSettings = Field(default_factory=ImageSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    batch: BatchSettings = Field(default_factory=BatchSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    external_tools: ExternalToolsSettings = Field(default_factory=ExternalToolsSettings)

    @field_validator("app_name")
    @classmethod
    def _validate_app_name(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("app_name must be a non-empty string")
        return v.strip()

    def prepare_runtime(self) -> "ChemistryCompanionSettings":
        """
        Ensure configured runtime directories exist.

        Returns
        -------
        ChemistryCompanionSettings
            The current settings object for fluent usage.
        """
        self.directories.ensure_directories()
        return self

    @property
    def log_file(self) -> Path:
        """
        Full path to the configured log file.
        """
        return self.directories.logs_dir / self.logging.filename

    @property
    def default_export_extension(self) -> str:
        """
        Return the default file extension for exports.

        Raises
        ------
        ValueError
            If the configured default export format is unsupported.
        """
        mapping = {
            "csv": ".csv",
            "excel": ".xlsx",
            "pdf": ".pdf",
        }

        fmt = str(self.export.default_format).strip().lower()
        if fmt not in mapping:
            supported = ", ".join(mapping.keys())
            raise ValueError(
                f"Unsupported export format: {self.export.default_format!r}. "
                f"Supported formats: {supported}"
            )
        return mapping[fmt]

    def as_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-serializable snapshot of settings.

        Path objects are converted to strings recursively.
        """
        data = self.model_dump()

        def _convert(obj: Any) -> Any:
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_convert(x) for x in obj]
            if isinstance(obj, tuple):
                return tuple(_convert(x) for x in obj)
            return obj

        return _convert(data)

    def save_to_file(self, path: Union[str, Path]) -> None:
        """
        Save current settings to a JSON file.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf8") as fh:
            json.dump(self.as_dict(), fh, indent=2, ensure_ascii=False)
        logger.debug("Settings saved to %s", p)

    @classmethod
    def load_from_file(cls, path: Union[str, Path]) -> "ChemistryCompanionSettings":
        """
        Load settings from a JSON file.

        Environment variables still override file values.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        with p.open("r", encoding="utf8") as fh:
            data = json.load(fh)
        return cls(**data)

    def configure_logging(self) -> None:
        """
        Configure the root logger according to current settings.

        Adds:
        - one console StreamHandler if not already present
        - one FileHandler if file logging is enabled and not already present

        This function is designed to be idempotent.
        """
        root = logging.getLogger()
        level = getattr(logging, self.logging.level, logging.INFO)
        root.setLevel(level)

        formatter = logging.Formatter(self.logging.fmt, datefmt=self.logging.datefmt)

        has_console_stream = any(type(h) is logging.StreamHandler for h in root.handlers)
        if not has_console_stream:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            root.addHandler(stream_handler)

        if self.logging.log_to_file:
            log_path = self.log_file
            try:
                log_path.parent.mkdir(parents=True, exist_ok=True)
                has_matching_file = any(
                    isinstance(h, logging.FileHandler) and Path(getattr(h, "baseFilename", "")) == log_path
                    for h in root.handlers
                )
                if not has_matching_file:
                    file_handler = logging.FileHandler(log_path, encoding="utf8")
                    file_handler.setFormatter(formatter)
                    root.addHandler(file_handler)
            except Exception as exc:
                logger.debug("Could not create log file handler: %s", exc)


@lru_cache(maxsize=1)
def get_settings() -> ChemistryCompanionSettings:
    """
    Return a cached settings instance.

    Use reset_settings_cache() in tests when environment variables change.
    """
    return ChemistryCompanionSettings()


def reset_settings_cache() -> None:
    """
    Clear the cached settings instance.

    Useful in tests when environment variables are modified.
    """
    get_settings.cache_clear()


__all__ = [
    "BatchErrorMode",
    "BatchSettings",
    "ChemistryCompanionSettings",
    "DirectorySettings",
    "ExportFormat",
    "ExportSettings",
    "ImageFormat",
    "ImageSettings",
    "LLMProvider",
    "LLMSettings",
    "LogLevel",
    "LoggingSettings",
    "get_settings",
    "reset_settings_cache",
]