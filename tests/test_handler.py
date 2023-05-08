from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.exceptions import ErrorDetail, ValidationError

from exceptions_hog.handler import exception_handler
from exceptions_hog.settings import api_settings

# DRF exceptions


def test_not_acceptable_exception() -> None:
    response = exception_handler(exceptions.NotAcceptable())
    assert response is not None
    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.data == {
        "type": "invalid_request",
        "code": "not_acceptable",
        "detail": "Could not satisfy the request Accept header.",
        "attr": None,
    }


def test_unsupported_media_type_exception() -> None:
    response = exception_handler(exceptions.UnsupportedMediaType("application/xml"))
    assert response is not None
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.data == {
        "type": "invalid_request",
        "code": "unsupported_media_type",
        "detail": 'Unsupported media type "application/xml" in request.',
        "attr": None,
    }


def test_throttled_exception() -> None:
    response = exception_handler(exceptions.Throttled(62))
    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data == {
        "type": "throttled_error",
        "code": "throttled",
        "detail": "Request was throttled. Expected available in 62 seconds.",
        "attr": None,
    }


def test_validation_error() -> None:
    # Default code
    response = exception_handler(
        exceptions.ValidationError("I did not like your input.")
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "invalid_input",  # Default code for `validation_error`
        "detail": "I did not like your input.",
        "attr": None,
    }

    # Custom code
    response = exception_handler(
        exceptions.ValidationError("I did not like your input.", code="ugly_input")
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "ugly_input",  # Default code for `validation_error`
        "detail": "I did not like your input.",
        "attr": None,
    }


