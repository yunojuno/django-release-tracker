from .base import *  # noqa: F401

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "demo.db"}}

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = ("whitenoise.runserver_nostatic",) + INSTALLED_APPS
