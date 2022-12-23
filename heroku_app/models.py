from __future__ import annotations

import re
from typing import Any

import dateparser
from django.db import models


def parse_description(description: str) -> str:
    """Extract deployed commit from description."""
    regex = r"Deploy (?P<commit>\w*)"
    if match := re.match(regex, description, re.RegexFlag.IGNORECASE):
        return match["commit"]
    return ""


class HerokuReleaseManager(models.Manager):
    def create(self, **release_kwargs: Any) -> HerokuRelease:
        description = release_kwargs["description"]
        slug = release_kwargs["slug"]
        return super().create(
            created_at=dateparser.parse(release_kwargs["created_at"]),
            version=release_kwargs["version"],
            description=description,
            commit_hash=parse_description(description),
            status=release_kwargs["status"],
            slug_id=slug["id"] if slug else None,
            raw=release_kwargs,
        )


class HerokuRelease(models.Model):

    version = models.PositiveIntegerField(unique=True)

    description = models.TextField()

    slug_id = models.UUIDField(blank=True, null=True)

    commit_hash = models.CharField(blank=True, max_length=40)

    created_at = models.DateTimeField()

    raw = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=100)

    objects = HerokuReleaseManager()

    def __repr__(self) -> str:
        return f"<HerokuRelease version={self.version}>"

    def __str__(self) -> str:
        return f"Release v{self.version}"
