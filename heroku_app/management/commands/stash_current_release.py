"""
Cerate a new HerokuRelease from the current running environment.

The following env vars are set on a release if the runtime-dyno-metadata
labs feature is enabled: `heroku labs:enable runtime-dyno-metadata`

    HEROKU_APP_ID=
    HEROKU_APP_NAME=
    HEROKU_DYNO_ID=
    HEROKU_RELEASE_CREATED_AT=
    HEROKU_RELEASE_LOG_STREAM=
    HEROKU_RELEASE_STREAM_URL=
    HEROKU_RELEASE_VERSION=
    HEROKU_SLUG_COMMIT=
    HEROKU_SLUG_DESCRIPTION=

"""
import logging
from os import getenv
from typing import Any

from django.core.management import BaseCommand
from django.db import IntegrityError

from heroku_app.models import HerokuRelease

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        created_at = getenv("HEROKU_RELEASE_CREATED_AT")
        commit_hash = getenv("HEROKU_SLUG_COMMIT")
        version = int(getenv("HEROKU_RELEASE_VERSION", "v0")[1:])
        description = getenv("HEROKU_SLUG_DESCRIPTION")
        try:
            release = HerokuRelease.objects.create(
                version=version,
                created_at=created_at,
                commit_hash=commit_hash,
                description=description,
                status="success",
            )
        except IntegrityError:
            logger.exception("Error stashing current release")
        else:
            self.stdout.write(f"Created new release: {release}")
