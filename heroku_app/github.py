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

logger = logging.getLogger(__name__)


def get_compare_url(base_head: str) -> str:
    return f"{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/compare/{base_head}"


def get_release_note(base_head: str) -> str:
    if not GITHUB_USER_NAME:
        raise Exception("Missing GITHUB_USER_NAME setting")
    if not GITHUB_API_TOKEN:
        raise Exception("Missing GITHUB_API_TOKEN setting")
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


def generate_release_note(release: HerokuRelease) -> str:
    """
    {
    "tag_name": "v1.0.0",
    "target_commitish": "master",
    "name": "v1.0.0",
    "body": "Description of the release",
    "draft": false,
    "prerelease": false,
    "generate_release_notes": false
    }
    """
    from .models import HerokuRelease

    url = f"{GITHUB_API_BASE_URL}/repos/{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/releases/generate-notes"
    data = {
        "tag_name": release.tag_name,
        "target_commitish": release.commit_hash,
        "previous_tag_name": release.parent.tag_name,
    }
    response = requests.post(
        url,
        headers={"Accept": "application/vnd.github+json"},
        auth=(GITHUB_USER_NAME, GITHUB_API_TOKEN),
        json=data,
    )
    print(data)
    print(response.json())
    response.raise_for_status()
    return response.json().get("body")


def create_github_release(release: HerokuRelease) -> dict:
    from .models import HerokuRelease

    url = f"{GITHUB_API_BASE_URL}/repos/{GITHUB_ORG_NAME}/{GITHUB_REPO_NAME}/releases"
    data = {
        "tag_name": release.tag_name,
        "name": f"Release {release.tag_name}",
        "target_commitish": release.commit_hash,
        "body": release.release_note,
        "generate_release_notes": True,
    }
    response = requests.post(
        url,
        headers={"Accept": "application/vnd.github+json"},
        auth=(GITHUB_USER_NAME, GITHUB_API_TOKEN),
        json=data,
    )
    print(data)
    print(response.json())
    response.raise_for_status()
    return response.json()
