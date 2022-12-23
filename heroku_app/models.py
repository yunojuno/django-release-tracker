from __future__ import annotations

import logging
import re
from typing import Any

import dateparser
from django.db import models
from requests.exceptions import HTTPError

from . import github

logger = logging.getLogger(__name__)


def parse_description(description: str) -> str:
    """Extract deployed commit from description."""
    regex = r"Deploy (?P<commit>\w*)"
    if match := re.match(regex, description, re.RegexFlag.IGNORECASE):
        return match["commit"]
    return ""


class HerokuReleaseQuerySet(models.QuerySet):
    def deployments(self) -> HerokuReleaseQuerySet:
        return self.exclude(commit_hash="")

    def has_parent(self) -> HerokuReleaseQuerySet:
        return self.exclude(parent__isnull=True)

    def has_no_parent(self) -> HerokuReleaseQuerySet:
        return self.filter(parent__isnull=True)


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

    def get_parent(self, release: HerokuRelease) -> HerokuRelease | None:
        return (
            self.get_queryset()
            .deployments()
            .filter(version__lt=release.version)
            .order_by("version")
            .last()
        )

    def backfill_missing_parents(self) -> None:
        deployment = (
            self.get_queryset()
            .deployments()
            .has_not_parent()
            .order_by("version")
            .last()
        )
        while deployment:
            if parent := self.get_parent(deployment):
                deployment.parent = parent
                deployment.save(update_fields=["parent"])
            deployment = parent

    def backfill_missing_release_notes(self) -> None:
        for release in (
            self.get_queryset().deployments().has_parent().filter(release_note="")
        ):
            release.set_release_note()


class HerokuRelease(models.Model):

    version = models.PositiveIntegerField(unique=True)

    description = models.TextField(blank=True, default="")

    slug_id = models.UUIDField(blank=True, null=True)

    commit_hash = models.CharField(blank=True, max_length=40)

    created_at = models.DateTimeField()

    raw = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=100)

    parent = models.OneToOneField("self", null=True, on_delete=models.SET_NULL)

    release_note = models.TextField(blank=True, default="")

    objects = HerokuReleaseManager.from_queryset(HerokuReleaseQuerySet)()

    def __repr__(self) -> str:
        return f"<HerokuRelease version={self.version}>"

    def __str__(self) -> str:
        return f"Release v{self.version}"

    @property
    def base_head(self) -> str:
        if not self.commit_hash:
            return ""
        if not self.parent:
            return ""
        if not self.parent.commit_hash:
            return ""
        return f"{self.parent.commit_hash}...{self.commit_hash}"

    def get_release_note(self) -> str:
        try:
            return github.get_release_note(self.base_head)
        except HTTPError:
            logger.exception("Error retrieving release note")
            return ""

    def set_release_note(self) -> None:
        self.release_note = self.get_release_note()
        self.save(update_fields=["release_note"])
