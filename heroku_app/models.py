from __future__ import annotations

import logging
from typing import Any

import dateparser
from django.db import models
from requests.exceptions import HTTPError

from . import github

logger = logging.getLogger(__name__)


def get_release_type(description: str) -> str:
    """Extract release type from description."""
    if description.lower().startswith("deploy"):
        return str(HerokuRelease.ReleaseType.DEPLOYMENT)
    if description.lower().endswith("config vars"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith("update"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith(("add", "attach", "detach")):
        return str(HerokuRelease.ReleaseType.ADD_ON)
    return str(HerokuRelease.ReleaseType.UNKNOWN)


def get_commit_hash(description: str) -> str:
    """Extract commit hash from release description."""
    action, commit_hash = description.split(" ", maxsplit=1)
    if action.lower() == "deploy":
        return commit_hash
    return ""


def get_release_parent(version: int) -> HerokuRelease | None:
    """Fetch the most recent deployment."""
    return (
        HerokuRelease.objects.deployments()
        .filter(version__lt=version)
        .order_by("version")
        .last()
    )


class HerokuReleaseQuerySet(models.QuerySet):
    def deployments(self) -> HerokuReleaseQuerySet:
        return self.filter(release_type=HerokuRelease.ReleaseType.DEPLOYMENT)


class HerokuReleaseManager(models.Manager):
    def create(
        self,
        description: str,
        version: int,
        created_at: str,
        status: str,
        slug: dict | None = None,
        **release_kwargs: Any,
    ) -> HerokuRelease:
        """Create a new release and set the parent property if a deployment."""
        commit = get_commit_hash(description)
        release_type = get_release_type(description)
        parent = (
            get_release_parent(version)
            if release_type == HerokuRelease.ReleaseType.DEPLOYMENT
            else None
        )
        return super().create(
            created_at=dateparser.parse(created_at),
            version=version,
            description=description,
            release_type=release_type,
            commit_hash=commit,
            parent=parent,
            status=status,
            slug_id=slug["id"] if slug else None,
            raw=release_kwargs,
        )


class HerokuRelease(models.Model):
    class ReleaseType(models.TextChoices):

        DEPLOYMENT = ("DEPLOYMENT", "Code deployment")
        ADD_ON = ("ADD_ON", "Add-ons")
        ENV_VARS = ("ENV_VARS", "Config vars")
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
    def is_deployment(self) -> bool:
        return self.release_type == HerokuRelease.ReleaseType.DEPLOYMENT

    @property
    def tag_name(self) -> str:
        if self.is_deployment:
            return f"v{self.version}"
        return ""

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
