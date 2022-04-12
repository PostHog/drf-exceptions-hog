from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.signals import got_request_exception
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.exceptions import ErrorDetail
from rest_framework.response import Response
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.views import set_rollback

from .exception_parser import (
    APIExceptionParser,
    ProtectedObjectExceptionParser,
    ValidationErrorParser,
)
from .exceptions import ProtectedObjectException
from .settings import api_settings
from .utils import ensure_string

DEFAULT_ERROR_DETAIL = ErrorDetail("A server error occurred.", code="error")

DEFAULT_EXCEPTION_PARSERS = (
    ValidationErrorParser(),
    ProtectedObjectExceptionParser(),
    APIExceptionParser(),
)

all_exception_parsers = (
    *DEFAULT_EXCEPTION_PARSERS,
    *[parser() for parser in api_settings.EXTRA_EXCEPTION_PARSERS],
)


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
    multiple_exceptions = "multiple"


class ExceptionKeyContentType(Enum):
    single = "single"
    flat = "flat"
    nested = "nested"
    many_flat = "many_flat"
    many_nested = "many_nested"
    index = "index"


@dataclass
class ExceptionKey:
    value: Union[str, int]
    details_type: ExceptionKeyContentType


class NormalizedException:
    def __init__(self, keys: List[ExceptionKey], error_details: List[ErrorDetail]):
        self.keys = keys
        self.error_details = error_details

    @property
    def attr(self) -> Optional[str]:
        """
        Returns the offending attribute name. Handles special case
            of __all__ (used for instance in UniqueTogetherValidator) to return `None`.
        """

        def override_or_return(key: Optional[str]) -> Optional[str]:
            """
            Returns overridden code if needs to change or provided code.
            """
            if key in ["__all__", drf_api_settings.NON_FIELD_ERRORS_KEY]:
                return None

            return key if key else None

        return override_or_return(
            api_settings.NESTED_KEY_SEPARATOR.join(self.key_values)
        )

    @property
    def code(self) -> str:
        """Always returns the first error code"""
        code = self.error_details[0].code
        if code == "invalid":
            # Special handling for validation errors. Use `invalid_input` instead
            # of `invalid` to provide more clarity.
            return "invalid_input"
        return self.error_details[0].code

    @property
    def detail(self) -> str:
        """Always returns the first error detail"""
        return str(self.error_details[0])

    @property
    def key_values(self) -> List[str]:
        # We do str(key.value) to get the actual error string on the ErrorDetail instance
        return [str(key.value) for key in self.keys]


def exception_handler(
    exc: BaseException, context: Optional[Dict] = None
) -> Optional[Response]:
    # Special handling for Django base exceptions first
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    elif isinstance(exc, ProtectedError):
        exc = ProtectedObjectException(
            "",
            protected_objects=exc.protected_objects,
        )

    if (
        getattr(settings, "DEBUG", False)
        and not api_settings.ENABLE_IN_DEBUG
        and not isinstance(exc, exceptions.APIException)
    ):
        # By default don't handle non-DRF errors in DEBUG mode, i.e. Django will treat
        # unhandled exceptions regularly (very evident yellow error page)

        # NOTE: to make sure we get exception tracebacks in test responses, we need
        # to make sure this signal is called. The django test client uses this to
        # pull out the exception traceback.
        #
        # See https://github.com/django/django/blob/3.2.9/django/test/client.py#L712
        got_request_exception.send(
            sender=None,
            request=context["request"] if context and "request" in context else None,
        )
        return None

    api_settings.EXCEPTION_REPORTING(exc, context)
    set_rollback()

    error_details = _get_error_details(exc)
    normalized_exceptions = _get_normalized_exceptions(error_details)

    if api_settings.SUPPORT_MULTIPLE_EXCEPTIONS and len(normalized_exceptions) > 1:
        response = dict(
            type=ErrorTypes.multiple_exceptions.value,
            code=ErrorTypes.multiple_exceptions.value,
            detail="Multiple exceptions occurred. Please check list for details.",
            attr=None,
            list=[
                _assemble_error(exc, error, False) for error in normalized_exceptions
            ],
            **_get_extra(exc)
        )
    else:
        response = _assemble_error(exc, normalized_exceptions[0])

    return Response(response, status=_get_http_status(exc))


def exception_reporter(exc: BaseException, context: Optional[Dict] = None) -> None:
    """
    Logic for reporting an exception to any APMs.
    Example:
        if not isinstance(exc, exceptions.APIException):
            capture_exception(exc)
    """
    pass


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
    return ErrorTypes.server_error


