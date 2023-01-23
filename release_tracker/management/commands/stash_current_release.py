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
            logger.info("Creating new HerokuRelease object")
            release: HerokuRelease = HerokuRelease.objects.stash()
        except IntegrityError:  # noqa: F841
            logger.exception("Database error stashing current release.")
        except requests.HTTPError:  # noqa: F841
            logger.exception("HTTP error syncing current release.")
        except KeyError:  # noqa: F841
            logger.exception("Error stashing release - environment variable missing.")
        except Exception:  # noqa: F841
            logger.exception("Unknown error syncing current release.")
        else:
            logger.info("Created new release: %s", release)
