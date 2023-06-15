from __future__ import annotations

import logging
from collections import namedtuple
from os import environ
from typing import Any, Callable
from uuid import UUID

import dateparser
from django.conf import settings
from django.db import models
from django.template.defaultfilters import date as datefmt
from django.utils.timezone import now as tz_now

from . import github, heroku
from .settings import GITHUB_SYNC_ENABLED

logger = logging.getLogger(__name__)
# tuple used to store results of batch operations
BatchResults = namedtuple("BatchResults", ["succeeded", "failed", "ignored"])

# yes, it's hardcoded - can be extracted to setting if required.
MAX_BATCH_COUNT = 100


def get_release_type(description: str) -> str:  # noqa: C901
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
        HerokuRelease.deployments.filter(version__lt=version).order_by("version").last()
    )


class HerokuReleaseQuerySet(models.QuerySet):
    def _batch(
        self, method: str, skip_if: Callable[[HerokuRelease], bool], max_count: int
    ) -> BatchResults:
        succeeded = failed = ignored = 0
        # force ordering as most operations require that releases are
        # processed in chronological order.
        for obj in self.order_by("version")[:max_count]:
            if skip_if(obj):
                logger.exception("Skipping object %r", obj)
                ignored += 1
                continue
            try:
                getattr(obj, method)()
            except Exception:  # noqa: B902
                failed += 1
                logger.exception("Error calling '%s' on object %r", method, obj)
            else:
                succeeded += 1
        return BatchResults(succeeded, failed, ignored)

    def set_parent_releases(self, max_count: int = MAX_BATCH_COUNT) -> BatchResults:
        skip_if = lambda obj: not obj.is_deployment  # noqa
        return self._batch("update_parent", skip_if, max_count)

    def pull(
        self, force: bool = False, max_count: int = MAX_BATCH_COUNT
    ) -> BatchResults:
        """
        Pull most recent release data from Heroku.

        By default this will ignore releases that have already been
        pulled. Use the `force` kwarg to override this.

        """
        skip_if = lambda obj: not force and obj.pulled_at  # noqa
        return self._batch("pull", skip_if, max_count)

    def push(
        self, force: bool = False, max_count: int = MAX_BATCH_COUNT
    ) -> BatchResults:
        """
        Push release data to Github.

        By default this will ignore releases that have already been
        pushed. Use the `force` kwarg to override this.

        """
        skip_if = lambda obj: not force and obj.pushed_at  # noqa
        return self._batch("push", skip_if, max_count)

    def sync(
        self, force: bool = False, max_count: int = MAX_BATCH_COUNT
    ) -> BatchResults:
        """
        Sync releases - pull from Heroku and push to Github.

        By default this will ignore releases that have already been
        pulled and pushed. Use the `force` kwarg to override this.

        """
        skip_if = lambda obj: not force and (obj.pulled_at and obj.pushed_at)  # noqa
        return self._batch("sync", skip_if, max_count)

    def update_github_release(self, max_count: int = MAX_BATCH_COUNT) -> BatchResults:
        """Update the release notes on Github."""
        skip_if = lambda obj: not obj.is_deployment  # noqa
        return self._batch("sync", skip_if, max_count)


class HerokuReleaseManager(models.Manager):
    def stash(self) -> HerokuRelease:
        """Create a new skeleton release from the environment variables."""
        # the following are set by Heroku if the Dyno Metadata feature
        # is installed. https://devcenter.heroku.com/articles/dyno-metadata
        created_at = dateparser.parse(environ["HEROKU_RELEASE_CREATED_AT"])
        version = int(environ["HEROKU_RELEASE_VERSION"].strip("v"))
        commit = environ["HEROKU_SLUG_COMMIT"]
        commit_description = environ["HEROKU_SLUG_DESCRIPTION"]
        release = self.create(
            version=version,
            created_at=created_at,
            commit=commit,
            commit_description=commit_description,
            release_type=get_release_type(commit_description),
        )
        release.update_parent()
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


class HerokuDeploymentReleaseManager(HerokuReleaseManager):
    def get_queryset(self) -> models.QuerySet[HerokuRelease]:
        return (
            super()
            .get_queryset()
            .filter(
                release_type__in=[
                    HerokuRelease.ReleaseType.DEPLOYMENT,
                    HerokuRelease.ReleaseType.PROMOTION,
                ]
            )
        )


