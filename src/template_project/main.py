"""Entry point and composition root: the only place wiring the components together."""

import io
import os
import sys
from pathlib import Path
from typing import TextIO

from loguru import logger

from template_project.exceptions import TemplateProjectError
from template_project.logging_setup import configure_logging
from template_project.models.application import Application
from template_project.settings import get_environment, load_config

CONFIG_DIRECTORY = Path("config")


def main() -> int:
    """Load the configuration, configure logging and start the application.

    Returns:
        The process exit code: 0 on success, 1 on a configuration or validation error.
    """
    _use_utf8(sys.stderr)
    try:
        settings = load_config(
            get_environment(os.environ), CONFIG_DIRECTORY, os.environ
        )
        configure_logging(settings.logging, sys.stderr)
        logger.debug("Configuration loaded: {}", settings)
        application = Application(settings.app_name)
    except TemplateProjectError as error:
        logger.error("{}", error)
        return 1
    logger.info(
        '"{}" started in the "{}" environment',
        application.get_name(),
        settings.environment,
    )
    return 0


def _use_utf8(stream: TextIO) -> None:
    # Windows consoles default to a legacy code page that cannot encode every
    # character loguru emits, which would corrupt the JSON log lines.
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8")
