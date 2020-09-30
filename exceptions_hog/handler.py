from enum import Enum
from typing import Dict, Optional, Tuple, Union

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework import exceptions, status
from rest_framework.response import Response

from .exceptions import ProtectedObjectException
from .settings import api_settings
from .utils import ensure_string

DEFAULT_ERROR_DETAIL = _("A server error occurred.")


class ErrorTypes(Enum):
    """
    Defines default error types. Custom error types are still supported by
    setting the `exception_type` or `default_type` attributes on an instance exception.
    """

    authentication_error = "authentication_error"
    invalid_request = "invalid_request"
    server_error = "server_error"
    throttled_error = "throttled_error"
    validation_error = "validation_error"


@ensure_string
def _get_error_type(exc) -> Union[str, ErrorTypes]:
    """
    Gets the `type` for the exception. Default types are defined for base DRF exceptions.
    """
    if hasattr(exc, "exception_type"):
        # Attempt first to get the type defined for this specific instance
        return exc.exception_type
    elif hasattr(exc, "default_type"):
        # Use the exception class default type if available
        return exc.default_type

    # Default configuration for DRF exceptions
    if isinstance(exc, exceptions.AuthenticationFailed):
        return ErrorTypes.authentication_error
    elif isinstance(exc, exceptions.MethodNotAllowed):
        return ErrorTypes.invalid_request
    elif isinstance(exc, exceptions.NotAcceptable):
        return ErrorTypes.invalid_request
    elif isinstance(exc, exceptions.NotAuthenticated):
        return ErrorTypes.authentication_error
    elif isinstance(exc, exceptions.NotFound):
        return ErrorTypes.invalid_request
    elif isinstance(exc, exceptions.ParseError):
        return ErrorTypes.invalid_request
    elif isinstance(exc, exceptions.PermissionDenied):
        return ErrorTypes.authentication_error
    elif isinstance(exc, exceptions.Throttled):
        return ErrorTypes.throttled_error
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        return ErrorTypes.invalid_request
    elif isinstance(exc, exceptions.ValidationError):
        return ErrorTypes.validation_error

    # Couldn't determine type, default to generic error
    # TODO: Allow this default to be configured in settings
    return ErrorTypes.server_error


def _get_main_exception_and_code(exc) -> Tuple[str, Optional[str]]:
    """
    Finds the main exception when there are multiple exceptions (e.g. when two inputs are
    failing validation), and returns the exception key and the computed exception code.
    """

    def override_or_return(code: str) -> str:
        """
        Returns overridden code if needs to change or provided code.
        """
        if code == "invalid" and isinstance(exc, exceptions.ValidationError):
            # Special handling for validation errors. Use `invalid_input` instead
            # of `invalid` to provide more clarity.
            return "invalid_input"

        return code

    # Get base exception codes from DRF (if exception is DRF)
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()

        if isinstance(codes, str):
            # Only one exception, return
            return (codes, None)
        elif isinstance(codes, dict):
            key = next(iter(codes))  # Get first key
            code = codes[key] if isinstance(codes[key], str) else codes[key][0]
            return (override_or_return(code), key)
        elif isinstance(codes, list):
            return (override_or_return(str(codes[0])), None)

    # TODO: Allow this default to be configured in settings
    return ("error", None)


@ensure_string
def _get_detail(exc, exception_key: str = "") -> str:

    if hasattr(exc, "detail"):
        # Get exception details if explicitly set. We don't obtain exception information
        # from base Python exceptions to avoid leaking sensitive information.
        if isinstance(exc.detail, str):
            return str(
                exc.detail
            )  # We do str() to get the actual error string on ErrorDetail instances
        elif isinstance(exc.detail, dict):
            return str(
                exc.detail[exception_key][0]
                if isinstance(exc.detail[exception_key], str)
                else exc.detail[exception_key][0]
            )
        elif isinstance(exc.detail, list) and len(exc.detail) > 0:
            return exc.detail[0]

    return DEFAULT_ERROR_DETAIL


def _get_attr(exc: BaseException, exception_key: Optional[str] = "") -> Optional[str]:
    return exception_key if exception_key else None


def _get_http_status(exc) -> int:
    return (
        exc.status_code
        if hasattr(exc, "status_code")
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def exception_reporter(exc: BaseException, context: Optional[Dict] = None) -> None:
    """
    Logic for reporting an exception to any APMs.
    Example:
        if not isinstance(exc, exceptions.APIException):
            capture_exception(exc)
    """
    pass


def exception_handler(exc: BaseException, context: Optional[Dict] = None) -> Response:

    # Handle Django base exceptions
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, ProtectedError):
        exc = ProtectedObjectException(
            "",
            protected_objects=exc.protected_objects,
        )

    exception_code, exception_key = _get_main_exception_and_code(exc)

    api_settings.EXCEPTION_REPORTING(exc, context)

    return Response(
        dict(
            type=_get_error_type(exc),
            code=exception_code,
            detail=_get_detail(exc, exception_key),
            attr=_get_attr(exc, exception_key),
        ),
        status=_get_http_status(exc),
    )
