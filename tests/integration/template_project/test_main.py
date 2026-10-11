import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from loguru import logger

from template_project.main import main

PROJECT_CONFIG_DIR = Path(__file__).parents[3] / "config"


class TestMain(unittest.TestCase):
    """Junction: main wiring settings and logging with real configuration files."""

    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests."""

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test: a working dir with the config."""
        self._temporary_directory = tempfile.TemporaryDirectory()
        working_dir = Path(self._temporary_directory.name)
        shutil.copytree(PROJECT_CONFIG_DIR, working_dir / "config")
        self._previous_dir = Path.cwd()
        os.chdir(working_dir)
        self.stderr = io.StringIO()
        stderr_patcher = mock.patch("sys.stderr", self.stderr)
        stderr_patcher.start()
        self.addCleanup(stderr_patcher.stop)

    def tearDown(self) -> None:
        """Execute at the ending of each test: restore global state."""
        logger.remove()
        os.chdir(self._previous_dir)
        self._temporary_directory.cleanup()

    def _run(self, environ: dict[str, str]) -> int:
        with mock.patch.dict(os.environ, environ, clear=True):
            return main()

    def test_main_when_local_logs_debug_and_startup(self) -> None:
        # Given
        environ = {"APP_ENV": "local"}

        # When
        exit_code = self._run(environ)

        # Then
        output = self.stderr.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("DEBUG", output)
        self.assertIn('"template-project" started in the "local" environment', output)

    def test_main_when_docker_hides_debug_messages(self) -> None:
        # Given
        environ = {"APP_ENV": "docker"}

        # When
        exit_code = self._run(environ)

        # Then
        output = self.stderr.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertNotIn("DEBUG", output)
        self.assertIn("started", output)

    def test_main_when_log_level_forced_overrides_environment(self) -> None:
        # Given
        environ = {"APP_ENV": "docker_prod", "APP_LOG_LEVEL": "DEBUG"}

        # When
        exit_code = self._run(environ)

        # Then
        self.assertEqual(exit_code, 0)
        self.assertIn('"level"', self.stderr.getvalue())
