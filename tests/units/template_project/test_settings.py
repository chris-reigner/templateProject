import tempfile
import unittest
from pathlib import Path

from template_project.exceptions import ConfigurationError
from template_project.settings import (
    LoggingSettings,
    Settings,
    get_environment,
    load_config,
)

BASE_TOML = """
[app]
name = "demo"

[logging]
level = "INFO"
serialize = false
file_path = ""
rotation = "10 MB"
retention = "14 days"
"""


class TestGetEnvironment(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests."""

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test."""

    def tearDown(self) -> None:
        """Execute at the ending of each test."""

    def test_get_environment_when_variable_absent_returns_local(self) -> None:
        # Given
        environ: dict[str, str] = {}

        # When
        environment = get_environment(environ)

        # Then
        self.assertEqual(environment, "local")

    def test_get_environment_when_variable_set_returns_its_value(self) -> None:
        # Given
        environ = {"APP_ENV": "docker_prod"}

        # When
        environment = get_environment(environ)

        # Then
        self.assertEqual(environment, "docker_prod")

    def test_get_environment_when_variable_blank_returns_local(self) -> None:
        # Given
        environ = {"APP_ENV": "  "}

        # When
        environment = get_environment(environ)

        # Then
        self.assertEqual(environment, "local")


class TestLoadConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests."""

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test: a fresh config directory."""
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.config_dir = Path(self._temporary_directory.name)
        self._write("base.toml", BASE_TOML)
        self._write("local.toml", '[logging]\nlevel = "DEBUG"\n')

    def tearDown(self) -> None:
        """Execute at the ending of each test."""
        self._temporary_directory.cleanup()

    def _write(self, file_name: str, content: str) -> None:
        (self.config_dir / file_name).write_text(content, encoding="utf-8")

    def test_load_config_when_files_valid_returns_merged_settings(self) -> None:
        # Given
        environ: dict[str, str] = {}

        # When
        settings = load_config("local", self.config_dir, environ)

        # Then
        expected = Settings(
            environment="local",
            app_name="demo",
            logging=LoggingSettings(
                level="DEBUG",
                serialize=False,
                file_path=None,
                rotation="10 MB",
                retention="14 days",
            ),
        )
        self.assertEqual(settings, expected)

    def test_load_config_when_file_path_set_returns_path(self) -> None:
        # Given
        self._write("local.toml", '[logging]\nfile_path = "logs/app.log"\n')

        # When
        settings = load_config("local", self.config_dir, {})

        # Then
        self.assertEqual(settings.logging.file_path, Path("logs/app.log"))

    def test_load_config_when_log_level_variable_set_overrides_file(self) -> None:
        # Given
        environ = {"APP_LOG_LEVEL": "error"}

        # When
        settings = load_config("local", self.config_dir, environ)

        # Then
        self.assertEqual(settings.logging.level, "ERROR")

    def test_load_config_when_base_file_missing_raises_configuration_error(
        self,
    ) -> None:
        # Given
        (self.config_dir / "base.toml").unlink()

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, "not found"):
            load_config("local", self.config_dir, {})

    def test_load_config_when_environment_unknown_raises_listing_available(
        self,
    ) -> None:
        # Given
        self._write("docker.toml", "")

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, r"'staging'.*docker, local"):
            load_config("staging", self.config_dir, {})

    def test_load_config_when_log_level_variable_invalid_raises_naming_it(
        self,
    ) -> None:
        # Given
        environ = {"APP_LOG_LEVEL": "VERBOSE"}

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, "'VERBOSE'"):
            load_config("local", self.config_dir, environ)

    def test_load_config_when_log_level_in_file_invalid_raises_naming_it(
        self,
    ) -> None:
        # Given
        self._write("local.toml", '[logging]\nlevel = "LOUD"\n')

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, "'LOUD'"):
            load_config("local", self.config_dir, {})

    def test_load_config_when_section_missing_raises_naming_it(self) -> None:
        # Given
        self._write("base.toml", '[logging]\nlevel = "INFO"\n')

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, r"\[app\]"):
            load_config("local", self.config_dir, {})

    def test_load_config_when_value_has_wrong_type_raises_naming_key(self) -> None:
        # Given
        self._write("local.toml", '[logging]\nserialize = "yes"\n')

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, r"logging\.serialize"):
            load_config("local", self.config_dir, {})

    def test_load_config_when_toml_malformed_raises_configuration_error(
        self,
    ) -> None:
        # Given
        self._write("local.toml", "[logging\n")

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, "Invalid TOML"):
            load_config("local", self.config_dir, {})
