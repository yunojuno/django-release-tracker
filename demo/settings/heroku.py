import dj_database_url

from .base import *  # noqa: F401

DATABASES = {"default": dj_database_url.config(conn_max_age=600, ssl_require=True)}

ALLOWED_HOSTS = [".herokuapp.com"]
