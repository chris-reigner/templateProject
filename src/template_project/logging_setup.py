"""Loguru configuration, applied once at the entry point."""

from typing import TextIO

from loguru import logger

from template_project.settings import LoggingSettings


def configure_logging(settings: LoggingSettings, sink: TextIO) -> None:
    """Replace every loguru handler with the configured ones.

    Args:
        settings: Master level, JSON output and optional log file.
        sink: Stream receiving the logs (usually ``sys.stderr``).
    """
    logger.remove()
    logger.add(sink, level=settings.level, serialize=settings.serialize)
    if settings.file_path is not None:
        logger.add(
            settings.file_path,
            level=settings.level,
            serialize=settings.serialize,
            rotation=settings.rotation,
            retention=settings.retention,
            encoding="utf-8",
        )
