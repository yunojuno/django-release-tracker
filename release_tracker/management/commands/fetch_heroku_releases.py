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

        all_releases = crawl(max_count=100)
        existing_releases = HerokuRelease.objects.all().values_list(
            "version", flat=True
        )
        new_releases = [
            r for r in all_releases if r["version"] not in existing_releases
        ]
        for release in new_releases:
            try:
                self.stdout.write("Creating new release")
                hr = HerokuRelease(version=release["version"])
                hr.parse_heroku_api_response(release)
                hr.save()
                hr.update_parent()
            except IntegrityError:
                self.stderr.write(f"Error creating new release:\n{release}")
