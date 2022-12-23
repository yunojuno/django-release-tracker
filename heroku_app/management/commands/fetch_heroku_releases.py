from typing import Any, Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from heroku_app.api import crawl
from heroku_app.models import HerokuRelease


class Command(BaseCommand):

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)


    def handle(self, *args: Any, **options: Any) -> None:

        releases = crawl(max_count=10000)
        for release in releases:
            HerokuRelease.objects.create(**release)
