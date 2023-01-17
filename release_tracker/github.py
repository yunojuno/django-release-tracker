from __future__ import annotations

import logging

import requests

from .settings import (
    GITHUB_API_TOKEN,
    GITHUB_ORG_NAME,
    GITHUB_REPO_NAME,
    GITHUB_USER_NAME,
)

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_REPO_URL = (
    f"{GITHUB_API_BASE_URL}/repos/{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}"
)
GITHUB_API_RELEASES_URL = f"{GITHUB_API_REPO_URL}/releases"
GITHUB_API_RELEASE_NOTES_URL = f"{GITHUB_API_RELEASES_URL}/generate-notes"

logger = logging.getLogger(__name__)


def format_api_errors(ex: requests.HTTPError) -> str:  # noqa: C901 (11)
    """
    Format error messages.

    See https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#client-errors  # noqa: E501

    """
    response = ex.response

    def _400() -> str:
        return response.json()["message"]

    def _422() -> str:
        try:
            errors: list[dict] = response.json()["errors"]
            return "\n".join(
                [f'E {e["resource"]}.{e["field"]}: {e["code"]}' for e in errors]
            )
        except KeyError:
            logger.exception("Error parsing Github 422 response JSON:")
            logger.error(response.json())
        return ""

    if response.status_code == 400:
        return _400()
    if response.status_code == 422:
        return _422()
    if response.status_code == 500:
        return f"Unknown server error: {ex}"
    return ""


def check_auth() -> tuple[str, str]:
    if not GITHUB_API_TOKEN:
        raise Exception("Missing GITHUB_API_TOKEN setting")
    if not GITHUB_ORG_NAME:
        raise Exception("Missing GITHUB_ORG_NAME setting")
    if not GITHUB_USER_NAME:
        raise Exception("Missing GITHUB_USER_NAME setting")
    if not GITHUB_REPO_NAME:
        raise Exception("Missing GITHUB_REPO_NAME setting")
    return (GITHUB_USER_NAME, GITHUB_API_TOKEN)


def _request(
    request_method: str,
    url: str,
    raise_for_status: bool = True,
    **request_kwargs: object,
) -> requests.Response:
    auth = check_auth()
    headers = {"Accept": "application/vnd.github+json"}
    method = getattr(requests, request_method)
    response = method(url, auth=auth, headers=headers, **request_kwargs)
    if response.status_code == 422:
        logger.debug(response.json())
    if raise_for_status:
        response.raise_for_status()
    return response


def get_release(tag_name: str) -> dict:
    """Fetch release JSON from API."""
    url = f"{GITHUB_API_RELEASES_URL}/tags/{tag_name}"
    response = _request("get", url, raise_for_status=False)
    # release found - return the JSON representation
    if response.status_code == 200:
        return scrub_release(response.json())
    # release does not exist - return a falsey empty dict
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return {}


def update_release(release_id: int, data: dict) -> dict:
    url = f"{GITHUB_API_RELEASES_URL}/{release_id}"
    release = _request("patch", url, json=data).json()
    return scrub_release(release)


def delete_release(release_id: int) -> None:
    url = f"{GITHUB_API_RELEASES_URL}/{release_id}"
    response = _request("delete", url, raise_for_status=False)
    # expected response status for a deletion
    if response.status_code == 204:
        return
    # release does not exist - ignore
    if response.status_code == 404:
        return
    # for everything else raise if appropriate
    response.raise_for_status()


def create_release(
    tag_name: str,
    commit: str,
    body: str | None = None,
    generate_release_notes: bool = True,
) -> dict:
    """Create a new Github release."""
    data = {
        "tag_name": tag_name,
        "name": f"Release {tag_name}",
        "target_commitish": commit,
        "body": body or "",
        "generate_release_notes": generate_release_notes,
    }
    release = _request("post", GITHUB_API_RELEASES_URL, json=data).json()
    return scrub_release(release)


def generate_release_notes(tag_name: str) -> str:
    """Generate release notes from the generate-notes API."""
    response = _request(
        "post",
        GITHUB_API_RELEASE_NOTES_URL,
        json={"tag_name": tag_name},
    )
    return response.json().get("body")


def get_compare_url(base_head: str) -> str:
    return f"{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/compare/{base_head}"


def scrub_release(slug: dict) -> dict:
    return {
        k: v
        for k, v in slug.items()
        if k
        in [
            "body",
            "created_at",
            "html_url",
            "id",
            "name",
            "published_at",
            "tag_name",
            "target_commitish",
        ]
    }