def _get_normalized_exceptions(
    error_details: Optional[Dict],
    parent_keys: List[ExceptionKey] = None,
) -> List[NormalizedException]:
    """
    Returns a normalized one-level list of exception attributes and codes. Used to
    standardize multiple exceptions and complex nested exceptions.

    Example:

    Input => {
        "update": [
             ErrorDetail(
                string="This field is required.",
                code="required",
            ),
        ]
        "form": {
             "email": [
                ErrorDetail(
                    string="This field is required.",
                    code="required",
                ),
            ],
            "password": [
                ErrorDetail(
                    string="This password is unsafe.",
                    code="unsafe_password",
                )
            ],
        }
    }

    Output => [
         NormalizedException(
             "keys": [
                ExceptionKey(value="update", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    string="This field is required.",
                    code="required",
                ),
            ]
         ),
         NormalizedException(
             "keys": [
                ExceptionKey(value="form", type="nested")
                ExceptionKey(value="email", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    string="This field is required.",
                    code="required",
                ),
            ]
         ),
         NormalizedException(
             "keys": [
                ExceptionKey(value="form", type="nested")
                ExceptionKey(value="password", type="flat")
             ],
             "error_details": [
                ErrorDetail(
                    string="This password is unsafe.",
                    code="unsafe_password",
                )
            ]
         ),
    ]
    """

    if error_details is None:
        return [NormalizedException(keys=[], error_details=[DEFAULT_ERROR_DETAIL])]

    items: List[NormalizedException] = []

    def get_details_type(
        _details: Union[List, Dict, ErrorDetail]
    ) -> ExceptionKeyContentType:
        if isinstance(_details, list):
            if isinstance(_details[0], list):
                # Example: [[ErrorDetail(string="Error", code="error")]]
                return ExceptionKeyContentType.many_flat
            elif isinstance(_details[0], dict):
                # Example: {"error": ErrorDetail(string="Error", code="error"})
                return ExceptionKeyContentType.many_nested
            else:
                # Example: [ErrorDetail(string="Error", code="error")]
                return ExceptionKeyContentType.flat
        elif isinstance(_details, dict):
            # Example: [{"error": [ErrorDetail(string="Error", code="error")]}]
            return ExceptionKeyContentType.nested
        # Example: ErrorDetail(string="Error", code="error")
        return ExceptionKeyContentType.single

    def normalize_single_details(
        _keys: List[ExceptionKey], _details: ErrorDetail
    ) -> List[NormalizedException]:
        return [NormalizedException(keys=_keys, error_details=[_details])]

    def normalize_flat_details(
        _keys: List[ExceptionKey], _details: List[ErrorDetail]
    ) -> List[NormalizedException]:
        return [NormalizedException(keys=_keys, error_details=_details)]

    def normalize_nested_details(
        _keys: List[ExceptionKey], _details: Dict
    ) -> List[NormalizedException]:
        return _get_normalized_exceptions(
            error_details=_details.copy(), parent_keys=_keys
        )

    def normalize_many_flat_details(
        _keys: List[ExceptionKey], _details: List[List[ErrorDetail]]
    ) -> List[NormalizedException]:
        return [
            NormalizedException(
                keys=[
                    *_keys,
                    ExceptionKey(
                        value=index, details_type=ExceptionKeyContentType.index
                    ),
                ],
                error_details=detail,
            )
            for index, detail in enumerate(_details)
        ]

    def normalize_many_nested_details(
        _keys: List[ExceptionKey], _details: List[Dict]
    ) -> List[NormalizedException]:
        result: List[NormalizedException] = []
        for index, nested_error_details in enumerate(_details):
            result.extend(
                _get_normalized_exceptions(
                    error_details=nested_error_details.copy(),
                    parent_keys=[
                        *_keys,
                        ExceptionKey(
                            value=index,
                            details_type=ExceptionKeyContentType.index,
                        ),
                    ],
                )
            )
        return result

    switcher = {
        ExceptionKeyContentType.single: normalize_single_details,
        ExceptionKeyContentType.flat: normalize_flat_details,
        ExceptionKeyContentType.nested: normalize_nested_details,
        ExceptionKeyContentType.many_flat: normalize_many_flat_details,
        ExceptionKeyContentType.many_nested: normalize_many_nested_details,
    }

    for key, details in error_details.items():
        parsed_key = ExceptionKey(value=key, details_type=get_details_type(details))
        parsed_keys: List[ExceptionKey] = (parent_keys or []) + [parsed_key]
        normalizer = switcher[parsed_key.details_type]
        items.extend(normalizer(parsed_keys, details))

    return items


def _get_http_status(exc) -> int:
    return (
        exc.status_code
        if hasattr(exc, "status_code")
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def _get_extra(exc: BaseException) -> Dict:
    return {"extra": getattr(exc, "extra")} if hasattr(exc, "extra") else {}


def _assemble_error(
    exc: BaseException, normalized_exc: NormalizedException, with_extra=True
) -> Dict:
    return dict(
        type=_get_error_type(exc),
        code=normalized_exc.code,
        detail=normalized_exc.detail,
        attr=normalized_exc.attr,
        **(_get_extra(exc) if with_extra else {})
    )


def _get_error_details(exc: Any) -> Optional[Dict]:
    for parser in all_exception_parsers:
        if parser.match(exc):
            return parser.parse(exc)
    return None
