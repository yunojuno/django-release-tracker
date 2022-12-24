import logging

import requests

from .settings import HEROKU_API_TOKEN, HEROKU_APP_NAME

logger = logging.getLogger("__name__")


def crawl(max_count: int, range_start: str = "id ..", page_size: int = 1000) -> list:
    range = f"{range_start};max={page_size}"
    releases: list[dict] = []
    while range and len(releases) < max_count:
        response = _releases(range)
        releases += response.json()
        range = response.headers.get("Next-Range", "")
    return releases


def _releases(range: str) -> requests.Response:
    if not HEROKU_API_TOKEN:
        raise Exception("Missing HEROKU_API_TOKEN config var.")
    response = requests.get(
        f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/releases/",
        headers={
            "Range": range,
            "Accept": "Accept: application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        },
    )
    response.raise_for_status()
    return response
