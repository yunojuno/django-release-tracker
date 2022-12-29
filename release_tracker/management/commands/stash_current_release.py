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

from release_tracker.models import HerokuRelease

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        try:
            self.stdout.write("Creating new HerokuRelease object")
            release: HerokuRelease = HerokuRelease.objects.auto_create()
            self.stdout.write(f"Syncing {release} with Github")
            release.sync()
            self.stdout.write("Updating release parent")
            release.update_parent()
        except IntegrityError as ex:
            self.stderr.write(f"Error stashing current release: {ex}")
        except requests.HTTPError as ex:
            self.stderr.write(f"Error pushing current release to github: {ex}")
        except Exception as ex:  # noqa: B902
            logger.exception("Error ")
            self.stderr.write(f"Error pushing current release to github: {ex}")
        else:
            self.stdout.write(f"Created new release: {release}")
