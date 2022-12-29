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

logger = logging.getLogger(__name__)


def format_api_errors(ex: requests.HTTPError) -> str:
    """
    Format error messages.

    See https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#client-errors

    """
    response = ex.response

    def _400() -> str:
        try:
            return response.json()["message"]
        except Exception:
            logger.exception("Error parsing Github response")

    def _422() -> str:
        try:
            errors: list[dict] = response.json()["errors"]
            return "\n".join(
                [f'E {e["resource"]}.{e["field"]}: {e["code"]}' for e in errors]
            )
        except KeyError:
            logger.exception("Error parsing Github 422 response JSON:")
            logger.error(response.json())
        except Exception:
            logger.exception("Error parsing Github response")
            logger.error(response.text)

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
    **request_kwargs,
) -> requests.Response:
    auth = check_auth()
    headers = {"Accept": "application/vnd.github+json"}
    method = getattr(requests, request_method)
    response = method(url, auth=auth, headers=headers, **request_kwargs)
    if raise_for_status:
        response.raise_for_status()
    return response


def get_release(tag_name: str) -> dict:
    """Fetch release JSON from API."""
    url = f"{GITHUB_API_RELEASES_URL}/tags/{tag_name}"
    response = _request("get", url, raise_for_status=False)
    # release found - return the JSON representation
    if response.status_code == 200:
        return response.json()
    # release does not exist - return a falsey empty dict
    if response.status_code == 404:
        return {}
    response.raise_for_status()


def update_release(release_id: int, data: dict) -> dict:
    url = f"{GITHUB_API_RELEASES_URL}/{release_id}"
    return _request("patch", url, json=data).json()


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
        "body": body,
        "generate_release_notes": generate_release_notes,
    }
    return _request("post", GITHUB_API_RELEASES_URL, json=data).json()


def get_compare_url(base_head: str) -> str:
    return f"{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/compare/{base_head}"
