import io
import json
import tempfile
import unittest
from pathlib import Path

from loguru import logger

from template_project.logging_setup import configure_logging
from template_project.settings import LoggingSettings


def make_settings(
    level: str = "INFO", *, serialize: bool = False, file_path: Path | None = None
) -> LoggingSettings:
    return LoggingSettings(
        level=level,
        serialize=serialize,
        file_path=file_path,
        rotation="10 MB",
        retention="14 days",
    )


class TestConfigureLogging(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests."""

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test: a fresh in-memory sink."""
        self.sink = io.StringIO()

    def tearDown(self) -> None:
        """Execute at the ending of each test: release every loguru handler."""
        logger.remove()

    def test_configure_logging_when_level_info_hides_debug_messages(self) -> None:
        # Given
        configure_logging(make_settings("INFO"), self.sink)

        # When
        logger.debug("hidden message")
        logger.info("visible message")

        # Then
        output = self.sink.getvalue()
        self.assertNotIn("hidden message", output)
        self.assertIn("visible message", output)

    def test_configure_logging_when_serialize_writes_json_lines(self) -> None:
        # Given
        configure_logging(make_settings("INFO", serialize=True), self.sink)

        # When
        logger.info("structured message")

        # Then
        record = json.loads(self.sink.getvalue().splitlines()[0])
        self.assertEqual(record["record"]["message"], "structured message")

    def test_configure_logging_when_called_twice_does_not_duplicate_output(
        self,
    ) -> None:
        # Given
        configure_logging(make_settings("INFO"), self.sink)
        configure_logging(make_settings("INFO"), self.sink)

        # When
        logger.info("single message")

        # Then
        self.assertEqual(self.sink.getvalue().count("single message"), 1)

    def test_configure_logging_when_file_path_set_also_writes_to_file(self) -> None:
        # Given
        with tempfile.TemporaryDirectory() as directory:
            log_file = Path(directory) / "app.log"
            configure_logging(make_settings("INFO", file_path=log_file), self.sink)

            # When
            logger.info("persisted message")
            logger.remove()

            # Then
            self.assertIn("persisted message", log_file.read_text(encoding="utf-8"))
