"""Patch notes of the bot itself: the `vX.Y.Z` tags of its GitHub repository."""
import logging
import re
from dataclasses import dataclass

import requests

from lolbot import settings

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
GITHUB_TIMEOUT = (3.05, 10.0)
TAG_PAGE_SIZE = 100
MAX_TAG_PAGES = 5
VERSION_TAG = re.compile(r"v(\d+)\.(\d+)\.(\d+)")
MERGE_TITLE = re.compile(r"Merge pull request #\d+ from \S+", re.IGNORECASE)


class GitHubError(Exception):
    """GitHub could not be reached or answered with something unexpected."""


@dataclass(frozen=True)
class PatchNote:
    version: str
    notes: str


def _get(path: str, **params):
    try:
        response = requests.get(
            f"{GITHUB_API_URL}/repos/{settings.GITHUB_REPO}/{path}",
            params=params,
            headers={"Accept": "application/vnd.github+json"},
            timeout=GITHUB_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("GitHub request %s failed: %s", path, e)
        raise GitHubError(str(e)) from e


def _version_key(tag: str) -> tuple[int, ...]:
    return tuple(int(part) for part in VERSION_TAG.fullmatch(tag).groups())


def _release_tags() -> list[dict]:
    """Every `vX.Y.Z` tag, newest version first (GitHub lists tags alphabetically)."""
    tags: list[dict] = []
    for page in range(1, MAX_TAG_PAGES + 1):
        batch = _get("tags", per_page=TAG_PAGE_SIZE, page=page)
        tags += [t for t in batch if VERSION_TAG.fullmatch(t["name"])]
        if len(batch) < TAG_PAGE_SIZE:
            break
    return sorted(tags, key=lambda t: _version_key(t["name"]), reverse=True)


def clean_commit_message(message: str) -> str:
    """Drop the "Merge pull request #N from user/branch" line, which says nothing useful."""
    lines = message.strip().splitlines()
    if len(lines) > 1 and MERGE_TITLE.match(lines[0]):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _note(tag: dict) -> PatchNote:
    commit = _get(f"commits/{tag['commit']['sha']}")
    return PatchNote(tag["name"].lstrip("v"), clean_commit_message(commit["commit"]["message"]))


def fetch_patch_notes(limit: int = 5) -> list[PatchNote]:
    """The notes of the `limit` most recent versions, newest first."""
    return [_note(tag) for tag in _release_tags()[:limit]]


def fetch_patch_note(version: str) -> PatchNote | None:
    """The notes of one version (`1.2.0` or `v1.2.0`), or None when there is no such tag."""
    wanted = f"v{version.lstrip('vV')}"
    for tag in _release_tags():
        if tag["name"] == wanted:
            return _note(tag)
    return None
