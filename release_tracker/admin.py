import json

import requests
from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from .github import get_compare_url
from .models import HerokuRelease, HerokuReleaseQuerySet


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
        # "commit_hash",
        "diff_url",
        "release_url",
        # "has_release_note",
    )
    list_filter = ("created_at", "release_type")
    exclude = ("heroku_release", "github_release", "slug_id")
    ordering = ("-version",)
    readonly_fields = (
        "version",
        "commit_hash",
        "release_type",
        "description",
        "release_note",
        "created_at",
        "pulled_at",
        # "heroku_release_id",
        "pushed_at",
        "parent",
        # "github_release_id",
        "release_url",
        "diff_url",
        "status",
        "_heroku",
        "_github",
    )
    actions = (
        "set_parent_releases",
        "pull_from_heroku",
        "push_to_github",
        "sync_releases",
    )

    @admin.display(description="Release note", boolean=True)
    def has_release_note(self, obj: HerokuRelease) -> bool:
        return bool(obj.release_note)

    @admin.display(description="Changeset")
    def _diff(self, obj: HerokuRelease) -> str:
        return obj.base_head

    @admin.display(description="Github diff")
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
                f"<a href='{obj.github_release_url}' target='_blank' rel='noopener'>{str(obj)}</a>"
            )
        return ""

    @admin.display(description="Heroku API release data")
    def _heroku(self, obj: HerokuRelease) -> str:
        return format_json(obj.heroku_release)

    @admin.display(description="Github API release data")
    def _github(self, obj: HerokuRelease) -> str:
        return format_json(obj.github_release)

    @admin.action(description="Update selected release parents")
    def set_parent_releases(
        self, request: HttpRequest, qs: HerokuReleaseQuerySet
    ) -> None:
        updated = failed = 0
        ignored = qs.filter(commit_hash="").count()
        for obj in qs.exclude(commit_hash=""):
            try:
                obj.update_parent()
                updated += 1
            except Exception:  # noqa: B902
                failed += 1
        if updated:
            self.message_user(
                request, f"Updated {updated}  Heroku releases.", "success"
            )
        if ignored:
            self.message_user(
                request, f"Ignored {ignored} non-deployment releases", "warning"
            )
        if failed:
            self.message_user(
                request, f"Failed to update {failed}  Heroku releases.", "error"
            )

    @admin.action(description="Pull selected releases from Heroku")
    def pull_from_heroku(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        for obj in qs:
            obj.pull()
        self.message_user(
            request, f"Pulled {qs.count()} releases from Heroku.", "success"
        )

    @admin.action(description="Push selected releases to Github")
    def push_to_github(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        pushed = failed = 0
        for obj in qs:
            try:
                obj.push()
            except Exception:
                failed += 1
            else:
                pushed += 1
        if pushed:
            self.message_user(
                request, f"Pushed {pushed} releases to Github.", "success"
            )
        if failed:
            self.message_user(
                request, f"Failed to push {failed} releases to Github.", "error"
            )

    @admin.action(description="Sync selected releases (Heroku to Gihub)")
    def sync_releases(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        for obj in qs:
            try:
                obj.sync()
            except requests.HTTPError:
                pass
        self.message_user(
            request,
            f"Synced {qs.count()} releases between Heroku and Github.",
            "success",
        )

    # @admin.action(description="Update selected release notes")
    # def set_release_notes(
    #     self, request: HttpRequest, qs: HerokuReleaseQuerySet
    # ) -> None:
    #     updated = ignored = failed = 0
    #     for obj in qs:
    #         if not obj.base_head:
    #             ignored += 1
    #             continue
    #         try:
    #             obj.update_release_note()
    #             updated += 1
    #         except Exception:  # noqa: B902
    #             failed += 1
    #     if updated:
    #         self.message_user(
    #             request, f"Updated {updated}  Heroku releases.", "success"
    #         )
    #     if ignored:
    #         self.message_user(
    #             request, f"Ignored {ignored} non-deployment releases", "warning"
    #         )
    #     if failed:
    #         self.message_user(
    #             request, f"Failed to update {failed}  Heroku releases.", "error"
    #         )

    # @admin.action(description="Generate Github release")
    # def push_to_github(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
    #     for obj in qs.order_by("id"):
    #         obj.push()
