import json

from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import HerokuRelease


@admin.register(HerokuRelease)
class HerokuReleaseAdmin(admin.ModelAdmin):
    list_display = ("version", "created_at", "description", "commit_hash")
    list_filter = ("created_at",)
    exclude = ("raw",)
    readonly_fields = (
        "version",
        "description",
        "created_at",
        "commit_hash",
        "slug_id",
        "status",
        "_raw",
    )

    @admin.display(description="Raw API response")
    def _raw(self, obj: HerokuRelease) -> str:
        """
        Return an indented HTML pretty-print version of JSON.
        Take the event_payload JSON, indent it, order the keys and then
        present it as a <code> block. That's about as good as we can get
        until someone builds a custom syntax function.
        """
        pretty = json.dumps(obj.raw, sort_keys=True, indent=4, separators=(",", ": "))
        html = pretty.replace(" ", "&nbsp;").replace("\n", "<br>")
        return mark_safe("<code>{}</code>".format(html))  # noqa: S703, S308
