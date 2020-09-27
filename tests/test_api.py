import pytest
from rest_framework import status


@pytest.mark.django_db
class TestAPI:
    def test_api_not_found(self, test_client, res_not_found) -> None:
        response = test_client.get("/hedgehogs/49402")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data == res_not_found

    def test_api_permission_denied(self, test_client, auth_header) -> None:
        response = test_client.get("/denied", HTTP_AUTHORIZATION=auth_header)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {
            "type": "authentication_error",
            "code": "permission_denied",
            "detail": "You are not allowed to do this!",
            "attr": None,
        }

    def test_api_authentication_failed(self, test_client) -> None:

        # Unauthenticated
        response = test_client.get("/denied")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data == {
            "type": "authentication_error",
            "code": "not_authenticated",
            "detail": "Authentication credentials were not provided.",
            "attr": None,
        }

        # Authentication failed
        response = test_client.get("/denied", HTTP_AUTHORIZATION="Basic dTpw")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data == {
            "type": "authentication_error",
            "code": "authentication_failed",
            "detail": "Invalid username/password.",
            "attr": None,
        }

    def test_api_method_not_allowed(self, test_client) -> None:
        response = test_client.post("/hedgehogs/34")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data == {
            "type": "invalid_request",
            "code": "method_not_allowed",
            "detail": 'Method "POST" not allowed.',
            "attr": None,
        }

    def test_api_validation_error(self, test_client) -> None:
        response = test_client.post(
            "/hedgehogs", {"name": "Sonic", "color": "blue", "age": "invalid"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            "type": "validation_error",
            "code": "invalid_input",
            "detail": "A valid integer is required.",
            "attr": "age",
        }

    def test_api_multiple_validation_errors(self, test_client) -> None:

        # This would raise an exception for missing name AND invalid age
        # but only the main exception will be returned
        response = test_client.post("/hedgehogs", {"color": "blue", "age": "invalid"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {
            "type": "validation_error",
            "code": "required",
            "detail": "This field is required.",
            "attr": "name",
        }

    def test_unhandled_server_error(self, test_client, res_server_error) -> None:
        """
        Tests generic unhandled Python exceptions. Note we assert that a generic
        error message is returned in these cases to avoid leaking sensitive information.
        """

        # Assertion error
        response = test_client.post("/exception", {"type": "assertion_error"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data == res_server_error

        # Arithmetic error
        response = test_client.post("/exception", {"type": "arithmetic_error"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data == res_server_error

        # Key error
        response = test_client.post("/exception", {"type": "key_error"})
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data == res_server_error

        # Exception
        response = test_client.post("/exception")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data == res_server_error
