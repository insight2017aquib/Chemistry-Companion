"""
tests/test_logging_utils.py

Unit tests for core/logging_utils.py

Covers:
- idempotent configuration (no duplicate handlers)
- console handler presence and message emission
- file handler creation and path correctness
- set_verbosity updates managed handlers
- colored console option toggling (best-effort)
- graceful fallback when file handler cannot be created
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import pytest

from core import logging_utils as lu


def _remove_managed_from_root() -> None:
    """
    Remove handlers managed by logging_utils from the application logger.
    """
    root = logging.getLogger(lu.LOGGER_NAMESPACE)
    for handler in list(root.handlers):
        if getattr(handler, lu._HANDLER_MARKER, False):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    root.propagate = True


def test_configure_logging_adds_console_handler(caplog):
    """
    configure_logging should attach a managed console handler and emit records.
    """
    _remove_managed_from_root()
    caplog.set_level(logging.DEBUG, logger=lu.LOGGER_NAMESPACE)

    cfg = lu.LoggingConfig(level="DEBUG", colored_console=False)
    logger = lu.configure_logging(
        config=cfg,
        console=True,
        file_logging=False,
        propagate=True,
    )

    assert any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, lu._HANDLER_MARKER, False)
        for handler in logger.handlers
    )

    logger.debug("debug-test")

    assert any("debug-test" in record.message for record in caplog.records)


def test_configure_logging_adds_rotating_file_handler(tmp_path):
    """
    configure_logging should attach a managed rotating file handler with the
    expected resolved file path.
    """
    _remove_managed_from_root()

    logfile = tmp_path / "logs" / "app.log"
    cfg = lu.LoggingConfig(
        level="INFO",
        log_file=logfile,
        rotate_by_time=False,
        rotate_max_bytes=1024,
        backup_count=2,
    )
    logger = lu.configure_logging(config=cfg, console=False, file_logging=True)

    found = False
    for handler in logger.handlers:
        if getattr(handler, lu._HANDLER_MARKER, False) and isinstance(
            handler, logging.handlers.RotatingFileHandler
        ):
            found = True
            assert Path(getattr(handler, "baseFilename", "")).resolve() == logfile.resolve()

    assert found


def test_idempotent_configuration(tmp_path):
    """
    Repeated configuration should not duplicate managed handlers.
    """
    _remove_managed_from_root()

    logfile = tmp_path / "logs" / "app2.log"
    cfg = lu.LoggingConfig(level="INFO", log_file=logfile)

    logger = lu.configure_logging(config=cfg)
    initial = sum(1 for handler in logger.handlers if getattr(handler, lu._HANDLER_MARKER, False))

    logger2 = lu.configure_logging(config=cfg)
    after = sum(1 for handler in logger2.handlers if getattr(handler, lu._HANDLER_MARKER, False))

    assert initial == after


def test_set_verbosity_updates_handlers(caplog):
    """
    set_verbosity should update logger and managed handler levels.
    """
    _remove_managed_from_root()
    caplog.set_level(logging.DEBUG, logger=lu.LOGGER_NAMESPACE)

    cfg = lu.LoggingConfig(level="INFO", colored_console=False)
    logger = lu.configure_logging(
        config=cfg,
        console=True,
        file_logging=False,
        propagate=True,
    )

    logger.debug("should-not-see")
    assert not any("should-not-see" in record.message for record in caplog.records)

    lu.set_verbosity("DEBUG")
    logger.debug("now-see")

    assert any("now-see" in record.message for record in caplog.records)
    assert logger.level == logging.DEBUG
    assert all(
        handler.level == logging.DEBUG
        for handler in logger.handlers
        if getattr(handler, lu._HANDLER_MARKER, False)
    )


def test_colored_console_toggle(monkeypatch):
    """
    Enabling colored console output should still create a managed stream handler.
    """
    _remove_managed_from_root()

    monkeypatch.setattr(lu, "_COLORAMA_AVAILABLE", True)

    cfg = lu.LoggingConfig(level="INFO", colored_console=True)
    logger = lu.configure_logging(config=cfg, console=True, file_logging=False)

    assert any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, lu._HANDLER_MARKER, False)
        for handler in logger.handlers
    )

    monkeypatch.setattr(lu, "_COLORAMA_AVAILABLE", False)


def test_file_handler_fallback_on_bad_path():
    """
    File handler creation failure should not raise if console logging is enabled.
    """
    _remove_managed_from_root()

    bad_path = Path("/") / "app.log"
    cfg = lu.LoggingConfig(level="INFO", log_file=bad_path)

    logger = lu.configure_logging(config=cfg, console=True, file_logging=True)

    assert any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)