def test_validation_error_serializer_field() -> None:
    response = exception_handler(
        exceptions.ValidationError(
            {
                "phone_number": [
                    ErrorDetail(string="This field is required.", code="required")
                ]
            }
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "required",
        "detail": "This field is required.",
        "attr": "phone_number",
    }


def test_validation_error_with_simple_nested_serializer_field() -> None:
    response = exception_handler(
        exceptions.ValidationError(
            {
                "parent": {
                    "children_attr": [
                        ErrorDetail(string="This field is required.", code="required")
                    ],
                    "second_children_attr": [
                        ErrorDetail(
                            string="This field is also invalid.", code="invalid_too"
                        )
                    ],
                }
            }
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "required",
        "detail": "This field is required.",
        "attr": "parent__children_attr",
    }


def test_extra_attribute() -> None:
    class ExtraException(Exception):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
            self.extra = {"id": "123"}  # type: ignore

    response = exception_handler(ExtraException())
    assert response is not None
    assert response.data == {
        "type": "server_error",
        "code": "error",
        "detail": "A server error occurred.",
        "attr": None,
        "extra": {"id": "123"},
    }


def test_extra_attribute_with_multiple_exceptions(monkeypatch) -> None:
    monkeypatch.setattr(api_settings, "SUPPORT_MULTIPLE_EXCEPTIONS", True)

    class ExtraException(exceptions.ValidationError):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
            self.extra = {"id": "123"}  # type: ignore

    response = exception_handler(
        ExtraException(
            {
                "email": ErrorDetail(string="This field is required.", code="required"),
                "password": [
                    ErrorDetail(
                        string="This password is unsafe.",
                        code="unsafe_password",
                    )
                ],
            },
        )
    )
    assert response is not None
    assert response.data == {
        "type": "multiple",
        "code": "multiple",
        "detail": "Multiple exceptions ocurred. Please check list for details.",
        "attr": None,
        "extra": {"id": "123"},
        "list": [
            {
                "type": "validation_error",
                "code": "required",
                "detail": "This field is required.",
                "attr": "email",
            },
            {
                "type": "validation_error",
                "code": "unsafe_password",
                "detail": "This password is unsafe.",
                "attr": "password",
            },
        ],
    }


def test_validation_error_with_complex_nested_serializer_field() -> None:
    response = exception_handler(
        exceptions.ValidationError(
            {
                "parent": {
                    "l1_attr": {
                        "l2_attr": {
                            "l3_attr": ErrorDetail(
                                string="Focus on this error.", code="focus"
                            ),
                        },
                        "l2_attr_2": {
                            "l3_attr_2": [
                                ErrorDetail(
                                    string="This field is also invalid.",
                                    code="invalid_too",
                                )
                            ]
                        },
                    },
                    "l1_attr_2": [
                        ErrorDetail(
                            string="This field is also invalid.", code="invalid_too"
                        )
                    ],
                }
            }
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "focus",
        "detail": "Focus on this error.",
        "attr": "parent__l1_attr__l2_attr__l3_attr",
    }


def test_nested_serializer_field_with_special_characters() -> None:
    """
    Tests proper handling of the edge case of an attribute name using the same characters
    as the `NESTED_KEY_SEPARATOR`.
    """
    response = exception_handler(
        exceptions.ValidationError(
            {
                "my__special___attribute": {
                    "children_attr": [
                        ErrorDetail(string="This field is required.", code="required")
                    ],
                }
            }
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "required",
        "detail": "This field is required.",
        "attr": "my__special___attribute__children_attr",
    }


# Django & DRF exceptions


def test_throttled_exception_with_no_wait() -> None:
    throttled = exceptions.Throttled(wait=None)
    response = exception_handler(throttled)
    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data == {
        "attr": None,
        "code": "throttled",
        "detail": "Request was throttled.",
        "type": "throttled_error",
    }
    # older versions in the CI test matrix don't have headers on Response
    if getattr(response, "headers", None):
        assert "Retry-After" not in response.headers


def test_throttled_exception_with_wait() -> None:
    throttled = exceptions.Throttled(wait=100)
    response = exception_handler(throttled)
    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data == {
        "attr": None,
        "code": "throttled",
        "detail": "Request was throttled. Expected available in 100 seconds.",
        "type": "throttled_error",
    }
    # older versions in the CI test matrix don't have headers on Response
    if getattr(response, "headers", None):
        assert response.headers["Retry-After"] == "100"


def test_not_found_exception(res_not_found) -> None:
    response = exception_handler(exceptions.NotFound())
    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found

    # Test Django base exception too
    response = exception_handler(Http404())
    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found


def test_permission_denied_exception(res_permission_denied) -> None:
    response = exception_handler(exceptions.PermissionDenied())
    assert response is not None
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == res_permission_denied

    # Test Django base exception too
    response = exception_handler(PermissionDenied())
    assert response is not None
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == res_permission_denied


def test_protected_error() -> None:
    response = exception_handler(
        ProtectedError("Resource 'Hedgehog' has dependencies.", protected_objects=[1])
    )
    assert response is not None
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {
        "type": "invalid_request",
        "code": "protected_error",
        "detail": "Requested operation cannot be completed because"
        " a related object is protected.",
        "attr": None,
    }


def test_unique_together_exception() -> None:
    """
    Asserts special handling of __all__ exceptions.
    """
    response = exception_handler(
        ValidationError(
            {"__all__": ["User with this name and email already exists."]},
            code="unique_together",
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "unique_together",
        "detail": "User with this name and email already exists.",
        "attr": None,
    }


def test_non_field_errors_exception() -> None:
    """
    Asserts special handling of non_field_errors exceptions.
    https://www.django-rest-framework.org/api-guide/settings/#non_field_errors_key
    """
    response = exception_handler(
        ValidationError(
            {"non_field_errors": ["This form is invalid."]},
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "invalid_input",
        "detail": "This form is invalid.",
        "attr": None,
    }


def test_non_field_errors_exception_with_custom_key(settings) -> None:
    """
    Asserts special handling of non_field_errors exceptions.
    https://www.django-rest-framework.org/api-guide/settings/#non_field_errors_key
    """

    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "NON_FIELD_ERRORS_KEY": "my_custom_error_key",
    }

    response = exception_handler(
        ValidationError(
            {"my_custom_error_key": ["This form is invalid."]},
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "invalid_input",
        "detail": "This form is invalid.",
        "attr": None,
    }


# Python exceptions


def test_not_implemented_error(res_server_error) -> None:
    response = exception_handler(
        NotImplementedError("This function is not implemented")
    )
    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error


def test_attribute_error(res_server_error) -> None:
    response = exception_handler(AttributeError())
    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error


def test_import_error(res_server_error) -> None:
    response = exception_handler(ImportError())
    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error


def test_type_error(res_server_error) -> None:
    response = exception_handler(TypeError())
    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error


# Exception handling in DEBUG mode


def test_drf_exception_in_debug(settings) -> None:
    settings.DEBUG = True

    # Exception is handled as usual with the exceptions_hog handler
    response = exception_handler(exceptions.Throttled(28))
    assert response is not None
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data == {
        "type": "throttled_error",
        "code": "throttled",
        "detail": "Request was throttled. Expected available in 28 seconds.",
        "attr": None,
    }


def test_not_found_exception_in_debug(settings, res_not_found) -> None:
    settings.DEBUG = True

    # Same as normal, since exception is an APIException instance
    response = exception_handler(exceptions.NotFound())
    assert response is not None
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found

    # Test Django base 404 exception too
    response = exception_handler(Http404())
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found


@patch("django.core.signals.got_request_exception.send")
def test_python_exception_in_debug(mock_django_exception, settings) -> None:
    settings.DEBUG = True
    # Not handled, since not APIException instance
    response = exception_handler(TypeError())
    assert response is None
    mock_django_exception.assert_called_once_with(sender=None, request=None)


def test_python_exception_with_enabled_in_debug(
    res_server_error, settings, monkeypatch
) -> None:
    settings.DEBUG = True
    monkeypatch.setattr(api_settings, "ENABLE_IN_DEBUG", True)

    # Handled by exceptions_hog since `ENABLE_IN_DEBUG` is `True`
    response = exception_handler(TypeError())
    assert response is not None
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error


def test_list_response_validation_error_with_multiple_exceptions(
    monkeypatch,
) -> None:
    monkeypatch.setattr(api_settings, "SUPPORT_MULTIPLE_EXCEPTIONS", True)
    response = exception_handler(
        exceptions.ValidationError(
            {
                "email": ErrorDetail(string="This field is required.", code="required"),
                "password": [
                    ErrorDetail(
                        string="This password is unsafe.",
                        code="unsafe_password",
                    )
                ],
            },
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "multiple",
        "code": "multiple",
        "detail": "Multiple exceptions ocurred. Please check list for details.",
        "attr": None,
        "list": [
            {
                "type": "validation_error",
                "code": "required",
                "detail": "This field is required.",
                "attr": "email",
            },
            {
                "type": "validation_error",
                "code": "unsafe_password",
                "detail": "This password is unsafe.",
                "attr": "password",
            },
        ],
    }


def test_list_response_validation_error_with_complex_nested_serializer_field(
    monkeypatch,
) -> None:
    monkeypatch.setattr(api_settings, "SUPPORT_MULTIPLE_EXCEPTIONS", True)
    response = exception_handler(
        exceptions.ValidationError(
            {
                "parent": {
                    "l1_attr": {
                        "l2_attr": {
                            "l3_attr": ErrorDetail(
                                string="Focus on this error.", code="focus"
                            ),
                        },
                        "l2_attr_2": {
                            "l3_attr_2": [
                                ErrorDetail(
                                    string="This field is also invalid.",
                                    code="invalid_too",
                                )
                            ]
                        },
                    },
                    "l1_attr_2": [
                        ErrorDetail(
                            string="This field is also invalid.", code="invalid_too"
                        )
                    ],
                }
            }
        )
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "multiple",
        "code": "multiple",
        "detail": "Multiple exceptions ocurred. Please check list for details.",
        "attr": None,
        "list": [
            {
                "type": "validation_error",
                "code": "focus",
                "detail": "Focus on this error.",
                "attr": "parent__l1_attr__l2_attr__l3_attr",
            },
            {
                "type": "validation_error",
                "code": "invalid_too",
                "detail": "This field is also invalid.",
                "attr": "parent__l1_attr__l2_attr_2__l3_attr_2",
            },
            {
                "type": "validation_error",
                "code": "invalid_too",
                "detail": "This field is also invalid.",
                "attr": "parent__l1_attr_2",
            },
        ],
    }
