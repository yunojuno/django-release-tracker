from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from django.db import IntegrityError

from release_tracker.heroku import crawl
from release_tracker.models import HerokuRelease


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> None:
        all_releases = crawl(max_count=10000)
        existing_releases = HerokuRelease.objects.all().values_list(
            "version", flat=True
        )
        new_releases = [
            r for r in all_releases if r["version"] not in existing_releases
        ]
        for release in new_releases:
            version = release["version"]
            self.stdout.write(f"Creating new release: {version}")
            hr = HerokuRelease(version=version)
            hr.parse_heroku_api_response(release)
            try:
                hr.save()
            except IntegrityError as ex:
                self.stderr.write(f"Error creating new release: {ex}")
                self.stderr.write(release)
