from typing import Any

from django.core.management import BaseCommand
from django.core.management.base import CommandParser
from django.db import IntegrityError

from heroku_app.api import crawl
from heroku_app.models import HerokuRelease


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
        HerokuRelease.objects.all().values_list("version", flat=True)
        for release in new_releases:
            try:
                HerokuRelease.objects.create(**release)
            except IntegrityError:
                self.stderr.write(f"Error creating new release:\n{release}")
