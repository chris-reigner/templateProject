import io
import sys
import unittest
from pathlib import Path
from unittest import mock

from template_project.exceptions import ConfigurationError
from template_project.main import main
from template_project.settings import LoggingSettings, Settings


def make_settings(app_name: str = "demo") -> Settings:
    return Settings(
        environment="local",
        app_name=app_name,
        logging=LoggingSettings(
            level="DEBUG",
            serialize=False,
            file_path=None,
            rotation="10 MB",
            retention="14 days",
        ),
    )


class TestMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests."""

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test: isolate every collaborator."""
        self.load_config = self._patch("template_project.main.load_config")
        self.configure_logging = self._patch("template_project.main.configure_logging")
        self.logger = self._patch("template_project.main.logger")

    def tearDown(self) -> None:
        """Execute at the ending of each test."""

    def _patch(self, target: str) -> mock.MagicMock:
        patcher = mock.patch(target)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_main_when_configuration_valid_returns_zero(self) -> None:
        # Given
        self.load_config.return_value = make_settings()

        # When
        exit_code = main()

        # Then
        self.assertEqual(exit_code, 0)

    def test_main_when_configuration_valid_reads_config_directory(self) -> None:
        # Given
        self.load_config.return_value = make_settings()

        # When
        main()

        # Then
        self.assertEqual(self.load_config.call_args.args[1], Path("config"))

    def test_main_when_configuration_valid_configures_logging_on_stderr(
        self,
    ) -> None:
        # Given
        settings = make_settings()
        self.load_config.return_value = settings

        # When
        main()

        # Then
        self.configure_logging.assert_called_once_with(settings.logging, sys.stderr)

    def test_main_when_configuration_valid_logs_startup(self) -> None:
        # Given
        self.load_config.return_value = make_settings()

        # When
        main()

        # Then
        self.logger.info.assert_called_once()
        self.assertIn("started", self.logger.info.call_args.args[0])

    def test_main_when_stderr_is_text_stream_switches_it_to_utf8(self) -> None:
        # Given
        self.load_config.return_value = make_settings()
        stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

        # When
        with mock.patch("sys.stderr", stderr):
            main()

        # Then
        self.assertEqual(stderr.encoding, "utf-8")

    def test_main_when_configuration_invalid_returns_one_and_logs_error(
        self,
    ) -> None:
        # Given
        self.load_config.side_effect = ConfigurationError("broken")

        # When
        exit_code = main()

        # Then
        self.assertEqual(exit_code, 1)
        self.logger.error.assert_called_once()

    def test_main_when_application_name_empty_returns_one(self) -> None:
        # Given
        self.load_config.return_value = make_settings(app_name="")

        # When
        exit_code = main()

        # Then
        self.assertEqual(exit_code, 1)
