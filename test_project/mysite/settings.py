"""
This settings file is used ONLY to be able to run Django commands on test_project. Not
used during tests
"""

from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "#mk0y8q%rh!ieekh5h#39b@a99u3eg$93kc9oq#z1kpzvg+k2_"

DEBUG = True

ALLOWED_HOSTS: List[str] = []

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "test_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "mysite.urls"

WSGI_APPLICATION = "mysite.wsgi.application"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True
