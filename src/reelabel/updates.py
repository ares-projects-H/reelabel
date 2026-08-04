"""Manual, privacy-preserving checks for official Reelabel releases.

This module performs no work when it is imported. The GUI calls
``check_for_updates`` only after the user explicitly chooses to check.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ._version import __version__

LATEST_RELEASE_API = "https://api.github.com/repos/ares-projects-H/reelabel/releases/latest"
OFFICIAL_RELEASE_PATH = "/ares-projects-H/reelabel/releases/tag/"
MAX_RESPONSE_BYTES = 1_048_576
VERSION_RE = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class UpdateCheckError(RuntimeError):
    """Base error for a manual update check."""


class UpdateNetworkError(UpdateCheckError):
    """GitHub could not be reached."""


class UpdateResponseError(UpdateCheckError):
    """GitHub returned data that Reelabel could not safely use."""


class UpdateVersionError(UpdateCheckError):
    """A local or remote version does not use MAJOR.MINOR.PATCH format."""


@dataclass(frozen=True)
class UpdateCheckResult:
    """Verified result of a user-requested update check."""

    current_version: str
    latest_version: str
    update_available: bool
    release_url: str
    current_is_newer: bool = False


def _parse_version(value: str) -> tuple[int, int, int]:
    """Parse the deliberately small version format used for public releases."""

    match = VERSION_RE.fullmatch(value)
    if match is None:
        raise UpdateVersionError(
            f"Invalid release version {value!r}; expected MAJOR.MINOR.PATCH."
        )
    return tuple(int(component) for component in match.groups())


def _validate_release_url(value: object, expected_tag: str) -> str:
    """Accept only HTTPS links to this project's official GitHub releases."""

    if not isinstance(value, str):
        raise UpdateResponseError("The release response does not contain a valid URL.")
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise UpdateResponseError("The release URL contains an invalid port.") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != f"{OFFICIAL_RELEASE_PATH}{expected_tag}"
        or parsed.query
        or parsed.fragment
    ):
        raise UpdateResponseError("The release URL is not an official Reelabel GitHub URL.")
    return value


def check_for_updates(
    current_version: str = __version__,
    *,
    timeout: float = 8.0,
    opener: Callable[..., object] | None = None,
) -> UpdateCheckResult:
    """Check GitHub for the latest release without downloading any installer.

    ``opener`` exists so tests can provide a local response. Normal application
    use sends one HTTPS GET request to GitHub only after an explicit user action.
    No media paths, settings, or other user data are included.
    """

    current = _parse_version(current_version)
    request = Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Reelabel/{current_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    open_request = opener or urlopen
    try:
        with open_request(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise UpdateNetworkError("GitHub could not be reached.") from exc

    if len(body) > MAX_RESPONSE_BYTES:
        raise UpdateResponseError("The release response is unexpectedly large.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateResponseError("GitHub returned an unreadable release response.") from exc
    if not isinstance(payload, dict):
        raise UpdateResponseError("GitHub returned an unexpected release response.")

    tag = payload.get("tag_name")
    if not isinstance(tag, str):
        raise UpdateResponseError("The release response does not contain a version.")
    latest = _parse_version(tag)
    release_url = _validate_release_url(payload.get("html_url"), tag)
    return UpdateCheckResult(
        current_version=current_version.removeprefix("v"),
        latest_version=tag.removeprefix("v"),
        update_available=latest > current,
        release_url=release_url,
        current_is_newer=current > latest,
    )
