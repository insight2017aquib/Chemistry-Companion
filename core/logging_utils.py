"""
chemistry_companion/core/logging_utils.py

Centralized, robust logging utilities for Chemistry Companion.

Features
- Idempotent configuration (avoids duplicate handlers)
- Console (stream) + rotating file logging (size- or time-based)
- Optional colored console output (uses colorama when available)
- Configurable verbosity and formatting
- Small Protocol to accept settings objects from core.config
- Type hints and docstrings
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, Union, runtime_checkable

# Optional color support
try:
    import colorama  # type: ignore
    from colorama import Fore, Style  # type: ignore

    _COLORAMA_AVAILABLE = True
    colorama.init(autoreset=True)
except Exception:
    _COLORAMA_AVAILABLE = False

# Marker attribute used to identify handlers added by this module
_HANDLER_MARKER = "_chemistry_companion_managed"

# Default application logger namespace
LOGGER_NAMESPACE = "chemistry_companion"


@runtime_checkable
class SupportsLoggingSettings(Protocol):
    """
    Protocol for settings objects consumable by configure_logging().

    Expected attributes:
      - logging: object with attributes `level`, `fmt`, `datefmt`, `log_to_file`
      - log_file: Path or str for the log file location (optional)
    """

    logging: object
    log_file: Optional[Union[str, Path]]


@dataclass(frozen=True)
class LoggingConfig:
    """
    Lightweight configuration container for logging.

    Attributes
    ----------
    level:
        Logging level name or numeric value (e.g., "DEBUG" or logging.DEBUG).
    log_file:
        Optional path to a log file. If None, file logging is disabled.
    rotate_by_time:
        If True, use TimedRotatingFileHandler; otherwise use RotatingFileHandler.
    rotate_when:
        Time rotation specifier (e.g., "midnight", "H") used when rotate_by_time=True.
    rotate_interval:
        Interval count for time-based rotation.
    rotate_max_bytes:
        Max bytes for size-based rotation.
    backup_count:
        Number of rotated files to keep.
    colored_console:
        If True, attempt colored console output (uses colorama if available).
    fmt:
        Log message format string.
    datefmt:
        Date format for log messages.
    """

    level: Union[str, int] = "INFO"
    log_file: Optional[Union[str, Path]] = None
    rotate_by_time: bool = False
    rotate_when: str = "midnight"
    rotate_interval: int = 1
    rotate_max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 7
    colored_console: bool = False
    fmt: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


# -------------------------
# Helpers
# -------------------------
def _coerce_level(level: Union[str, int]) -> int:
    """Convert textual or numeric level to logging level int."""
    if isinstance(level, int):
        return level
    if not isinstance(level, str) or not level.strip():
        raise ValueError("Logging level must be a non-empty string or integer.")
    name = level.strip().upper()
    if not hasattr(logging, name):
        raise ValueError(f"Unsupported logging level: {level!r}")
    val = getattr(logging, name)
    if not isinstance(val, int):
        raise ValueError(f"Unsupported logging level: {level!r}")
    return val


def _should_use_color(explicit: Optional[bool]) -> bool:
    """Decide whether to use colored console output."""
    if explicit is not None:
        return explicit and _COLORAMA_AVAILABLE
    if os.environ.get("NO_COLOR"):
        return False
    return _COLORAMA_AVAILABLE and sys.stderr.isatty()


def _mark_handler(handler: logging.Handler) -> None:
    """Mark a handler as managed by this module to avoid duplicates."""
    try:
        setattr(handler, _HANDLER_MARKER, True)
    except Exception:
        pass


def _is_managed_handler(handler: logging.Handler) -> bool:
    """Return True if handler was added by this module."""
    return bool(getattr(handler, _HANDLER_MARKER, False))


def _remove_managed_handlers(logger: logging.Logger) -> None:
    """Remove and close handlers previously added by this module for the given logger."""
    for h in list(logger.handlers):
        if _is_managed_handler(h):
            try:
                logger.removeHandler(h)
            except Exception:
                pass
            try:
                h.close()
            except Exception:
                pass


# -------------------------
# Formatters
# -------------------------
class _ColorFormatter(logging.Formatter):
    """Formatter that wraps levelname in ANSI color codes (uses colorama if available)."""

    LEVEL_COLORS = {
        "DEBUG": Fore.CYAN if _COLORAMA_AVAILABLE else "",
        "INFO": Fore.GREEN if _COLORAMA_AVAILABLE else "",
        "WARNING": Fore.YELLOW if _COLORAMA_AVAILABLE else "",
        "ERROR": Fore.RED if _COLORAMA_AVAILABLE else "",
        "CRITICAL": Fore.MAGENTA if _COLORAMA_AVAILABLE else "",
    }

    def format(self, record: logging.LogRecord) -> str:
        original = record.levelname
        color = self.LEVEL_COLORS.get(original, "")
        if color:
            record.levelname = f"{color}{original}{Style.RESET_ALL if _COLORAMA_AVAILABLE else ''}"
        try:
            return super().format(record)
        finally:
            record.levelname = original


def _make_formatter(fmt: str, datefmt: str, use_color: bool) -> logging.Formatter:
    """Return an appropriate formatter (colored or plain)."""
    if use_color and _COLORAMA_AVAILABLE:
        return _ColorFormatter(fmt=fmt, datefmt=datefmt)
    return logging.Formatter(fmt=fmt, datefmt=datefmt)


# -------------------------
# Public API
# -------------------------
def configure_logging(
    *,
    settings: Optional[SupportsLoggingSettings] = None,
    config: Optional[LoggingConfig] = None,
    level: Optional[Union[str, int]] = None,
    log_file: Optional[Union[str, Path]] = None,
    console: bool = True,
    file_logging: Optional[bool] = None,
    use_color: Optional[bool] = None,
    rotate_by_time: Optional[bool] = None,
    rotate_when: Optional[str] = None,
    rotate_interval: Optional[int] = None,
    rotate_max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
    logger_name: str = LOGGER_NAMESPACE,
    fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
    propagate: bool = False,
) -> logging.Logger:
    """
    Configure centralized logging for the application.

    This function is idempotent: calling it repeatedly replaces prior managed handlers
    rather than adding duplicates.

    Parameters
    ----------
    settings:
        Optional settings object (must follow SupportsLoggingSettings protocol).
    config:
        Optional LoggingConfig instance. Values here are defaults and overridden by explicit args.
    level:
        Logging level (string or int). If omitted, taken from config or settings.
    log_file:
        Explicit log file path. If omitted and settings provided, uses settings.log_file.
    console:
        Enable console logging.
    file_logging:
        Enable file logging. If None and settings provided, uses settings.logging.log_to_file.
    use_color:
        Enable colored console output. If None, auto-detect.
    rotate_by_time:
        If True, use TimedRotatingFileHandler; if False, use RotatingFileHandler.
    rotate_when:
        Time rotation specifier (e.g., "midnight") for time-based rotation.
    rotate_interval:
        Interval count for time-based rotation.
    rotate_max_bytes:
        Max bytes for size-based rotation.
    backup_count:
        Number of rotated files to keep.
    logger_name:
        Root logger name for the application.
    fmt:
        Log message format string.
    datefmt:
        Date format string.
    propagate:
        Whether the configured logger should propagate to parent loggers.

    Returns
    -------
    logging.Logger
        The configured application logger.
    """
    # Start with defaults from config if provided
    cfg = config or LoggingConfig()

    # Resolve values from settings if present
    resolved_level = level if level is not None else getattr(cfg, "level", "INFO")
    resolved_fmt = fmt if fmt is not None else getattr(cfg, "fmt", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    resolved_datefmt = datefmt if datefmt is not None else getattr(cfg, "datefmt", "%Y-%m-%d %H:%M:%S")
    resolved_log_file = Path(log_file) if log_file is not None else (Path(cfg.log_file) if cfg.log_file is not None else None)
    resolved_file_logging = file_logging if file_logging is not None else (True if cfg.log_file else False)
    resolved_rotate_by_time = rotate_by_time if rotate_by_time is not None else cfg.rotate_by_time
    resolved_rotate_when = rotate_when if rotate_when is not None else cfg.rotate_when
    resolved_rotate_interval = rotate_interval if rotate_interval is not None else cfg.rotate_interval
    resolved_rotate_max_bytes = rotate_max_bytes if rotate_max_bytes is not None else cfg.rotate_max_bytes
    resolved_backup_count = backup_count if backup_count is not None else cfg.backup_count
    resolved_use_color = _should_use_color(use_color if use_color is not None else cfg.colored_console)

    # If a settings object is provided, let it override unresolved values
    if settings is not None:
        # logging-level
        settings_level = getattr(settings.logging, "level", None)
        if level is None and settings_level is not None:
            resolved_level = settings_level
        # format/datefmt
        if fmt is None:
            resolved_fmt = getattr(settings.logging, "fmt", resolved_fmt)
        if datefmt is None:
            resolved_datefmt = getattr(settings.logging, "datefmt", resolved_datefmt)
        # file logging toggle
        if file_logging is None:
            resolved_file_logging = bool(getattr(settings.logging, "log_to_file", resolved_file_logging))
        # log file path
        if resolved_log_file is None:
            sf = getattr(settings, "log_file", None)
            if sf is not None:
                resolved_log_file = Path(sf)

    numeric_level = _coerce_level(resolved_level)

    # Validate rotation params
    if resolved_rotate_max_bytes is not None and resolved_rotate_max_bytes < 1:
        raise ValueError("rotate_max_bytes must be positive")
    if resolved_backup_count is not None and resolved_backup_count < 0:
        raise ValueError("backup_count must be zero or greater")

    app_logger = logging.getLogger(logger_name)
    app_logger.setLevel(numeric_level)
    app_logger.propagate = propagate

    # Remove previously managed handlers (idempotent)
    _remove_managed_handlers(app_logger)

    # Console handler
    if console:
        ch = logging.StreamHandler()
        ch.setLevel(numeric_level)
        ch.setFormatter(_make_formatter(resolved_fmt, resolved_datefmt, resolved_use_color))
        _mark_handler(ch)
        app_logger.addHandler(ch)

    # File handler (if enabled)
    if resolved_file_logging:
        if resolved_log_file is None:
            raise ValueError("File logging enabled but no log file path provided.")
        try:
            resolved_log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # best-effort; handler creation will fail if directory truly not writable
            pass

        # Avoid adding duplicate file handler for same path
        for h in app_logger.handlers:
            if _is_managed_handler(h) and isinstance(h, (logging.handlers.RotatingFileHandler, logging.handlers.TimedRotatingFileHandler)):
                existing = getattr(h, "baseFilename", None)
                if existing and Path(existing).resolve() == Path(resolved_log_file).resolve():
                    # already present for this path
                    break
        else:
            try:
                if resolved_rotate_by_time:
                    fh = logging.handlers.TimedRotatingFileHandler(
                        filename=str(resolved_log_file),
                        when=resolved_rotate_when,
                        interval=resolved_rotate_interval,
                        backupCount=resolved_backup_count,
                        encoding="utf-8",
                    )
                else:
                    fh = logging.handlers.RotatingFileHandler(
                        filename=str(resolved_log_file),
                        maxBytes=resolved_rotate_max_bytes,
                        backupCount=resolved_backup_count,
                        encoding="utf-8",
                    )
                fh.setLevel(numeric_level)
                fh.setFormatter(logging.Formatter(resolved_fmt, datefmt=resolved_datefmt))
                _mark_handler(fh)
                app_logger.addHandler(fh)
            except Exception as exc:
                # Fail gracefully: emit a warning to console logger
                app_logger.warning("Could not create file log handler (%s): %s", resolved_log_file, exc)

    return app_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Return a namespaced logger for application modules.

    Use this in modules instead of calling logging.getLogger directly to ensure
    consistent namespace and to avoid local handler setup.
    """
    if not name:
        return logging.getLogger(LOGGER_NAMESPACE)
    if name == LOGGER_NAMESPACE or name.startswith(f"{LOGGER_NAMESPACE}."):
        return logging.getLogger(name)
    cleaned = name.strip(". ")
    return logging.getLogger(f"{LOGGER_NAMESPACE}.{cleaned}")


def set_verbosity(level: Union[str, int], logger_name: str = LOGGER_NAMESPACE) -> None:
    """
    Update the level of the application logger and all managed handlers.
    """
    numeric = _coerce_level(level)
    logger = logging.getLogger(logger_name)
    logger.setLevel(numeric)
    for h in logger.handlers:
        if _is_managed_handler(h):
            h.setLevel(numeric)
