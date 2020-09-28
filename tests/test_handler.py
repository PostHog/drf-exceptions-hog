from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.http import Http404
from rest_framework import exceptions, status

from exceptions_hog.handler import exception_handler


# DRF exceptions
def test_not_acceptable_exception() -> None:
    response = exception_handler(exceptions.NotAcceptable())
    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.data == {
        "type": "invalid_request",
        "code": "not_acceptable",
        "detail": "Could not satisfy the request Accept header.",
        "attr": None,
    }


def test_unsupported_media_type_exception() -> None:
    response = exception_handler(exceptions.UnsupportedMediaType("application/xml"))
    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.data == {
        "type": "invalid_request",
        "code": "unsupported_media_type",
        "detail": 'Unsupported media type "application/xml" in request.',
        "attr": None,
    }


def test_throttled_exception() -> None:
    response = exception_handler(exceptions.Throttled(62))
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
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "type": "validation_error",
        "code": "ugly_input",  # Default code for `validation_error`
        "detail": "I did not like your input.",
        "attr": None,
    }


# Django & DRF exceptions


def test_not_found_exception(res_not_found) -> None:

    response = exception_handler(exceptions.NotFound())
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found

    # Test Django base exception too
    response = exception_handler(Http404())
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == res_not_found


def test_permission_denied_exception(res_permission_denied) -> None:

    response = exception_handler(exceptions.PermissionDenied())
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == res_permission_denied

    # Test Django base exception too
    response = exception_handler(PermissionDenied())
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == res_permission_denied


def test_protected_error() -> None:

    response = exception_handler(
        ProtectedError("Resource 'Hedgehog' has dependencies.", protected_objects=[1])
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.data == {
        "type": "invalid_request",
        "code": "protected_error",
        "detail": "Requested operation cannot be completed because"
        " a related object is protected.",
        "attr": None,
    }


# Python exceptions


def test_python_exceptions(res_server_error) -> None:

    # NotImplementedError
    response = exception_handler(
        NotImplementedError("This function is not implemented")
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error

    # AttributeError
    response = exception_handler(AttributeError())
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error

    # ImportError
    response = exception_handler(ImportError())
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error

    # TypeError
    response = exception_handler(TypeError())
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.data == res_server_error
