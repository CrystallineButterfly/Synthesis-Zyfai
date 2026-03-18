"""Custom exceptions for local runtime failures."""


class ConfigurationError(RuntimeError):
    """Raised when required runtime configuration is missing."""


class PartnerExecutionError(RuntimeError):
    """Raised when a partner call fails."""
