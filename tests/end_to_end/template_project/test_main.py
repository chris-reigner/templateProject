"""Step definitions for main.feature: the installed application run as a subprocess."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

PROJECT_CONFIG_DIR = Path(__file__).parents[3] / "config"
LEVELS = ("TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL")
TEXT_LEVEL_PATTERN = re.compile(r"\|\s*([A-Z]+)\s*\|")
ANSI_COLOR_PATTERN = re.compile(r"\x1b\[[0-9;]*m")

scenarios("main.feature")


@pytest.fixture
def app_environ() -> dict[str, str]:
    environ = dict(os.environ)
    environ.pop("APP_ENV", None)
    environ.pop("APP_LOG_LEVEL", None)
    return environ


def log_levels(output: str) -> list[str]:
    levels = []
    for line in filter(str.strip, ANSI_COLOR_PATTERN.sub("", output).splitlines()):
        if line.startswith("{"):
            levels.append(json.loads(line)["record"]["level"]["name"])
        else:
            match = TEXT_LEVEL_PATTERN.search(line)
            if match:
                levels.append(match.group(1))
    return levels


@given(
    "a working directory containing a copy of the template configuration",
    target_fixture="working_dir",
)
def working_dir(tmp_path: Path) -> Path:
    shutil.copytree(PROJECT_CONFIG_DIR, tmp_path / "config")
    return tmp_path


@given("no environment is selected")
def no_environment(app_environ: dict[str, str]) -> None:
    app_environ.pop("APP_ENV", None)


@given(parsers.parse('the "{environment}" environment is selected'))
def environment_selected(app_environ: dict[str, str], environment: str) -> None:
    app_environ["APP_ENV"] = environment


@given(parsers.parse('the log level is forced to "{level}"'))
def log_level_forced(app_environ: dict[str, str], level: str) -> None:
    app_environ["APP_LOG_LEVEL"] = level


@given("the configuration directory is missing")
def configuration_missing(working_dir: Path) -> None:
    shutil.rmtree(working_dir / "config")


@given("the configured application name is empty")
def application_name_empty(working_dir: Path) -> None:
    base_file = working_dir / "config" / "base.toml"
    content = base_file.read_text(encoding="utf-8")
    base_file.write_text(
        content.replace('name = "template-project"', 'name = ""'), encoding="utf-8"
    )


@when("I start the application", target_fixture="result")
def start_application(
    working_dir: Path, app_environ: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("template-project")
    assert executable is not None, "Run the tests with `uv run` (script not on PATH)"
    return subprocess.run(
        [executable],
        cwd=working_dir,
        env=app_environ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )


@then("the application exits successfully")
def exits_successfully(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr


@then("the application exits with an error")
def exits_with_error(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode != 0


@then(
    parsers.parse(
        'the log announces that "{name}" started in the "{environment}" environment'
    )
)
def startup_announced(
    result: subprocess.CompletedProcess[str], name: str, environment: str
) -> None:
    assert f'"{name}" started in the "{environment}" environment' in result.stderr


@then("debug messages are shown in the log")
def debug_shown(result: subprocess.CompletedProcess[str]) -> None:
    assert "DEBUG" in log_levels(result.stderr)


@then(parsers.parse('messages below the "{level}" level are hidden from the log'))
def lower_levels_hidden(result: subprocess.CompletedProcess[str], level: str) -> None:
    threshold = LEVELS.index(level)
    assert all(LEVELS.index(found) >= threshold for found in log_levels(result.stderr))


@then("every log line is valid JSON")
def every_line_is_json(result: subprocess.CompletedProcess[str]) -> None:
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert lines
    for line in lines:
        json.loads(line)


@then(parsers.parse('the error message names the unknown environment "{environment}"'))
def unknown_environment_named(
    result: subprocess.CompletedProcess[str], environment: str
) -> None:
    assert f"Unknown environment '{environment}'" in result.stderr


@then("the error message lists the available environments")
def available_environments_listed(result: subprocess.CompletedProcess[str]) -> None:
    assert "Available environments: docker, docker_prod, local" in result.stderr


@then(parsers.parse('the error message names the invalid log level "{level}"'))
def invalid_level_named(result: subprocess.CompletedProcess[str], level: str) -> None:
    assert f"Invalid log level '{level}'" in result.stderr


@then("the error message says that a configuration file was not found")
def configuration_not_found(result: subprocess.CompletedProcess[str]) -> None:
    assert "Configuration file not found" in result.stderr


@then("the error message says that the application name must not be empty")
def application_name_must_not_be_empty(
    result: subprocess.CompletedProcess[str],
) -> None:
    assert "application name must not be empty" in result.stderr
