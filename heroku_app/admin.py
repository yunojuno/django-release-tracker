import json

from django.contrib import admin
from django.http import HttpRequest
from django.utils.safestring import mark_safe

from .github import get_compare_url
from .models import HerokuRelease, HerokuReleaseQuerySet


@admin.register(HerokuRelease)
class HerokuReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "created_at",
        "description",
        # "commit_hash",
        "diff_url",
        "has_release_note",
    )
    list_filter = ("created_at", "release_type")
    exclude = ("raw", "slug_id")
    ordering = ("-version",)
    readonly_fields = (
        "version",
        "release_type",
        "description",
        "release_note",
        "created_at",
        "commit_hash",
        "parent",
        "diff_url",
        "status",
        "_raw",
    )
    actions = ("set_parent_releases", "set_release_notes", "push_to_github")

    @admin.display(description="Release note", boolean=True)
    def has_release_note(self, obj: HerokuRelease) -> bool:
        return bool(obj.release_note)

    @admin.display(description="Changeset")
    def _diff(self, obj: HerokuRelease) -> str:
        return obj.base_head

    @admin.display(description="View diff")
    def diff_url(self, obj: HerokuRelease) -> str:
        if base_head := obj.base_head:
            url = f"https://github.com/{get_compare_url(base_head)}"
            return mark_safe(  # noqa: S308,S703
                f"<a href='{url}' target='_blank' rel='noopener'>{base_head}</a>"
            )
        return ""

    @admin.display(description="Raw API response")
    def _raw(self, obj: HerokuRelease) -> str:
        """
        Return an indented HTML pretty-print version of JSON.

        Take the event_payload JSON, indent it, order the keys and then present
        it as a <code> block. That's about as good as we can get until someone
        builds a custom syntax function.

        """
        pretty = json.dumps(obj.raw, sort_keys=True, indent=4, separators=(",", ": "))
        html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
        return mark_safe("<code>{}</code>".format(html))  # noqa: S703, S308

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

    @admin.action(description="Update selected release notes")
    def set_release_notes(
        self, request: HttpRequest, qs: HerokuReleaseQuerySet
    ) -> None:
        updated = ignored = failed = 0
        for obj in qs:
            if not obj.base_head:
                ignored += 1
                continue
            try:
                obj.update_release_note()
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

    @admin.action(description="Generate Github release")
    def push_to_github(self, request: HttpRequest, qs: HerokuReleaseQuerySet) -> None:
        for obj in qs.order_by("id"):
            obj.push()
