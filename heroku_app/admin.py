import json

from django.contrib import admin
from django.utils.safestring import mark_safe

from .github import get_compare_url
from .models import HerokuRelease


@admin.register(HerokuRelease)
class HerokuReleaseAdmin(admin.ModelAdmin):
    list_display = (
        "version",
        "created_at",
        "description",
        "commit_hash",
        "parent",
        "has_release_note",
    )
    list_filter = ("created_at",)
    exclude = ("raw", "slug_id")
    readonly_fields = (
        "version",
        "description",
        "release_note",
        "created_at",
        "commit_hash",
        "parent",
        "diff_url",
        # "slug_id",
        "status",
        "_raw",
    )

    @admin.display(description="Has release note", boolean=True)
    def has_release_note(self, obj: HerokuRelease) -> bool:
        return bool(obj.release_note)

    @admin.display(description="View diff")
    def diff_url(self, obj: HerokuRelease) -> str:
        url = f"https://github.com/{get_compare_url(obj.base_head)}"
        return mark_safe(  # noqa: S308,S703
            f"<a href='{url}' target='_blank' rel='noopener'>{obj.base_head}</a>"
        )

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
