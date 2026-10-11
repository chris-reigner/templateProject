import unittest
from pathlib import Path

from template_project.exceptions import ConfigurationError
from template_project.settings import load_config

PROJECT_CONFIG_DIR = Path(__file__).parents[3] / "config"


class TestLoadConfig(unittest.TestCase):
    """Junction: the loader against the real configuration files of the project."""

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

    def test_load_config_when_local_returns_debug_text_logs(self) -> None:
        # Given
        environment = "local"

        # When
        settings = load_config(environment, PROJECT_CONFIG_DIR, {})

        # Then
        self.assertEqual(settings.app_name, "template-project")
        self.assertEqual(settings.logging.level, "DEBUG")
        self.assertFalse(settings.logging.serialize)

    def test_load_config_when_docker_returns_info_level(self) -> None:
        # Given
        environment = "docker"

        # When
        settings = load_config(environment, PROJECT_CONFIG_DIR, {})

        # Then
        self.assertEqual(settings.logging.level, "INFO")

    def test_load_config_when_docker_prod_returns_warning_json_logs(self) -> None:
        # Given
        environment = "docker_prod"

        # When
        settings = load_config(environment, PROJECT_CONFIG_DIR, {})

        # Then
        self.assertEqual(settings.logging.level, "WARNING")
        self.assertTrue(settings.logging.serialize)

    def test_load_config_when_environment_unknown_lists_project_environments(
        self,
    ) -> None:
        # Given
        environment = "staging"

        # When / Then
        with self.assertRaisesRegex(ConfigurationError, "docker, docker_prod, local"):
            load_config(environment, PROJECT_CONFIG_DIR, {})
