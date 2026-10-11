"""Domain model describing the running application."""

from template_project.exceptions import ValidationError


class Application:
    """The application, identified by its configured name."""

    def __init__(self, name: str) -> None:
        """Build the application.

        Args:
            name: Human-readable application name; must not be blank.

        Raises:
            ValidationError: If the name is empty or only whitespace.
        """
        if not name.strip():
            message = "The application name must not be empty."
            raise ValidationError(message)
        self._name = name

    def get_name(self) -> str:
        """Return the application name."""
        return self._name
