from typing import Dict

from django.conf import settings
from rest_framework.settings import APISettings

USER_SETTINGS: Dict = getattr(settings, "EXCEPTIONS_HOG", None)

DEFAULTS: Dict = {
    "EXCEPTION_REPORTING": "exceptions_hog.handler.exception_reporter",
}

# List of settings that may be in string import notation.
IMPORT_STRINGS = ("EXCEPTION_REPORTING",)

api_settings: APISettings = APISettings(USER_SETTINGS, DEFAULTS, IMPORT_STRINGS)
