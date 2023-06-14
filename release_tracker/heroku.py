import logging
from uuid import UUID

import requests

from .settings import HEROKU_API_TOKEN, HEROKU_APP_NAME

logger = logging.getLogger("__name__")

API_PREFIX = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/"


def check_auth() -> None:
    if not HEROKU_API_TOKEN:
        raise Exception("Missing HEROKU_API_TOKEN config var.")


def _get(url: str, **headers: str) -> requests.Response:
    """Call the platform api with a GET request."""
    check_auth()
    headers.setdefault("Authorization", f"Bearer {HEROKU_API_TOKEN}")
    headers.setdefault("Accept", "Accept: application/vnd.heroku+json; version=3")
    response = requests.get(f"{API_PREFIX}{url}", headers=headers, timeout=10)
    response.raise_for_status()
    return response


def crawl(max_count: int, range_start: str = "id ..", page_size: int = 1000) -> list:
    logger.debug("Crawling releases (max_count=%i)", max_count)
    next_range = f"{range_start};max={page_size}"
    releases: list[dict] = []
    while next_range and len(releases) < max_count:
        response = _get("releases", Range=next_range)
        releases += response.json()
        next_range = response.headers.get("Next-Range", "")
    return releases


def get_release(version: str) -> dict:
    release = _get(f"releases/{version}").json()
    return scrub_release(release)


def get_slug(slug_id: UUID) -> dict:
    slug = _get(f"slugs/{slug_id}").json()
    return scrub_slug(slug)


def scrub_release(release: dict) -> dict:
    return {
        k: v
        for k, v in release.items()
        if k in ["created_at", "description", "status", "id", "slug", "version"]
    }


def scrub_slug(slug: dict) -> dict:
    return {
        k: v
        for k, v in slug.items()
        if k in ["commit", "commit_description", "id", "size", "updated_at"]
    }
