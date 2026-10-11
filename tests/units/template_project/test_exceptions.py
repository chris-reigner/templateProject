import unittest

from template_project.exceptions import (
    ConfigurationError,
    TemplateProjectError,
    ValidationError,
)


class TestTemplateProjectError(unittest.TestCase):
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

    def test_init_when_message_given_is_an_exception_with_that_message(self) -> None:
        # Given
        message = "something went wrong"

        # When
        error = TemplateProjectError(message)

        # Then
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), message)


class TestConfigurationError(unittest.TestCase):
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

    def test_init_when_raised_is_caught_as_template_project_error(self) -> None:
        # Given
        message = "bad configuration"

        # When / Then
        with self.assertRaises(TemplateProjectError):
            raise ConfigurationError(message)


class TestValidationError(unittest.TestCase):
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

    def test_init_when_raised_is_caught_as_template_project_error(self) -> None:
        # Given
        message = "invalid value"

        # When / Then
        with self.assertRaises(TemplateProjectError):
            raise ValidationError(message)
