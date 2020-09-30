import base64
import random

import pytest
from django.contrib.auth import get_user_model


def pytest_configure():
    from django.conf import settings

    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "rest_framework",
            "test_project.test_app",
        ],
        ROOT_URLCONF="test_project.mysite.urls",
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        REST_FRAMEWORK={
            "EXCEPTION_HANDLER": "exceptions_hog.exception_handler",
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "rest_framework.authentication.BasicAuthentication",
            ],
        },
    )
    try:
        import django

        django.setup()
    except AttributeError:
        pass


@pytest.fixture
def test_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def auth_header() -> str:
    username: str = f"user_{random.randint(100,999)}"
    get_user_model().objects._create_user(
        username=username, email=f"{username}@example.com", password="password"
    )
    return f'Basic {base64.b64encode(f"{username}:password".encode()).decode()}'


@pytest.fixture
def res_not_found():
    """
    Default response for not found exception.
    """
    return {
        "type": "invalid_request",
        "code": "not_found",
        "detail": "Not found.",
        "attr": None,
    }


@pytest.fixture
def res_permission_denied():
    """
    Default response for permission denied exception.
    """
    return {
        "type": "authentication_error",
        "code": "permission_denied",
        "detail": "You do not have permission to perform this action.",
        "attr": None,
    }


@pytest.fixture
def res_server_error():
    """
    Default response for an unhandled exception (base internal server error).
    """
    return {
        "type": "server_error",
        "code": "error",
        "detail": "A server error occurred.",
        "attr": None,
    }
