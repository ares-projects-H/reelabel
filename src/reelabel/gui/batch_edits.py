"""Pure proposal transforms; never select or rename a file implicitly."""

import re
from pathlib import Path

from reelabel import core

EPISODE_EDIT_RE = re.compile(
    r"(?:(?P<season>S\d{1,2})\s+)?(?P<episode>E\d{1,3}(?:[.-]\d+)?)",
    re.I,
)


def batch_episode_name(
    original_template: str,
    edited_template: str,
    candidate: str,
) -> str | None:
    """Apply a corrected title/season pattern while preserving episode numbers."""

    original_match = EPISODE_EDIT_RE.search(original_template)
    edited_match = EPISODE_EDIT_RE.search(edited_template)
    candidate_match = EPISODE_EDIT_RE.search(candidate)
    if not original_match or not edited_match or not candidate_match:
        return None

    original_prefix = original_template[: original_match.start()]
    edited_prefix = edited_template[: edited_match.start()]
    candidate_prefix = candidate[: candidate_match.start()]
    original_season = original_match.group("season")
    edited_season = edited_match.group("season")
    if (
        original_prefix.casefold() == edited_prefix.casefold()
        and (original_season or "").casefold() == (edited_season or "").casefold()
    ):
        return None
    if candidate_prefix.casefold() != original_prefix.casefold():
        return None

    episode = candidate_match.group("episode").upper()
    token = f"{edited_season.upper()} {episode}" if edited_season else episode
    return edited_prefix + token + candidate[candidate_match.end() :]


def batch_movie_sidecar_name(
    original_movie: str,
    edited_movie: str,
    candidate: str,
) -> str | None:
    """Apply a movie title edit to one related subtitle proposal.

    Only an exact proposed movie stem is replaced. Language and forced
    subtitle suffixes such as ``.fr`` or ``.forced`` remain unchanged.
    """

    original_path = Path(original_movie)
    edited_path = Path(edited_movie)
    candidate_path = Path(candidate)
    if original_path.suffix.casefold() not in core.VIDEO_EXTENSIONS:
        return None
    if candidate_path.suffix.casefold() not in core.SUBTITLE_EXTENSIONS:
        return None

    original_stem = original_path.stem
    prefix = f"{original_stem}."
    if not candidate.casefold().startswith(prefix.casefold()):
        return None
    return edited_path.stem + candidate[len(original_stem) :]
