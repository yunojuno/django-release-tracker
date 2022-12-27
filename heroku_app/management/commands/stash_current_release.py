"""
Create a new HerokuRelease from the current running environment.

The following env vars are set on a release if the runtime-dyno-metadata
labs feature is enabled: `heroku labs:enable runtime-dyno-metadata`

"""
import logging
from typing import Any

import requests
from django.core.management import BaseCommand
from django.db import IntegrityError

from heroku_app.models import HerokuRelease

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        try:
            release: HerokuRelease = HerokuRelease.objects.auto_create()
            release.sync()
            release.update_parent()
        except IntegrityError as ex:
            self.stderr.write(f"Error stashing current release: {ex}")
        except requests.HTTPError as ex:
            self.stderr.write(f"Error pushing current release to github: {ex}")
        else:
            self.stdout.write(f"Created new release: {release}")
