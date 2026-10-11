"""Exception hierarchy of the package: every error raised on purpose derives from it."""


class TemplateProjectError(Exception):
    """Base class of every error raised by the package."""


class ConfigurationError(TemplateProjectError):
    """Raised when the configuration is missing, malformed or invalid."""


class ValidationError(TemplateProjectError):
    """Raised when a domain object is built with invalid values."""
