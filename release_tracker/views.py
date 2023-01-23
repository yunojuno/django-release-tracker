from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .models import HerokuRelease


def admin_action_view(
    request: HttpRequest, release_id: int, method: str
) -> HttpResponseRedirect:
    """Shared view called by all the others."""
    hr = get_object_or_404(HerokuRelease, id=release_id)
    getattr(hr, method)()
    messages.add_message(request, messages.SUCCESS, "Updated release.")
    url = reverse(
        "admin:release_tracker_herokurelease_change",
        kwargs={"object_id": release_id},
    )
    return HttpResponseRedirect(url)


@user_passes_test(lambda u: u.is_staff)
def admin_pull(request: HttpRequest, release_id: int) -> HttpResponseRedirect:
    """Pull from Heroku."""
    return admin_action_view(request, release_id, "pull")


@user_passes_test(lambda u: u.is_staff)
def admin_push(request: HttpRequest, release_id: int) -> HttpResponseRedirect:
    """Push to Github."""
    return admin_action_view(request, release_id, "push")


@user_passes_test(lambda u: u.is_staff)
def admin_release_notes(request: HttpRequest, release_id: int) -> HttpResponseRedirect:
    """Update Github release notes."""
    return admin_action_view(request, release_id, "update_generated_release_notes")


@user_passes_test(lambda u: u.is_staff)
def admin_sync(request: HttpRequest, release_id: int) -> HttpResponseRedirect:
    """Sync between Heroku and Github."""
    return admin_action_view(request, release_id, "sync")
