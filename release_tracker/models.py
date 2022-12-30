from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import dateparser
from django.db import models
from django.utils.timezone import now as tz_now

from . import github, heroku
from .settings import (
    HEROKU_RELEASE_CREATED_AT,
    HEROKU_RELEASE_VERSION,
    HEROKU_SLUG_COMMIT,
    HEROKU_SLUG_DESCRIPTION,
)

logger = logging.getLogger(__name__)


def get_release_type(description: str) -> str:
    """Extract release type from description."""
    if not description:
        raise ValueError("Missing description.")
    if description.lower().startswith("deploy"):
        return str(HerokuRelease.ReleaseType.DEPLOYMENT)
    if description.lower().startswith("promote"):
        return str(HerokuRelease.ReleaseType.PROMOTION)
    if description.lower().startswith("rollback"):
        return str(HerokuRelease.ReleaseType.ROLLBACK)
    if description.lower().endswith("config vars"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith("update"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith(("add", "attach", "detach")):
        return str(HerokuRelease.ReleaseType.ADD_ON)
    if description.lower().endswith("add-on"):
        return str(HerokuRelease.ReleaseType.ADD_ON)
    return str(HerokuRelease.ReleaseType.OTHER)


def get_commit(description: str) -> str:
    """Extract commit hash from release description."""
    action, commit = description.split(" ", maxsplit=1)
    if action.lower() == "deploy":
        return commit
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
        return self.filter(release_type__in=[
            HerokuRelease.ReleaseType.DEPLOYMENT,
            HerokuRelease.ReleaseType.PROMOTION,
        ])


class HerokuReleaseManager(models.Manager):
    def auto_create(self) -> HerokuRelease:
        """Create a new release from the current running dyno."""
        if not HEROKU_RELEASE_VERSION:
            raise Exception("Missing HEROKU_RELEASE_VERSION env var.")
        if not HEROKU_RELEASE_CREATED_AT:
            raise Exception("Missing HEROKU_RELEASE_CREATED_AT env var.")
        if not HEROKU_SLUG_COMMIT:
            raise Exception("Missing HEROKU_SLUG_COMMIT env var.")
        if not HEROKU_SLUG_DESCRIPTION:
            raise Exception("Missing HEROKU_SLUG_DESCRIPTION env var.")
        return self.create(
            version=HEROKU_RELEASE_VERSION,
            created_at=HEROKU_RELEASE_CREATED_AT,
            commit=HEROKU_SLUG_COMMIT,
            commit_description=HEROKU_SLUG_DESCRIPTION,
            release_type=get_release_type(HEROKU_SLUG_DESCRIPTION),
        )

    def create_from_api(
        self,
        description: str,
        version: int,
        created_at: str,
        status: str,
        slug: dict | None = None,
        **release_kwargs: Any,
    ) -> HerokuRelease:
        """Create a new release from the Heroku API response."""
        commit = get_commit(description)
        commit_description = ""
        release_type = get_release_type(description)
        parent = (
            get_release_parent(version)
            if release_type == HerokuRelease.ReleaseType.DEPLOYMENT
            else None
        )
        if release_type == HerokuRelease.ReleaseType.DEPLOYMENT and slug:
            slug.update(heroku.get_slug(slug["id"]))
            commit_description = slug["commit_description"]
            # override short hash with the full-length hash as Github
            # needs this for some API operations.
            commit = slug["commit"]
        return super().create(
            created_at=dateparser.parse(created_at),
            version=version,
            description=description,
            commit=commit,
            commit_description=commit_description,
            release_type=release_type,
            parent=parent,
            status=status,
            slug_id=slug["id"] if slug else None,
            heroku_release=release_kwargs,
        )


class HerokuRelease(models.Model):
    class ReleaseType(models.TextChoices):

        DEPLOYMENT = ("DEPLOYMENT", "Slug deployment")
        PROMOTION = ("PROMOTION", "Pipeline promotion")
        ROLLBACK = ("ROLLBACK", "Release rollback")
        ADD_ON = ("ADD_ON", "Add-ons")
        ENV_VARS = ("ENV_VARS", "Config vars")
        OTHER = ("OTHER", "Other (misc.)")

    version = models.PositiveIntegerField(unique=True)

    description = models.TextField(
        blank=True,
        default="",
        help_text="Heroku release description (auto-generated).",
    )

    slug_id = models.UUIDField(
        blank=True,
        null=True,
        help_text="The slug id comes from the platform API or the config vars.",
    )

    commit = models.CharField(
        max_length=40,
        blank=True,
        default="",
        help_text="Commit hash - pulled from Heroku API (/slugs), pushed to Github.",
    )

    commit_description = models.TextField(
        blank=True,
        default="",
        help_text="The commit description pulled from the Heroku platform API.",
    )

    status = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Release status pulled from Heroku platform API.",
    )

    created_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the release was created by Heroku (from API).",
    )

    pulled_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the release data was pulled from Heroku",
    )

    pushed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the release data was pushed to Github.",
    )

    heroku_release = models.JSONField(
        null=True,
        blank=True,
        help_text="Release as represented by the Heroku platform API.",
    )

    github_release = models.JSONField(
        null=True,
        blank=True,
        help_text="Release as represented by the Github REST API.",
    )

    parent = models.OneToOneField(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        help_text="The previous release - used to generate changelog.",
        related_name="child",
    )

    release_type = models.CharField(
        max_length=10,
        choices=ReleaseType.choices,
        blank=True,
        default=ReleaseType.OTHER,
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
    def is_promotion(self) -> bool:
        return self.release_type == HerokuRelease.ReleaseType.PROMOTION

    @property
    def short_commit(self) -> str:
        return self.commit[:6] if self.commit else get_commit(self.description)

    @property
    def tag_name(self) -> str:
        if self.is_deployment or self.is_promotion:
            return f"v{self.version}"
        return ""

    @property
    def is_synced(self) -> bool | None:
        return self.pulled_at and self.pushed_at

    @property
    def base_head(self) -> str:
        """Form the base...head reference used to fetch diff from Github."""
        if not self.commit:
            return ""
        if not self.parent:
            return ""
        if not self.parent.commit:
            return ""
        return f"{self.parent.short_commit}...{self.short_commit}"

    def get_parent(self) -> HerokuRelease | None:
        """Return first deployment before this one."""
        if self.is_deployment or self.is_promotion:
            return get_release_parent(self.version)
        return None

    def update_parent(self) -> None:
        self.parent = self.get_parent()
        self.save(update_fields=["parent"])

    @property
    def heroku_release_id(self) -> UUID | None:
        if not self.heroku_release:
            return None
        return UUID(self.heroku_release["id"])

    @property
    def github_release_id(self) -> int | None:
        if not self.github_release:
            return None
        return int(self.github_release["id"])

    @property
    def github_release_url(self) -> str | None:
        if not self.github_release:
            return None
        return self.github_release["html_url"]

    def parse_heroku_api_response(self, data: dict) -> None:
        """Parse API release data into properties."""
        logger.debug("Parsing Heroku API response")
        self.status = data["status"]
        self.description = data["description"]
        self.release_type = get_release_type(self.description)
        self.created_at = dateparser.parse(data["created_at"])
        if slug := data["slug"]:
            self.slug_id = slug.get("id", None)
            self.commit = slug.get("commit", "")
            self.commit_description = slug.get("commit_description", "")
        self.heroku_release = data

    def pull(self) -> None:
        """
        Pull most recent release data from Heroku.

        This method pulls in the latest release data from the Heroku
        API, and then pulls the related Slug info if appropriate. It
        updates the commit and release note from the Slug. It updates
        the heroku_release attribute with the full Slug data.

        """
        if not self.version:
            raise AttributeError("Missing version number.")
        logger.debug("Pulling release %s from Heroku", self.version)
        release = heroku.get_release(self.version)
        if release.get("slug", None):
            slug = heroku.get_slug(release["slug"]["id"])
            release["slug"].update(slug)
        self.parse_heroku_api_response(release)
        self.pulled_at = tz_now()
        self.save()

    def push(self) -> None:
        """
        Push release data to Github.

        This is a pessimistic insert - makes two API calls, the first is
        a GET to fetch a matching release. If it does not exist, a
        second POST request is made to create a new release.

        Raises AttributeError if the tag_name is not set as without this
        it's impossible to create a release.

        """
        if not self.tag_name:
            raise AttributeError(f"{self} is missing tag_name property.")
        if not self.commit:
            raise AttributeError(f"{self} is missing commit property.")
        # if the parent has not been pushed then autogenerating the
        # release note will pull in every commit in history...
        generate_release_notes = bool(self.parent and self.parent.pushed_at)
        self.github_release = github.get_release(
            self.tag_name
        ) or github.create_release(
            tag_name=self.tag_name,
            commit=self.commit,
            body=self.commit_description,
            generate_release_notes=generate_release_notes,
        )
        self.pushed_at = tz_now()
        self.save()

    def sync(self) -> None:
        """
        Pull from Heroku and push to Github.

        The minimum requirement here is a version number.

        """
        self.pull()
        self.push()

    def delete_from_github(self) -> None:
        """Delete Github release and reset metadata to reflect this."""
        if not self.github_release_id:
            return
        github.delete_release(self.github_release_id)
        self.github_release = None
        self.pushed_at = None
        self.save()
