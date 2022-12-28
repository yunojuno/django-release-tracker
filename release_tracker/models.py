from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import dateparser
import requests
from django.db import IntegrityError, models
from django.utils.timezone import now as tz_now
from requests.exceptions import HTTPError

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
    if description.lower().startswith("deploy"):
        return str(HerokuRelease.ReleaseType.DEPLOYMENT)
    if description.lower().endswith("config vars"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith("update"):
        return str(HerokuRelease.ReleaseType.ENV_VARS)
    if description.lower().startswith(("add", "attach", "detach")):
        return str(HerokuRelease.ReleaseType.ADD_ON)
    if description.lower().endswith("add-on"):
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
    def auto_create(self) -> HerokuRelease:
        """Create a new release from the current running dyno."""
        try:
            release: HerokuRelease = self.create(
                version=int(HEROKU_RELEASE_VERSION),
                created_at=HEROKU_RELEASE_CREATED_AT,
                commit_hash=HEROKU_SLUG_COMMIT,
                description=HEROKU_SLUG_DESCRIPTION,
                release_type=get_release_type(HEROKU_SLUG_DESCRIPTION),
                status="success",
            )
        except IntegrityError:
            logger.exception("Error auto-creating a new release")
        else:
            return release

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
        commit = get_commit_hash(description)
        release_type = get_release_type(description)
        # release_note = ""
        parent = (
            get_release_parent(version)
            if release_type == HerokuRelease.ReleaseType.DEPLOYMENT
            else None
        )
        # if release_type == HerokuRelease.ReleaseType.DEPLOYMENT and slug:
        #     slug.update(get_slug(slug["id"]))
        #     release_note = slug["commit_description"]
        #     release_kwargs["slug_size"] = slug["size"]
        #     release_kwargs["slug"] = slug
        #     # override short hash with the full-length hash as Github
        #     # needs this for some API operations.
        #     commit = slug["commit"]
        return super().create(
            created_at=dateparser.parse(created_at),
            version=version,
            description=description,
            # release_note=release_note,
            release_type=release_type,
            commit_hash=commit,
            parent=parent,
            status=status,
            slug_id=slug["id"] if slug else None,
            heroku_release=release_kwargs,
        )


class HerokuRelease(models.Model):
    class ReleaseType(models.TextChoices):

        DEPLOYMENT = ("DEPLOYMENT", "Code deployment")
        ADD_ON = ("ADD_ON", "Add-ons")
        ENV_VARS = ("ENV_VARS", "Config vars")
        UNKNOWN = ("UNKNOWN", "Unknown")

    version = models.PositiveIntegerField(unique=True)

    description = models.TextField(
        blank=True, default="", help_text="Heroku release description (auto-generated)."
    )

    slug_id = models.UUIDField(blank=True, null=True)

    commit_hash = models.CharField(blank=True, max_length=40)

    created_at = models.DateTimeField(
        blank=True, null=True, help_text="When the release was created by Heroku."
    )

    pulled_at = models.DateTimeField(
        blank=True, null=True, help_text="When the release data was pulled from Heroku"
    )

    pushed_at = models.DateTimeField(
        blank=True, null=True, help_text="When the release data was pushed to Github."
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

    status = models.CharField(max_length=100)

    parent = models.OneToOneField(
        "self",
        null=True,
        on_delete=models.SET_NULL,
        help_text="The previous release - used to generate changelog.",
    )

    release_note = models.TextField(
        blank=True,
        default="",
        help_text="The release note pulled from the Heroku platform API.",
    )

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
        return f"{self.parent.commit_hash[:6]}...{self.commit_hash[:6]}"

    def get_parent(self) -> HerokuRelease | None:
        """Return first deployment before this one."""
        if not self.is_deployment:
            return None
        return (
            HerokuRelease.objects.filter(version__lt=self.version)
            .deployments()
            .order_by("version")
            .last()
        )

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

    @property
    def github_release_data(self) -> dict:
        """Format the data required for the release API call."""
        return {
            "tag_name": self.tag_name,
            "commit_hash": self.commit_hash,
            "body": self.release_note,
            "generate_release_notes": True,
        }

    def pull(self) -> None:
        """
        Pull most recent release data from Heroku.

        This method pulls in the latest release data from the Heroku
        API, and then pulls the related Slug info if appropriate. It
        updates the commit and release note from the Slug. It updates
        the heroku_release attribute with the full Slug data.

        Fields that are updated by this method:

            "heroku_release", "slug_id", "commit_hash", "release_note"

        """
        if not self.version:
            raise Exception("Missing Heroku release version.")
        self.heroku_release = heroku.get_release(self.version)
        self.created_at = dateparser.parse(self.heroku_release["created_at"])
        if not (release_slug := self.heroku_release["slug"]):
            self.save(update_fields=["heroku_release"])
            return
        self.slug_id = release_slug["id"]
        slug = heroku.get_slug(self.slug_id)
        self.heroku_release.update(slug)
        self.commit_hash = slug["commit"]
        self.release_note = slug["commit_description"]
        self.status = self.heroku_release["status"]
        self.pulled_at = tz_now()
        self.save(
            update_fields=[
                "pulled_at",
                "heroku_release",
                "slug_id",
                "commit_hash",
                "release_note",
            ]
        )

    def push(self) -> bool:
        """
        Push release data to Github.

        Calls the Github create release API, using the current Heroku
        release data - tag_name, commit_hash, release_note. It passes
        the generate_release_notes param so that Github will create the
        release from all commits since the last (Github) release.

        Raises AttributeError if the tag_name is not set as without this
        it's impossible to create a release.

        Logs and re-raises HTTPError if the API request failed.

        """
        if not self.tag_name:
            raise AttributeError(f"{self} is missing tag_name property.")
        try:
            release = github.create_release(**self.github_release_data)
        except requests.HTTPError as ex:
            logger.error("Error pushing release to github")
            logger.error(github.format_api_errors(ex))
            raise
        else:
            self.github_release = release
            self.pushed_at = tz_now()
            self.save(update_fields=["pushed_at", "github_release"])
        return True

    def sync(self) -> None:
        """
        Pull from Heroku and push to Github.

        The minimum requirement here is a version number.

        """
        self.pull()
        self.push()
