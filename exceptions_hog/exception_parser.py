import abc
from typing import Any, Dict

from rest_framework import exceptions
from rest_framework.exceptions import ErrorDetail

from .exceptions import ProtectedObjectException


class ExceptionParser:
    @abc.abstractmethod
    def match(self, exception: BaseException) -> bool:
        pass

    @abc.abstractmethod
    def parse(self, exception: Any) -> Dict[str, ErrorDetail]:
        pass


class ValidationErrorParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return isinstance(exception, exceptions.ValidationError)

    def parse(self, exception: exceptions.ValidationError) -> Dict[str, ErrorDetail]:
        detail = exception.detail
        return {"": detail} if isinstance(detail, list) else detail


class ProtectedObjectExceptionParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return isinstance(exception, ProtectedObjectException)

    def parse(self, exception: ProtectedObjectException) -> Dict[str, ErrorDetail]:
        return {"": ErrorDetail(string=exception.detail, code="protected_error")}


class APIExceptionParser(ExceptionParser):
    def match(self, exception: BaseException) -> bool:
        return hasattr(exception, "detail") and isinstance(
            getattr(exception, "detail"), ErrorDetail
        )

    def parse(self, exception: exceptions.APIException) -> Dict[str, ErrorDetail]:
        return {"": exception.detail}