class HerokuRelease(models.Model):
    class ReleaseType(models.TextChoices):
        DEPLOYMENT = ("DEPLOYMENT", "Slug deployment")
        PROMOTION = ("PROMOTION", "Pipeline promotion")
        ROLLBACK = ("ROLLBACK", "Release rollback")
        ADD_ON = ("ADD_ON", "Add-ons")
        ENV_VARS = ("ENV_VARS", "Config vars")
        OTHER = ("OTHER", "Other (misc.)")

    # these two release types both represent a new code deployment
    deployment_release_types = [ReleaseType.DEPLOYMENT, ReleaseType.PROMOTION]

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
    deployments = HerokuDeploymentReleaseManager.from_queryset(HerokuReleaseQuerySet)()

    def __repr__(self) -> str:
        return f"<HerokuRelease version={self.version}>"

    def __str__(self) -> str:
        return f"Release v{self.version}"

    @property
    def is_deployment(self) -> bool:
        """Return True if this represents a new code deployment."""
        return self.release_type in self.deployment_release_types

    @property
    def short_commit(self) -> str:
        return self.commit[:8] if self.commit else get_commit(self.description)

    @property
    def tag_name(self) -> str:
        if self.is_deployment:
            return f"v{self.version}"
        return ""

    @property
    def created_at_display(self) -> str:
        return datefmt(self.created_at, settings.DATETIME_FORMAT)

    @property
    def release_name(self) -> str:
        if self.is_deployment:
            return f"Release {self.tag_name} - {self.created_at_display}"
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

    @property
    def slug_size(self) -> int | None:
        if not self.pulled_at:
            return None
        if not self.heroku_release:
            return None
        if slug := self.heroku_release["slug"]:
            return slug["size"]
        return None

    @property
    def slug_size_display(self) -> str:
        """Return str representation of slug size as MB."""
        if not self.slug_size:
            return ""
        return f"{int(self.slug_size / 1024 / 1024)}MB"

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
        self.status = data["status"] or ""
        self.description = data["description"] or ""
        self.release_type = get_release_type(self.description)
        self.created_at = dateparser.parse(data["created_at"])
        if slug := data["slug"]:
            self.slug_id = slug.get("id", None)
            self.commit = slug.get("commit") or ""
            self.commit_description = slug.get("commit_description") or ""
        self.heroku_release = heroku.scrub_release(data)

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

    def get_parent(self) -> HerokuRelease | None:
        """Return first deployment before this one."""
        if self.is_deployment:
            return get_release_parent(self.version)
        return None

    def update_parent(self) -> None:
        self.parent = self.get_parent()
        self.save(update_fields=["parent"])

    def push(self) -> None:
        """
        Push release data to Github.

        This is a pessimistic insert - makes two API calls, the first is
        a GET to fetch a matching release. If it does not exist, a
        second POST request is made to create a new release.

        Raises AttributeError if the tag_name is not set as without this
        it's impossible to create a release.

        """
        if not GITHUB_SYNC_ENABLED:
            raise Exception("GITHUB_SYNC_ENABLED is False")
        if not self.tag_name:
            raise AttributeError(f"{self} is missing tag_name property.")
        if not self.commit:
            raise AttributeError(f"{self} is missing commit property.")
        if not self.parent:
            raise AttributeError(f"{self} is missing parent property.")
        # if the parent has not been pushed then autogenerating the
        # release note will pull in every commit in history...
        generate_release_notes = bool(self.parent.pushed_at)
        self.github_release = github.get_release(
            self.tag_name
        ) or github.create_release(
            tag_name=self.tag_name,
            release_name=self.release_name,
            commit=self.commit,
            generate_release_notes=generate_release_notes,
        )
        self.pushed_at = tz_now()
        self.save()

    def sync(self) -> None:
        """Pull from Heroku and push to Github."""
        self.pull()
        self.update_parent()
        self.push()

    def delete_from_github(self) -> None:
        """Delete Github release and reset metadata to reflect this."""
        if not self.github_release_id:
            return
        github.delete_release(self.github_release_id)
        self.github_release = None
        self.pushed_at = None
        self.save()

    def update_github_release(self) -> None:
        """
        Update the release notes on Github.

        This method fetches the auto-generated release notes from the
        Github API and the release_name and re-pushes to Github. Useful
        if the release get out of sync for some reason, or if we decide
        to change the format and need to re-generate the notes.

        """
        if not (self.pushed_at and self.github_release_id):
            raise ValueError("Release has not yet been pushed to Github.")
        github.update_release(
            self.github_release_id,
            {
                "body": github.generate_release_notes(self.tag_name),
                "name": self.release_name,
            },
        )
