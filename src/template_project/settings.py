"""Configuration loader: the only module reading config files and environment variables.

The active environment file (``<environment>.toml``) is merged over ``base.toml``,
then environment-variable overrides are applied, and the result is validated into
an immutable, typed ``Settings`` object.
"""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from template_project.exceptions import ConfigurationError

ENVIRONMENT_VARIABLE = "APP_ENV"
LOG_LEVEL_VARIABLE = "APP_LOG_LEVEL"
DEFAULT_ENVIRONMENT = "local"
BASE_FILE_NAME = "base.toml"
VALID_LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL")


@dataclass(frozen=True)
class LoggingSettings:
    """Logging configuration (loguru)."""

    level: str
    serialize: bool
    file_path: Path | None
    rotation: str
    retention: str


@dataclass(frozen=True)
class Settings:
    """Validated application configuration."""

    environment: str
    app_name: str
    logging: LoggingSettings


def get_environment(environ: Mapping[str, str]) -> str:
    """Resolve the active environment name.

    Args:
        environ: Environment variables (usually ``os.environ``).

    Returns:
        The value of ``APP_ENV``, or ``local`` when it is absent or blank.
    """
    return environ.get(ENVIRONMENT_VARIABLE, "").strip() or DEFAULT_ENVIRONMENT


def load_config(
    environment: str, config_dir: Path, environ: Mapping[str, str]
) -> Settings:
    """Load, merge and validate the configuration of an environment.

    Args:
        environment: Name of the environment file to merge over ``base.toml``.
        config_dir: Directory containing the configuration files.
        environ: Environment variables used for overrides (``APP_LOG_LEVEL``).

    Returns:
        The validated settings.

    Raises:
        ConfigurationError: If a file is missing or malformed, the environment is
            unknown, or a value is missing or invalid.
    """
    base = _read_toml(config_dir / BASE_FILE_NAME)
    environment_file = config_dir / f"{environment}.toml"
    if not environment_file.is_file():
        message = (
            f"Unknown environment '{environment}'. "
            f"Available environments: {', '.join(_available_environments(config_dir))}."
        )
        raise ConfigurationError(message)
    merged = _merge(base, _read_toml(environment_file))
    return _build_settings(environment, merged, environ)


def _available_environments(config_dir: Path) -> list[str]:
    return sorted(
        path.stem for path in config_dir.glob("*.toml") if path.name != BASE_FILE_NAME
    )


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        message = f"Configuration file not found: {path}"
        raise ConfigurationError(message)
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except tomllib.TOMLDecodeError as error:
        message = f"Invalid TOML in {path}: {error}"
        raise ConfigurationError(message) from error


def _merge(
    base: Mapping[str, object], override: Mapping[str, object]
) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _build_settings(
    environment: str, config: Mapping[str, object], environ: Mapping[str, str]
) -> Settings:
    app = _section(config, "app")
    return Settings(
        environment=environment,
        app_name=_value(app, "app", "name", str),
        logging=_build_logging_settings(_section(config, "logging"), environ),
    )


def _build_logging_settings(
    section: Mapping[str, object], environ: Mapping[str, str]
) -> LoggingSettings:
    level_override = environ.get(LOG_LEVEL_VARIABLE, "").strip()
    file_path = _value(section, "logging", "file_path", str)
    return LoggingSettings(
        level=_validate_log_level(
            level_override or _value(section, "logging", "level", str)
        ),
        serialize=_value(section, "logging", "serialize", bool),
        file_path=Path(file_path) if file_path else None,
        rotation=_value(section, "logging", "rotation", str),
        retention=_value(section, "logging", "retention", str),
    )


def _validate_log_level(level: str) -> str:
    normalized = level.upper()
    if normalized not in VALID_LOG_LEVELS:
        message = (
            f"Invalid log level '{level}'. Valid levels: {', '.join(VALID_LOG_LEVELS)}."
        )
        raise ConfigurationError(message)
    return normalized


def _section(config: Mapping[str, object], name: str) -> Mapping[str, object]:
    section = config.get(name)
    if not isinstance(section, dict):
        message = f"Missing configuration section [{name}]."
        raise ConfigurationError(message)
    return section


def _value[T](
    section: Mapping[str, object], section_name: str, key: str, expected_type: type[T]
) -> T:
    value = section.get(key)
    if not isinstance(value, expected_type):
        message = (
            f"Configuration key '{section_name}.{key}' is missing or is not "
            f"of type {expected_type.__name__}."
        )
        raise ConfigurationError(message)
    return value
