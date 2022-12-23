from typing import Any, Optional

from django.core.management import BaseCommand

from heroku_app.api import crawl
from heroku_app.models import HerokuRelease


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:

        releases = crawl(max_count=10000)
        for release in releases:
            HerokuRelease.objects.create(**release)
