"""Tests for the explicit, privacy-preserving release check."""

from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from reelabel import updates

OFFICIAL_URL = "https://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0"


class FakeResponse:
    """Small context-managed response used instead of a real network request."""

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return self.body if size < 0 else self.body[:size]


def response_opener(tag: str, url: str = OFFICIAL_URL):
    body = json.dumps({"tag_name": tag, "html_url": url}).encode()

    def open_response(request, *, timeout: float):
        assert request.full_url == updates.LATEST_RELEASE_API
        assert request.get_header("User-agent").startswith("Reelabel/")
        assert timeout == 8.0
        return FakeResponse(body)

    return open_response


@pytest.mark.parametrize(
    ("current", "latest", "available", "current_is_newer"),
    (
        ("0.1.0", "v0.2.0", True, False),
        ("0.2.0", "v0.2.0", False, False),
        ("0.3.0", "v0.2.0", False, True),
    ),
)
def test_version_comparison(
    current: str,
    latest: str,
    available: bool,
    current_is_newer: bool,
) -> None:
    result = updates.check_for_updates(
        current,
        opener=response_opener(latest),
    )

    assert result.update_available is available
    assert result.current_is_newer is current_is_newer
    assert result.release_url == OFFICIAL_URL


def test_network_errors_are_distinct() -> None:
    def unavailable(*args, **kwargs):
        raise URLError("offline")

    with pytest.raises(updates.UpdateNetworkError):
        updates.check_for_updates(opener=unavailable)


@pytest.mark.parametrize(
    "body",
    (
        b"not json",
        b"[]",
        b'{"html_url": "https://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0"}',
    ),
)
def test_malformed_responses_are_rejected(body: bytes) -> None:
    with pytest.raises(updates.UpdateResponseError):
        updates.check_for_updates(opener=lambda *args, **kwargs: FakeResponse(body))


@pytest.mark.parametrize("version", ("0.2", "v0.2.0-beta", "latest", "01.2.3"))
def test_invalid_versions_are_rejected(version: str) -> None:
    with pytest.raises(updates.UpdateVersionError):
        updates.check_for_updates(version, opener=response_opener("v0.2.0"))

    with pytest.raises(updates.UpdateVersionError):
        updates.check_for_updates("0.1.0", opener=response_opener(version))


@pytest.mark.parametrize(
    "url",
    (
        "http://github.com/ares-projects-H/reelabel/releases/tag/v0.2.0",
        "https://github.com.evil.example/ares-projects-H/reelabel/releases/tag/v0.2.0",
        "https://github.com/another-owner/reelabel/releases/tag/v0.2.0",
        "https://github.com/ares-projects-H/reelabel/releases/tag/v9.9.9",
        "https://github.com:bad/ares-projects-H/reelabel/releases/tag/v0.2.0",
    ),
)
def test_unofficial_release_urls_are_rejected(url: str) -> None:
    with pytest.raises(updates.UpdateResponseError):
        updates.check_for_updates(opener=response_opener("v0.2.0", url))


def test_oversized_responses_are_rejected() -> None:
    body = b"x" * (updates.MAX_RESPONSE_BYTES + 1)
    with pytest.raises(updates.UpdateResponseError):
        updates.check_for_updates(opener=lambda *args, **kwargs: FakeResponse(body))
