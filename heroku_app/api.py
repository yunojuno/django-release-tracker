#! python
import argparse
import datetime
import logging
import re
from os import getenv
from typing import Iterator

import dateparser
import requests

HEROKU_API_TOKEN = getenv("HEROKU_API_TOKEN")
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")

logger = logging.getLogger("__name__")

parser = argparse.ArgumentParser()
parser.add_argument(
    "--range-start",
    type=str,
    dest="range_start",
    default="4000",
    help="id of the first release to start paging from",
)
parser.add_argument(
    "--page-size",
    type=int,
    dest="page_size",
    default="10",
    help="The number of items to return in each API call.",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    dest="verbose",
)


class HerokReleaseCrawler:
    def __init__(self) -> None:
        self.count: int = 0
        self.range_start: int = 4000
        self.page_size: int = 1000


def crawl(max_count: int, range_start: str = "id ..", page_size: int = 10) -> list:
    range = f"{range_start};max={page_size}"
    releases = []
    while range and len(releases) < max_count:
        response = _releases(range)
        releases += response.json()
        range = response.headers.get("Next-Range", "")
    return releases
    # deployments = [extract_deployment(r) for r in releases]
    # return [d for d in deployments if d][:max_count]


def extract_deployment(release: dict) -> tuple[int, datetime.datetime, str] | None:
    version, created_at, description = (
        release["version"],
        dateparser.parse(release["created_at"]),
        release["description"],
    )
    regex = r"Deploy (?P<commit>\w*)"

    if match := re.match(regex, description, re.RegexFlag.IGNORECASE):
        commit = match["commit"]
        return version, created_at, commit
    return None


def _releases(range: str) -> list:
    print("Requesting releases for range: ", range)
    return requests.get(
        f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/releases/",
        headers={
            "Range": range,
            "Accept": "Accept: application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        },
    )


def _slug(slug_id: str) -> dict:
    response = requests.get(
        f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/slugs/{slug_id}",
        headers={
            "Accept": "Accept: application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        },
    )
    return response.json()


# def get_releases(range: str = "id ..; max=1000") -> str:
def get_releases(range_start: int, max_count: int) -> Iterator[str]:
    response = requests.get(
        f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/releases/",
        headers={
            "Range": range,
            "Accept": "Accept: application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        },
    )
    range = "id ..; max=1000"
    releases = _releases(range)
    for release in releases:
        if slug_id := release.get("slug", None):
            slug = get_slug(slug_id["id"])
            # print(
            #     f"{release['version']};{slug['commit']};"
            #     f"{release['created_at']};{release['description']}"
            # )
    return response.headers.get("Next-Range", "")


def get_slug(slug_id: str):
    response = requests.get(
        f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/slugs/{slug_id}",
        headers={
            "Accept": "Accept: application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_TOKEN}",
        },
    )
    return response.json()


# range = "id ..; max=1000"
# while range:
#     range = get_releases(range)

if __name__ == "__main__":
    args = parser.parse_args()
    if args.verbose:
        logger.level = logging.DEBUG
    range_start = args.range_start
    page_size = args.page_size
    # import heroku

    # heroku.get_releases(f"id {range_start}..; max={page_size}")
    pages = 10
    # for p in range(pages):

    releases = crawl(10000, page_size=100)
    # printout = [f"{r[0]} {r[1].date().isoformat()} {r[2]}" for r in releases]
    # print("\n".join(printout))
    # get_releases(f"id 4000..; max={page_size}")
