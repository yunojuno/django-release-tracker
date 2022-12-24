from __future__ import annotations

import logging
from typing import Any

import dateparser
from django.db import models
from requests.exceptions import HTTPError

from . import github

logger = logging.getLogger(__name__)


def parse_description(description: str) -> tuple[str, str]:
    """Extract deployed commit from description."""
    action, message = description.split(" ", maxsplit=1)
    if action.lower() == "deploy":
        return str(HerokuRelease.ReleaseType.DEPLOYMENT), message
    if action.lower() == "set":
        return str(HerokuRelease.ReleaseType.ENV_VARS), ""
    if action.lower() in ("add", "remove"):
        return str(HerokuRelease.ReleaseType.ADD_ON), ""
    return str(HerokuRelease.ReleaseType.UNKNOWN), ""


class HerokuReleaseQuerySet(models.QuerySet):
    def deployments(self) -> HerokuReleaseQuerySet:
        return self.exclude(commit_hash="")


class HerokuReleaseManager(models.Manager):
    def create(self, **release_kwargs: Any) -> HerokuRelease:
        description = release_kwargs["description"]
        release_type, commit = parse_description(description)
        # may not appear if we are creating from the env vars
        slug = release_kwargs.get("slug", None)
        return super().create(
            created_at=dateparser.parse(release_kwargs["created_at"]),
            version=release_kwargs["version"],
            description=description,
            release_type=release_type,
            commit_hash=commit,
            status=release_kwargs["status"],
            slug_id=slug["id"] if slug else None,
            raw=release_kwargs,
        )


class HerokuRelease(models.Model):
    class ReleaseType(models.TextChoices):

        DEPLOYMENT = ("DEPLOYMENT", "Deployment")
        ADD_ON = ("ADD_ON", "Adjust addons")
        ENV_VARS = ("ENV_VARS", "Adjust env vars")
        UNKNOWN = ("UNKNOWN", "Unknown")

    version = models.PositiveIntegerField(unique=True)

    description = models.TextField(blank=True, default="")

    slug_id = models.UUIDField(blank=True, null=True)

    commit_hash = models.CharField(blank=True, max_length=40)

    created_at = models.DateTimeField()

    raw = models.JSONField(null=True, blank=True)

    status = models.CharField(max_length=100)

    parent = models.OneToOneField("self", null=True, on_delete=models.SET_NULL)

    release_note = models.TextField(blank=True, default="")

    release_type = models.CharField(
        max_length=10,
        choices=ReleaseType.choices,
        blank=True,
        default=ReleaseType.UNKNOWN,
    )

    objects = HerokuReleaseManager.from_queryset(HerokuReleaseQuerySet)()

    def __repr__(self) -> str:
        return f"<HerokuRelease version={self.version}>"

    def __str__(self) -> str:
        return f"Release v{self.version}"

    @property
    def base_head(self) -> str:
        """Form the base...head reference used to fetch diff from Github."""
        if not self.commit_hash:
            return ""
        if not self.parent:
            return ""
        if not self.parent.commit_hash:
            return ""
        return f"{self.parent.commit_hash}...{self.commit_hash}"

    def get_release_note(self) -> str:
        """Fetch release note from Github."""
        if not self.base_head:
            return ""
        try:
            return github.get_release_note(self.base_head)
        except HTTPError:
            logger.exception("Error retrieving release note")
        return ""

    def update_release_note(self) -> None:
        self.release_note = self.get_release_note()
        self.save(update_fields=["release_note"])

    def get_parent(self) -> HerokuRelease | None:
        """Return first deployment before this one."""
        return (
            HerokuRelease.objects.filter(version__lt=self.version)
            .deployments()
            .order_by("version")
            .last()
        )

    def update_parent(self) -> None:
        self.parent = self.get_parent()
        self.save(update_fields=["parent"])
