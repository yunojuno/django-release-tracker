import json
import logging

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from .github import get_compare_url
from .models import BatchResults, HerokuRelease, HerokuReleaseQuerySet

logger = logging.getLogger(__name__)


def format_json(json_: dict) -> str:
    pretty = json.dumps(json_, sort_keys=True, indent=4, separators=(",", ": "))
    html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
    return mark_safe("<code>{}</code>".format(html))  # noqa: S703, S308


@admin.register(HerokuRelease)
class HerokuReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "created_at",
        "description",
        "slug_size_display",
        "has_parent",
        "pulled",
        "pushed",
        "diff_url",
        "release_url",
    )
    list_filter = ("created_at", "release_type")
    exclude = ("heroku_release", "github_release", "slug_id")
    ordering = ("-version",)
    readonly_fields = (
        "version",
        "release_type",
        "description",
        "commit",
        "commit_description",
        "slug_size_display",
        "created_at",
        "parent",
        "pulled_at",
        "pushed_at",
        "synced_",
        "release_url",
        "diff_url",
        "status",
        "heroku_",
        "github_",
    )
    actions = (
        "set_parent_releases",
        "pull_from_heroku",
        "push_to_github",
        "sync_releases",
        "update_release_notes",
    )

    @admin.display(boolean=True)
    def has_parent(self, obj: HerokuRelease) -> bool:
        return bool(obj.parent_id)

    @admin.display(boolean=True)
    def pulled(self, obj: HerokuRelease) -> bool:
        return bool(obj.pulled_at)

    @admin.display(boolean=True)
    def pushed(self, obj: HerokuRelease) -> bool:
        return bool(obj.pushed_at)

    @admin.display(description="Slug size (MB)")
    def slug_size_display(self, obj: HerokuRelease) -> str:
        return obj.slug_size_display

    @admin.display(description="Changeset")
    def _diff(self, obj: HerokuRelease) -> str:
        return obj.base_head

    @admin.display(description="Changeset")
    def diff_url(self, obj: HerokuRelease) -> str:
        if base_head := obj.base_head:
            url = f"https://github.com/{get_compare_url(base_head)}"
            return mark_safe(  # noqa: S308,S703
                f"<a href='{url}' target='_blank' rel='noopener'>{base_head}</a>"
            )
        return ""

    @admin.display(description="Github release")
    def release_url(self, obj: HerokuRelease) -> str:
        if obj.github_release_url:
            return mark_safe(  # noqa: S308,S703
                f"<a href='{obj.github_release_url}' "
                f"target='_blank' rel='noopener'>{str(obj)}</a>"
            )
        return ""

    @admin.display(description="Synced", boolean=True)
    def synced_(self, obj: HerokuRelease) -> bool | None:
        if obj.is_deployment:
            return bool(obj.is_synced)
        return None

    @admin.display(description="Heroku API release data")
    def heroku_(self, obj: HerokuRelease) -> str:
        return format_json(obj.heroku_release)

    @admin.display(description="Github API release data")
    def github_(self, obj: HerokuRelease) -> str:
        return format_json(obj.github_release)

    def _message_user(self, request: HttpRequest, results: BatchResults) -> None:
        if results.succeeded:
            self.message_user(
                request, f"Updated {results.succeeded} releases.", "success"
            )
        if results.failed:
            self.message_user(
                request, f"Failed to update {results.failed} releases.", "error"
            )
        if results.ignored:
            self.message_user(request, f"Ignored {results.ignored} releases", "warning")

    @admin.action(description="Update parent releases")
    def set_parent_releases(
        self, request: HttpRequest, qs: HerokuReleaseQuerySet
    ) -> None:
        self._message_user(request, qs.set_parent_releases())

    @admin.action(description="Pull releases from Heroku")
    def pull_from_heroku(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        self._message_user(request, qs.pull())

    @admin.action(description="Push releases to Github")
    def push_to_github(self, request: HttpRequest, qs: QuerySet[HerokuRelease]) -> None:
        self._message_user(request, qs.push())

    @admin.action(description="Sync releases (pull & push)")
    def sync_releases(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        self._message_user(request, qs.sync())

    @admin.action(description="Update Github release notes")
    def update_release_notes(
        self, request: HttpRequest, qs: HerokuReleaseQuerySet
    ) -> None:
        results = qs.update_github_release()
        self._message_user(request, results)
