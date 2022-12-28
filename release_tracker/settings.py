import datetime
from os import getenv

import dateparser
from django.utils.functional import SimpleLazyObject, lazy

# Token used with the Platform API
HEROKU_API_TOKEN = getenv("HEROKU_API_TOKEN")

# Values set by dyno runtime metadata
def _release_version() -> int | None:
    if version := getenv("HEROKU_RELEASE_VERSION"):
        return int(version.strip("v"))


def _created_at() -> datetime.datetime | None:
    if created_at := getenv("HEROKU_RELEASE_CREATED_AT"):
        return dateparser.parse(created_at)
    return None


HEROKU_APP_ID = getenv("HEROKU_APP_ID")
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_RELEASE_CREATED_AT = lazy(_created_at)
HEROKU_RELEASE_VERSION = lazy(_release_version)
HEROKU_SLUG_COMMIT = getenv("HEROKU_SLUG_COMMIT")
HEROKU_SLUG_DESCRIPTION = getenv("HEROKU_SLUG_DESCRIPTION")


# Token used with the Github API
GITHUB_API_TOKEN = getenv("GITHUB_API_TOKEN")

# Username to whom the token belongs
GITHUB_USER_NAME = getenv("GITHUB_USER_NAME")

# Organisation to whom the source repo belongs
GITHUB_ORG_NAME = getenv("GITHUB_ORG_NAME")

# The source repo
GITHUB_REPO_NAME = getenv("GITHUB_REPO_NAME")
