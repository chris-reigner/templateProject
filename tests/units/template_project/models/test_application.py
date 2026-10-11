import unittest

from template_project.exceptions import ValidationError
from template_project.models.application import Application


class TestApplication(unittest.TestCase):
    application: Application

    @classmethod
    def setUpClass(cls) -> None:
        """Execute before all tests.

        Shared, read-only fixture: an application built with a valid name.
        """
        cls.application = Application("template-project")

    @classmethod
    def tearDownClass(cls) -> None:
        """Execute at the ending of the class."""

    def setUp(self) -> None:
        """Execute at the beginning of each test."""

    def tearDown(self) -> None:
        """Execute at the ending of each test."""

    def test_get_name_when_application_initialized_returns_given_name(self) -> None:
        # Given
        application = self.application

        # When
        name = application.get_name()

        # Then
        self.assertEqual(name, "template-project")

    def test_init_when_name_is_empty_raises_validation_error(self) -> None:
        # Given
        empty_name = ""

        # When / Then
        with self.assertRaisesRegex(ValidationError, "must not be empty"):
            Application(empty_name)

    def test_init_when_name_is_only_whitespace_raises_validation_error(self) -> None:
        # Given
        blank_name = "   "

        # When / Then
        with self.assertRaisesRegex(ValidationError, "must not be empty"):
            Application(blank_name)
