"""Custom exception hierarchy for Dashy.

Provides typed exceptions with RFC 9457 error codes for structured error
responses. All Dashy-specific exceptions inherit from ``DashyError``.
"""


class DashyError(Exception):
    """Base exception for all Dashy errors.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error identifier (RFC 9457 ``type`` suffix).
        status_code: HTTP status code to return.
        detail: Optional extra context for debugging.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "dashy-error",
        status_code: int = 500,
        detail: str | None = None,
    ) -> None:
        """Initialize a Dashy error.

        Args:
            message: Human-readable error description.
            error_code: Machine-readable error identifier (RFC 9457 ``type`` suffix).
            status_code: HTTP status code to return.
            detail: Optional extra context for debugging.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail


class WeatherApiError(DashyError):
    """Raised when the OpenWeatherMap API returns an error or is unreachable."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a WeatherApiError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="weather-api-error",
            status_code=502,
            detail=detail,
        )


class WeatherConfigError(DashyError):
    """Raised when weather configuration is invalid or missing."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a WeatherConfigError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="weather-config-error",
            status_code=500,
            detail=detail,
        )


class CalendarApiError(DashyError):
    """Raised when the Google Calendar API returns an error or is unreachable."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a CalendarApiError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="calendar-api-error",
            status_code=502,
            detail=detail,
        )


class CalendarConfigError(DashyError):
    """Raised when calendar configuration is invalid or missing."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a CalendarConfigError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="calendar-config-error",
            status_code=500,
            detail=detail,
        )


class ConfigError(DashyError):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a ConfigError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="config-error",
            status_code=500,
            detail=detail,
        )


class ValidationError(DashyError):
    """Raised when request input fails validation."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        """Initialize a ValidationError.

        Args:
            message: Human-readable error description.
            detail: Optional extra context for debugging.
        """
        super().__init__(
            message,
            error_code="validation-error",
            status_code=422,
            detail=detail,
        )
