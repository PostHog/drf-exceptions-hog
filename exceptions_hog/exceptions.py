from typing import ClassVar, Optional

from django.db.models import ProtectedError
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import status


class ExceptionClass:
    code: Optional[str] = None
    default_code: ClassVar[Optional[str]] = None

    def get_codes(self) -> Optional[str]:
        if self.code:
            return self.code
        elif self.default_code:
            return self.default_code
        return None


class ProtectedObjectException(ExceptionClass, ProtectedError):
    default_type: ClassVar[str] = "invalid_request"
    default_code: ClassVar[str] = "protected_error"
    status_code: ClassVar[int] = status.HTTP_409_CONFLICT
    default_detail: ClassVar[str] = _(
        "Requested operation cannot be completed because a related object is protected."
    )

    def __init__(self, msg, protected_objects):
        self.detail = force_str(msg or self.default_detail)
        super().__init__(msg, protected_objects)
