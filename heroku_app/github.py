#! python
import argparse
import logging
from os import getenv

import requests

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_TOKEN = getenv("GITHUB_API_TOKEN")
GITHUB_ORG_NAME = getenv("GITHUB_ORG_NAME")
GITHUB_REPO_NAME = getenv("GITHUB_REPO_NAME")
GITHUB_USER_NAME = getenv("GITHUB_USER_NAME")

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument(
    "base_head",
    type=str,
    help="The base...head commit range to compare",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    default=False,
    dest="verbose",
)


def get_compare_url(base_head: str) -> str:
    return (
        # f"{GITHUB_API_BASE_URL}/repos/"
        f"{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/compare/{base_head}"
    )


def get_release_note(base_head: str) -> str:
    url = f"{GITHUB_API_BASE_URL}/repos/{get_compare_url(base_head)}"
    response = requests.get(
        url,
        headers={"Accept": "application/vnd.github+json"},
        auth=(GITHUB_USER_NAME, GITHUB_API_TOKEN),
    )
    response.raise_for_status()
    messages = []
    for commit in response.json()["commits"]:
        if len(commit["parents"]) > 1:
            continue
        message = commit["commit"]["message"].split("\n", 1)[0]
        messages.append(f"* {message}")
    return "\n".join(messages)


# print(get_release_note("ae1f729...8bb3c89"))

# if __name__ == "__main__":
#     args = parser.parse_args()
#     if args.verbose:
#         logger.level = logging.DEBUG
# print(get_release_note(args.base_head))
