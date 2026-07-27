from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".wmv", ".webm", ".mpg", ".mpeg", ".ts", ".m2ts", ".rmvb"}
SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".sub", ".vtt", ".idx", ".sup"}
SIDECAR_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".webp", ".gif", ".bmp",
    ".tif", ".tiff", ".avif", ".heic", ".heif", ".ico", ".svg", ".nfo",
}
TECHNICAL_TOKENS = {
    "480p", "576p", "720p", "1080p", "1440p", "2160p", "4320p", "4k", "8k",
    "x264", "x265", "h264", "h265", "hevc", "av1", "aac", "ac3", "eac3", "dts",
    "truehd", "atmos", "bluray", "bdrip", "brrip", "web-dl", "webdl", "webrip",
    "hdtv", "dvdrip", "remux", "repack", "proper", "10bit", "8bit", "hdr", "dv",
    "dolby", "vision", "multi", "french", "vostfr", "criterion",
    "raw",
}
EXTRA_TOKENS = {
    "trailer", "trailers", "teaser", "teasers", "sample", "samples", "bonus",
    "extras", "extra", "interview", "interviews", "making of", "making-of",
    "featurette", "featurettes", "deleted scene", "deleted scenes", "extrait", "extraits",
}
GENERIC_MOVIE_FOLDER_WORDS = {"movie", "movies", "ova", "oad", "special", "specials"}
LANGUAGE_ALIASES = {
    "fr": "fr", "fre": "fr", "fra": "fr", "french": "fr", "francais": "fr", "français": "fr",
    "en": "en", "eng": "en", "english": "en", "anglais": "en",
    "es": "es", "spa": "es", "spanish": "es", "espanol": "es", "español": "es",
    "de": "de", "ger": "de", "deu": "de", "german": "de", "allemand": "de",
    "it": "it", "ita": "it", "italian": "it", "italien": "it",
    "ja": "ja", "jp": "ja", "jpn": "ja", "japanese": "ja", "japonais": "ja",
}
TYPE_ALIASES = {"forced": "forced", "sdh": "sdh", "cc": "cc", "commentary": "commentary", "hearing impaired": "sdh"}
_CONFIG_LOCK = threading.RLock()
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
DISC_RE = re.compile(r"(?<!\w)CD[\s._-]*(\d{1,2})(?!\w)", re.I)
EPISODE_NUMBER = r"\d{1,3}(?:[.-]\d{1,2})?"
EPISODE_REVISION = r"(?:v\d+)?"
# Release groups commonly append a revision marker (e.g. "04v2").  It is
# metadata for the same episode, not part of its title or episode number.
SERIES_RE = re.compile(rf"\bS(?:EASON|AISON)?\s*(\d{{1,2}})\s*[ ._-]*E(?:PISODE)?\s*({EPISODE_NUMBER}){EPISODE_REVISION}(?!\w)", re.I)
X_SERIES_RE = re.compile(rf"\b(\d{{1,2}})\s*[xX]\s*({EPISODE_NUMBER}){EPISODE_REVISION}(?!\w)", re.I)
EPISODE_RE = re.compile(rf"\b(?P<label>E|EP|EPISODE)\s*(?P<episode>\d{{1,3}}){EPISODE_REVISION}(?!\w)", re.I)
FRACTIONAL_EPISODE_RE = re.compile(rf"(?<!\d)({EPISODE_NUMBER})(?![\d.])")
BARE_RELEASE_EPISODE_RE = re.compile(rf"(?:^|\s-\s)({EPISODE_NUMBER}){EPISODE_REVISION}(?:\s+(END))?(?=\s*(?:\[|$))", re.I)
# Unlike a bare "- 04", a revision suffix makes it explicit that this is a
# release revision of episode 04. It is safe even without a Season folder.
VERSIONED_BARE_RELEASE_EPISODE_RE = re.compile(
    rf"^(?P<title>.+?)\s-\s(?P<episode>{EPISODE_NUMBER})v\d+(?:\s+(?P<end>END))?(?=\s*(?:\[|$))",
    re.I,
)
# Common raw releases use "Title - 01 RAW (station)" outside a Season
# subfolder.  This is only used when the title also agrees with its folder.
RAW_RELEASE_EPISODE_RE = re.compile(rf"(?:^|\s-\s)(\d{{1,3}}){EPISODE_REVISION}(?:\s+(END))?(?=\s*(?:RAW\b|\(|\[|$))", re.I)
CHAPTER_RE = re.compile(rf"\bCHAPTER\s*(\d{{1,3}}){EPISODE_REVISION}(?!\w)", re.I)
SEASON_FOLDER_RE = re.compile(r"^(?:s(?:eason|aison)?\s*)?(\d{1,2})$|^s(\d{1,2})$", re.I)
# A series title may carry its season in the same directory name, such as
# "Doctor X Season 3", "Show Saison 02", or the short "Show S03" form.
SEASON_TITLE_SUFFIX_RE = re.compile(
    r"^(?P<title>.+?)\s+(?:S(?:eason|aison)?\s*)(?P<season>\d{1,2})$", re.I
)


@dataclass
class ParsedName:
    title: str
    year: str | None = None
    season: int | None = None
    episode: str | None = None
    episode_title: str | None = None
    is_extra: bool = False
    disc: int | None = None
    chapter: int | None = None
    oad_episode: str | None = None

    @property
    def is_series(self) -> bool:
        return self.season is not None and self.episode is not None

    def display(self) -> str:
        base = self.title
        if self.disc is not None and not self.is_series:
            base += f".CD{self.disc}"
        if self.year:
            base += f" ({self.year})"
        if self.chapter is not None:
            base += f" Chapter {self.chapter:02d}"
        if self.oad_episode is not None:
            integer, dot, fraction = self.oad_episode.partition(".")
            separator = "." if int(integer) == 0 else "-"
            formatted = f"{int(integer):02d}" + (f"{separator}{fraction}" if dot else "")
            base += f" E{formatted}"
        if self.is_series:
            integer, dot, fraction = self.episode.partition(".")
            # Ordered specials use E00.1/E00.2, while ordinary fractional
            # episodes keep the established E13-5 style.
            fraction_separator = "." if int(integer) == 0 else "-"
            formatted_episode = f"{int(integer):02d}" + (f"{fraction_separator}{fraction}" if dot else "")
            base += f" S{self.season:02d} E{formatted_episode}"
            if self.episode_title:
                if self.episode_title in {"END", "SP"}:
                    base += f" {self.episode_title}"
                elif int(integer) == 0:
                    base += f" {self.episode_title}"
                else:
                    base += f" - {self.episode_title}"
        return base


@dataclass
class MediaFile:
    path: Path
    kind: str
    parsed: ParsedName
    suffixes: tuple[str, ...] = ()


@dataclass
class Rename:
    source: Path
    destination: Path
    reason: str
    status: str = "proposed"
    detail: str = ""


@dataclass
class Deletion:
    path: Path
    reason: str = "image ou fichier NFO du dossier renommé"
    status: str = "proposed"
    detail: str = ""


@dataclass
class Report:
    videos_found: int = 0
    subtitles_found: int = 0
    renames: list[Rename] = field(default_factory=list)
    deletions: list[Deletion] = field(default_factory=list)
    ignored: list[tuple[Path, str]] = field(default_factory=list)
    conflicts: list[tuple[Path, str]] = field(default_factory=list)
    missing_subtitles: list[tuple[Path, str]] = field(default_factory=list)


class ScanCancelled(RuntimeError):
    """Raised when a caller asks a read-only folder scan to stop."""


def _normal_space(value: str) -> str:
    value = re.sub(r"[._]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ._-\t")


def _tokens(value: str) -> list[str]:
    return [x for x in re.split(r"[\s._\-\[\](){}]+", value.casefold()) if x]


def _title_case(value: str) -> str:
    """Use a modest title case only when the original casing has no signal."""
    value = _normal_space(value)
    letters = "".join(ch for ch in value if ch.isalpha())
    if not letters or not (letters.islower() or letters.isupper()):
        return value
    minor = {"a", "an", "and", "as", "at", "but", "by", "de", "des", "du", "et", "for", "in", "la", "le", "les", "of", "on", "or", "the", "to", "un", "une", "vs", "with"}
    words = value.split(" ")
    result: list[str] = []
    for index, word in enumerate(words):
        if word == "KG":
            result.append(word)
        elif word.casefold() in minor and index not in (0, len(words) - 1):
            result.append(word.casefold())
        elif len(word) <= 4 and word.isupper() and any(ch.isdigit() for ch in word):
            result.append(word)
        else:
            result.append(word[:1].upper() + word[1:].casefold())
    return " ".join(result)


def _strip_release_prefix(value: str) -> str:
    """Remove leading bracketed release-group labels, e.g. ``[Commie]``."""
    return re.sub(r"^(?:\s*\[[^\]]+\]\s*)+", "", value).strip()


def _remove_technical(value: str) -> str:
    """Trim release metadata from its first clear marker onward."""
    text = _normal_space(_strip_release_prefix(value))
    parts = text.split()
    cut = len(parts)
    for index, part in enumerate(parts):
        token = part.casefold().strip("[](){}")
        if token in TECHNICAL_TOKENS or re.fullmatch(r"\d{3,4}p", token) or re.fullmatch(r"\d{3,4}x\d{3,4}", token):
            cut = index
            break
    return " ".join(parts[:cut]).strip()


def _extract_year(value: str) -> tuple[str, str | None]:
    match = YEAR_RE.search(value)
    if not match:
        return value, None
    cleaned = (value[:match.start()] + " " + value[match.end():]).strip()
    # Removing a year from "Title (2020)" must not leave "Title ( )".
    cleaned = re.sub(r"[\(\[\{]\s*[\)\]\}]", " ", cleaned)
    return _normal_space(cleaned), match.group(1)


def _extract_disc(value: str) -> tuple[str, int | None]:
    match = DISC_RE.search(value)
    if not match:
        return value, None
    cleaned = value[:match.start()] + " " + value[match.end():]
    return _normal_space(cleaned), int(match.group(1))


def _season_parent_info(path: Path, root: Path) -> tuple[int, Path, str | None] | None:
    """Find Season 1/S01 and title-bearing folders such as Show S01."""
    current = path.parent
    while True:
        name = _normal_space(current.name)
        match = SEASON_FOLDER_RE.fullmatch(name)
        if match:
            return int(match.group(1) or match.group(2)), current, None
        titled_match = SEASON_TITLE_SUFFIX_RE.fullmatch(name)
        if titled_match:
            return int(titled_match.group("season")), current, titled_match.group("title")
        if current == root or current.parent == current:
            return None
        current = current.parent


def _season_from_parents(path: Path, root: Path) -> int | None:
    info = _season_parent_info(path, root)
    return info[0] if info else None


def _series_title_from_parent(path: Path, root: Path) -> str | None:
    info = _season_parent_info(path, root)
    if not info:
        return None
    _, season_directory, embedded_title = info
    candidate = embedded_title if embedded_title is not None else season_directory.parent.name
    candidate = _remove_technical(candidate)
    return _title_case(_extract_year(candidate)[0]) or None


def parse_media_name(path: Path, root: Path) -> ParsedName:
    stem = path.stem
    normalized = _normal_space(stem)
    is_extra = any(marker in normalized.casefold() for marker in EXTRA_TOKENS)
    # Movie/Movies, OVA and OAD explicitly identify a film or short-film release,
    # not a TV episode, even when numbers resemble S01E01.
    is_movie_labelled = bool(re.search(r"\b(?:movies?|ova|oad)\b", normalized, re.I))
    is_oad_labelled = bool(re.search(r"\boad\b", normalized, re.I))
    # Match against the raw stem so a meaningful decimal episode such as
    # E13.5 is not destroyed by general dot-to-space normalization.
    match = SERIES_RE.search(stem) or X_SERIES_RE.search(stem)
    # OADs can have ordered entries, but do not belong to a TV season. Keep
    # their episode number as E01, E02, ... without adding S01.
    if match and is_oad_labelled:
        episode = match.group(2).replace("-", ".")
        before, after = _normal_space(stem[:match.start()]), _normal_space(stem[match.end():])
        before, year = _extract_year(before)
        title = _title_case(_remove_technical(before))
        raw_episode_title = _remove_technical(after).strip(" -")
        episode_title = (
            "END" if raw_episode_title.casefold() == "end"
            else "SP" if raw_episode_title.casefold() == "sp"
            else _title_case(raw_episode_title) or None
        )
        return ParsedName(title, year, episode_title=episode_title, is_extra=is_extra, oad_episode=episode)
    if match and not is_movie_labelled:
        season, episode = int(match.group(1)), match.group(2).replace("-", ".")
        before, after = _normal_space(stem[:match.start()]), _normal_space(stem[match.end():])
        before, year = _extract_year(before)
        title = _title_case(_remove_technical(before))
        season_info = _season_parent_info(path, root)
        # A title-bearing season directory is explicit metadata.  It repairs
        # release filenames that incorrectly carry S01 (or repeat the season
        # number in the title) inside e.g. "Saito-san Season 2".
        parent_title = _series_title_from_parent(path, root)
        if season_info and season != season_info[0]:
            # A contradiction such as "Season 2/Saitou-san 2 S01 E01"
            # is resolved from the explicit parent folder, which also avoids
            # retaining the duplicated season number in the title.
            season = season_info[0]
            title = parent_title or title
        elif season_info and season_info[2] is not None:
            title = parent_title or title
        elif not title:
            title = parent_title or ""
        raw_episode_title = _remove_technical(after).strip(" -")
        episode_title = (
            "END" if raw_episode_title.casefold() == "end"
            else "SP" if raw_episode_title.casefold() == "sp"
            else _title_case(raw_episode_title) or None
        )
        return ParsedName(title, year, season, episode, episode_title, is_extra)

    episode_match = EPISODE_RE.search(normalized)
    season_info = _season_parent_info(path, root)
    inherited = season_info[0] if season_info else None
    implicit_first_season = episode_match and episode_match.group("label").casefold() in {"ep", "episode"}
    if not is_movie_labelled and episode_match and (inherited is not None or implicit_first_season):
        before, after = normalized[:episode_match.start()].strip(), normalized[episode_match.end():].strip()
        before, year = _extract_year(before)
        parent_title = _series_title_from_parent(path, root)
        # "Title Season 3" and "Title S03" explicitly name both the
        # series and its season, so they are a more reliable title source
        # than release stems such as "Title-3 ep02".
        title = (
            parent_title
            if season_info and season_info[2] is not None
            else _title_case(_remove_technical(before)) or parent_title or ""
        )
        # Files named only "EP01" rely on their immediate folder for the
        # series title.  This is an explicit local source, not a guess.
        if not title:
            folder_value, folder_year = _extract_year(_remove_technical(_normal_space(path.parent.name)))
            title = _title_case(folder_value)
            year = year or folder_year
        raw_episode_title = _remove_technical(after).strip(" -")
        episode_title = (
            "END" if raw_episode_title.casefold() == "end"
            else "SP" if raw_episode_title.casefold() == "sp"
            else _title_case(raw_episode_title) or None
        )
        return ParsedName(title, year, inherited or 1, episode_match.group("episode"), episode_title, is_extra)

    # A trailing revision marker, such as "Title - 04v2", unambiguously
    # denotes a revised release of episode 04 rather than a title component.
    versioned_bare_release = VERSIONED_BARE_RELEASE_EPISODE_RE.search(normalized)
    if versioned_bare_release and not is_movie_labelled:
        title_value, year = _extract_year(versioned_bare_release.group("title"))
        title = _title_case(_remove_technical(title_value))
        if title:
            marker = "END" if versioned_bare_release.group("end") else None
            return ParsedName(title, year, inherited or 1, versioned_bare_release.group("episode").replace("-", "."), marker, is_extra)

    # Release names commonly end in " - 01 [720p]". In an explicit season
    # folder this position identifies the episode safely, including specials
    # such as 13.5. Other bare integers remain ambiguous and are not guessed.
    if inherited is not None and not is_movie_labelled:
        bare_release = BARE_RELEASE_EPISODE_RE.search(stem)
        fractional = next((m for m in FRACTIONAL_EPISODE_RE.finditer(stem) if "." in m.group(1)), None)
        episode = bare_release.group(1) if bare_release else fractional.group(1) if fractional else None
        if episode:
            title = _series_title_from_parent(path, root) or ""
            marker = "END" if bare_release and bare_release.group(2) else None
            return ParsedName(title, None, inherited, episode.replace("-", "."), marker, is_extra)

    # A raw release can use a bare episode number without a Season directory.
    # The current folder is accepted as the series title only when it has
    # meaningful words in common with the filename title.
    raw_release = RAW_RELEASE_EPISODE_RE.search(stem)
    if raw_release and not is_movie_labelled:
        before = _normal_space(stem[:raw_release.start()])
        filename_title = _title_case(_remove_technical(before))
        folder_value, folder_year = _extract_year(_remove_technical(_normal_space(path.parent.name)))
        folder_title = _title_case(folder_value)
        filename_words = {word for word in _tokens(filename_title) if len(word) > 1}
        folder_words = {word for word in _tokens(folder_title) if len(word) > 1}
        if folder_title and filename_words & folder_words:
            marker = "END" if raw_release.group(2) else None
            return ParsedName(folder_title, folder_year, 1, raw_release.group(1), marker, is_extra)

    # Multi-part releases may label their chronological parts as Chapter 1,
    # Chapter 2, etc. Keep that label rather than collapsing every file to
    # the same movie title.
    chapter_match = CHAPTER_RE.search(normalized)
    if chapter_match:
        before, year = _extract_year(normalized[:chapter_match.start()])
        title = _title_case(_remove_technical(before))
        if title:
            return ParsedName(title, year, is_extra=is_extra, chapter=int(chapter_match.group(1)))

    # Extract the disc before trimming technical metadata because CD1/CD2 is
    # often placed after DVDRip/XviD and would otherwise be discarded.
    value, disc = _extract_disc(normalized)
    value, year = _extract_year(_remove_technical(value))
    return ParsedName(_title_case(value), year, is_extra=is_extra, disc=disc)


def subtitle_suffixes(path: Path) -> tuple[str, ...]:
    normalized = _normal_space(path.stem).casefold()
    found: list[str] = []
    for phrase, code in {**LANGUAGE_ALIASES, **TYPE_ALIASES}.items():
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized, re.I) and code not in found:
            found.append(code)
    return tuple(found)


def load_config(config_path: Path | None) -> dict[str, set[str]]:
    config = {"video_extensions": set(VIDEO_EXTENSIONS), "subtitle_extensions": set(SUBTITLE_EXTENSIONS), "technical_tokens": set(TECHNICAL_TOKENS), "extra_tokens": set(EXTRA_TOKENS)}
    if not config_path:
        return config
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Configuration illisible: {exc}") from exc
    allowed = set(config) | {"language_aliases"}
    unknown = set(data) - allowed
    if unknown or not isinstance(data, dict):
        raise ValueError(f"Clés de configuration invalides: {', '.join(sorted(unknown)) or 'racine'}")
    for key in ("video_extensions", "subtitle_extensions", "technical_tokens", "extra_tokens"):
        if key in data:
            if not isinstance(data[key], list) or not all(isinstance(x, str) and x.strip() for x in data[key]):
                raise ValueError(f"{key} doit être une liste de chaînes non vides")
            values = {x.casefold().strip() for x in data[key]}
            if "extensions" in key and not all(x.startswith(".") for x in values):
                raise ValueError(f"{key} doit contenir des extensions commençant par un point")
            config[key].update(values)
    if "language_aliases" in data:
        if not isinstance(data["language_aliases"], dict) or not all(isinstance(k, str) and isinstance(v, str) and v for k, v in data["language_aliases"].items()):
            raise ValueError("language_aliases doit être un objet chaîne-vers-chaîne")
        LANGUAGE_ALIASES.update({k.casefold(): v.casefold() for k, v in data["language_aliases"].items()})
    return config


def discover(
    root: Path,
    recursive: bool,
    config: dict[str, set[str]],
    cancelled: Callable[[], bool] | None = None,
) -> tuple[list[Path], list[Path]]:
    iterator: Iterable[Path] = root.rglob("*") if recursive else root.iterdir()
    videos, subtitles = [], []
    for path in iterator:
        if cancelled is not None and cancelled():
            raise ScanCancelled("The scan was cancelled.")
        if not path.is_file():
            continue
        suffix = path.suffix.casefold()
        if suffix in config["video_extensions"]:
            videos.append(path)
        elif suffix in config["subtitle_extensions"]:
            subtitles.append(path)
    return sorted(videos), sorted(subtitles)


def _match_subtitle(subtitle: MediaFile, videos: list[MediaFile]) -> MediaFile | None:
    viable = [v for v in videos if not v.parsed.is_extra]
    scored: list[tuple[int, MediaFile]] = []
    sub_tokens = set(_tokens(subtitle.path.stem))
    for video in viable:
        score = len(sub_tokens & set(_tokens(video.path.stem)))
        if subtitle.parsed.year and subtitle.parsed.year == video.parsed.year:
            score += 10
        if subtitle.parsed.is_series and video.parsed.is_series:
            if (subtitle.parsed.season, subtitle.parsed.episode) == (video.parsed.season, video.parsed.episode):
                score += 30
            else:
                continue
        if subtitle.parsed.chapter is not None:
            if subtitle.parsed.chapter == video.parsed.chapter:
                score += 30
            elif video.parsed.chapter is not None:
                continue
        if subtitle.parsed.disc is not None:
            if subtitle.parsed.disc == video.parsed.disc:
                score += 30
            else:
                continue
        if subtitle.parsed.title and subtitle.parsed.title.casefold() == video.parsed.title.casefold():
            score += 20
        scored.append((score, video))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored[0][0] > 0 and (len(scored) == 1 or scored[0][0] > scored[1][0]) else None


def build_report(
    root: Path,
    recursive: bool = True,
    only: str | None = None,
    include_extras: bool = False,
    config_path: Path | None = None,
    include_sidecars: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> Report:
    """Build a read-only rename report without leaking custom config globally.

    The original CLI extends module-level token sets while loading a custom
    configuration. A desktop application can scan several folders during one
    session, so every scan must restore those defaults when it finishes.
    """
    with _CONFIG_LOCK:
        original_technical = set(TECHNICAL_TOKENS)
        original_extras = set(EXTRA_TOKENS)
        original_languages = dict(LANGUAGE_ALIASES)
        try:
            return _build_report(
                root,
                recursive,
                only,
                include_extras,
                config_path,
                include_sidecars,
                cancelled,
            )
        finally:
            TECHNICAL_TOKENS.clear()
            TECHNICAL_TOKENS.update(original_technical)
            EXTRA_TOKENS.clear()
            EXTRA_TOKENS.update(original_extras)
            LANGUAGE_ALIASES.clear()
            LANGUAGE_ALIASES.update(original_languages)


def _build_report(
    root: Path,
    recursive: bool,
    only: str | None,
    include_extras: bool,
    config_path: Path | None,
    include_sidecars: bool,
    cancelled: Callable[[], bool] | None,
) -> Report:
    root = root.resolve()
    config = load_config(config_path)
    # Configuration only extends the conservative built-ins for this process.
    TECHNICAL_TOKENS.update(config["technical_tokens"])
    EXTRA_TOKENS.update(config["extra_tokens"])
    videos, subtitles = discover(root, recursive, config, cancelled)
    report = Report(len(videos), len(subtitles))
    video_items = [MediaFile(path, "video", parse_media_name(path, root)) for path in videos]
    subtitle_items = [MediaFile(path, "subtitle", parse_media_name(path, root), subtitle_suffixes(path)) for path in subtitles]
    by_dir: dict[Path, list[MediaFile]] = defaultdict(list)
    for item in video_items:
        by_dir[item.path.parent].append(item)

    # A lone movie takes the cleaned folder title, including a clear year.
    for directory, items in by_dir.items():
        main_movies = [x for x in items if not x.parsed.is_extra and not x.parsed.is_series]
        multipart_movie = len(main_movies) > 1 and all(item.parsed.disc is not None for item in main_movies)
        if len(main_movies) == 1 or multipart_movie:
            folder_value, folder_year = _extract_year(_remove_technical(_normal_space(directory.name)))
            folder_title = _title_case(folder_value)
            # Do not turn a generic selected root (for example Downloads or a
            # temporary test directory) into a film title.  A parent is a
            # useful source when it names the release (same title words) or
            # makes its year explicit.
            movie_words = {word for item in main_movies for word in _tokens(item.parsed.title) if len(word) > 1}
            folder_words = {word for word in _tokens(folder_title) if len(word) > 1}
            meaningful_overlap = (movie_words & folder_words) - GENERIC_MOVIE_FOLDER_WORDS
            if folder_title and (folder_year or meaningful_overlap):
                for movie in main_movies:
                    movie.parsed.title = folder_title
                    movie.parsed.year = folder_year or movie.parsed.year

    selected_videos: list[MediaFile] = []
    for item in video_items:
        if item.parsed.is_extra and not include_extras:
            report.ignored.append((item.path, "extra identifié (option --include-extras requise)"))
            continue
        if not item.parsed.title:
            report.ignored.append((item.path, "titre insuffisant ou ambigu"))
            continue
        if only == "movies" and item.parsed.is_series:
            report.ignored.append((item.path, "série exclue par --movies"))
            continue
        if only == "series" and not item.parsed.is_series:
            report.ignored.append((item.path, "film exclu par --series"))
            continue
        selected_videos.append(item)
        target = item.path.with_name(item.parsed.display() + item.path.suffix)
        if target != item.path:
            report.renames.append(Rename(item.path, target, "nom vidéo normalisé"))

    selected_by_dir: dict[Path, list[MediaFile]] = defaultdict(list)
    for item in selected_videos:
        selected_by_dir[item.path.parent].append(item)
    grouped_subs: dict[Path, list[MediaFile]] = defaultdict(list)
    matches: dict[Path, MediaFile] = {}
    for subtitle in subtitle_items:
        match = _match_subtitle(subtitle, selected_by_dir[subtitle.path.parent])
        if match is None:
            report.ignored.append((subtitle.path, "sous-titre sans association certaine"))
        else:
            matches[subtitle.path] = match
            grouped_subs[match.path].append(subtitle)

    for video_path, group in grouped_subs.items():
        video = matches[group[0].path]
        for subtitle in group:
            base = video.parsed.display()
            # A plain subtitle uses the video's base. Recognized language/type
            # markers are always preserved, including SDH for accessibility.
            # Any true duplicate target is rejected later by conflict checks.
            if subtitle.suffixes:
                base += "." + ".".join(subtitle.suffixes)
            target = subtitle.path.with_name(base + subtitle.path.suffix)
            if target != subtitle.path:
                report.renames.append(Rename(subtitle.path, target, "sous-titre associé à la vidéo"))

    # Matroska files may contain embedded subtitle tracks, so only other
    # containers require an external subtitle.  Report the normalized media
    # identity even when the video itself already has a clean filename.
    for video in selected_videos:
        if video.path.suffix.casefold() != ".mkv" and video.path not in grouped_subs:
            report.missing_subtitles.append((video.path, video.parsed.display()))

    _mark_conflicts(report)
    # Related artwork and NFO files are informational in the public app.
    # They are listed only after an explicit opt-in, never by default.
    changed_directories = (
        {rename.source.parent for rename in report.renames if rename.status == "proposed"}
        if include_sidecars
        else set()
    )
    for directory in sorted(changed_directories):
        for path in sorted(directory.iterdir()):
            if path.is_file() and path.suffix.casefold() in SIDECAR_EXTENSIONS:
                report.deletions.append(Deletion(path))
    return report


def _mark_conflicts(report: Report) -> None:
    active = [r for r in report.renames if r.status == "proposed"]
    sources = {r.source.resolve() for r in active}
    destinations: dict[str, list[Rename]] = defaultdict(list)
    for rename in active:
        destinations[str(rename.destination.resolve()).casefold()].append(rename)
    for same_destination in destinations.values():
        if len(same_destination) > 1:
            for rename in same_destination:
                rename.status, rename.detail = "conflict", "plusieurs fichiers visent la même destination"
                report.conflicts.append((rename.source, rename.detail))
    for rename in active:
        if rename.status != "proposed":
            continue
        sibling_case_collision = any(p.name.casefold() == rename.destination.name.casefold() and p.resolve() not in sources for p in rename.destination.parent.iterdir())
        if rename.destination.exists() and rename.destination.resolve() not in sources or sibling_case_collision:
            rename.status, rename.detail = "conflict", "destination existante ou collision de casse"
            report.conflicts.append((rename.source, rename.detail))


def _rollback_paths(paths: list[tuple[Path, Path]]) -> list[str]:
    """Restore current paths to originals using a collision-safe two-phase move."""
    errors: list[str] = []
    staged: list[tuple[Path, Path]] = []
    for current, original in paths:
        if not current.exists():
            continue
        rollback_temp = current.with_name(f".{current.name}.rename-media-rollback-{uuid.uuid4().hex}.tmp")
        try:
            os.replace(current, rollback_temp)
            staged.append((rollback_temp, original))
        except OSError as exc:
            errors.append(f"Impossible de préparer la restauration de {current}: {exc}")
    for rollback_temp, original in staged:
        try:
            if original.exists():
                raise FileExistsError(f"destination de restauration existante: {original}")
            os.replace(rollback_temp, original)
        except OSError as exc:
            errors.append(f"Impossible de restaurer {original}: {exc}")
    return errors


def _destination_is_free(destination: Path) -> bool:
    if destination.exists():
        return False
    return not any(path.name.casefold() == destination.name.casefold() for path in destination.parent.iterdir())


def execute(
    report: Report,
    root: Path,
    history_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Apply a prepared report and write its audit files outside media folders.

    The CLI keeps its historical behavior by omitting ``history_dir``. The
    desktop app passes its private data directory so library folders receive
    only the explicitly approved media-name changes.
    """
    safe = [r for r in report.renames if r.status == "proposed"]
    deletions = list(report.deletions) if safe else []
    # Microseconds keep separate rapid operations from overwriting one another's
    # audit files, which is important when the GUI applies small batches.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = history_dir or root
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / f"rename_log_{stamp}.json"
    undo_path = output_dir / f"rename_undo_{stamp}.json"
    outcomes: list[dict[str, str]] = []
    deletion_outcomes: list[dict[str, str]] = []
    temporary: list[tuple[Rename, Path]] = []
    staged_deletions: list[tuple[Deletion, Path]] = []
    finalized_sources: set[Path] = set()
    try:
        for rename in safe:
            if not rename.source.exists():
                raise FileNotFoundError(f"source disparue depuis la planification: {rename.source}")
            temp = rename.source.with_name(f".{rename.source.name}.rename-media-{uuid.uuid4().hex}.tmp")
            os.replace(rename.source, temp)
            temporary.append((rename, temp))
        for deletion in deletions:
            if not deletion.path.exists():
                deletion.status = "missing"
                deletion.detail = "fichier disparu depuis la planification"
                continue
            temp = deletion.path.with_name(f".{deletion.path.name}.rename-media-delete-{uuid.uuid4().hex}.tmp")
            os.replace(deletion.path, temp)
            staged_deletions.append((deletion, temp))
        for rename, temp in temporary:
            if not _destination_is_free(rename.destination):
                raise FileExistsError(f"destination apparue depuis la planification: {rename.destination}")
            os.replace(temp, rename.destination)
            finalized_sources.add(rename.source)
            rename.status = "renamed"
            outcomes.append({"old_path": str(rename.source), "new_path": str(rename.destination), "status": "renamed", "error": ""})
    except OSError as exc:
        media_to_restore = [
            (rename.destination if rename.source in finalized_sources else temp, rename.source)
            for rename, temp in temporary
        ]
        rollback_errors = _rollback_paths(media_to_restore + [(temp, deletion.path) for deletion, temp in staged_deletions])
        outcomes.append({"old_path": "", "new_path": "", "status": "error", "error": str(exc)})
        if rollback_errors:
            outcomes.extend({"old_path": "", "new_path": "", "status": "rollback_error", "error": error} for error in rollback_errors)
        raise OSError(f"{exc}" + (f"; erreurs de restauration: {'; '.join(rollback_errors)}" if rollback_errors else "")) from exc
    else:
        # Sidecars are removed only after every rename has committed.
        for deletion, temp in staged_deletions:
            try:
                temp.unlink()
                deletion.status = "deleted"
                deletion_outcomes.append({"path": str(deletion.path), "status": "deleted", "error": ""})
            except OSError as exc:
                deletion.status = "error"
                deletion.detail = str(exc)
                try:
                    if not deletion.path.exists():
                        os.replace(temp, deletion.path)
                except OSError as restore_exc:
                    deletion.detail += f"; restauration impossible: {restore_exc}"
                deletion_outcomes.append({"path": str(deletion.path), "status": "error", "error": deletion.detail})
    finally:
        payload = {"created_at": datetime.now(timezone.utc).isoformat(), "operations": outcomes, "deletions": deletion_outcomes}
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        undo_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return log_path, undo_path


def undo(undo_path: Path, scope: Path | None = None) -> tuple[int, list[str]]:
    data = json.loads(undo_path.read_text(encoding="utf-8"))
    operations = [(Path(x["new_path"]), Path(x["old_path"])) for x in data.get("operations", []) if x.get("status") == "renamed"]
    if scope is not None:
        resolved_scope = scope.resolve()
        operations = [
            (source, destination)
            for source, destination in operations
            if destination.resolve().is_relative_to(resolved_scope)
        ]
        if not operations:
            return 0, [f"Aucune opération d'annulation dans le dossier: {resolved_scope}"]
    sources = {source.resolve() for source, _ in operations}
    errors = [f"Conflit: {destination}" for source, destination in operations if not source.exists() or (destination.exists() and destination.resolve() not in sources)]
    if errors:
        return 0, errors
    temporary: list[tuple[Path, Path, Path]] = []
    finalized_sources: set[Path] = set()
    try:
        for source, destination in operations:
            temp = source.with_name(f".{source.name}.rename-media-undo-{uuid.uuid4().hex}.tmp")
            os.replace(source, temp)
            temporary.append((source, temp, destination))
        for source, temp, destination in temporary:
            if not _destination_is_free(destination):
                raise FileExistsError(f"destination apparue pendant l'annulation: {destination}")
            os.replace(temp, destination)
            finalized_sources.add(source)
        return len(operations), []
    except OSError as exc:
        to_restore = [
            (destination if source in finalized_sources else temp, source)
            for source, temp, destination in temporary
        ]
        return 0, [str(exc), *_rollback_paths(to_restore)]


def print_report(report: Report, verbose: bool) -> None:
    for rename in report.renames:
        marker = "PROPOSÉ" if rename.status == "proposed" else "CONFLIT"
        print(f"[{marker}] {rename.source}\n  -> {rename.destination}\n  Raison: {rename.reason}{(': ' + rename.detail) if rename.detail else ''}")
    for path, reason in report.ignored:
        print(f"[IGNORÉ] {path}\n  Raison: {reason}")
    for path, media_name in report.missing_subtitles:
        print(f"[SOUS-TITRES MANQUANTS] {path}\n  Film/épisode: {media_name}\n  Raison: aucun sous-titre externe associé (les fichiers .mkv sont exemptés)")
    for deletion in report.deletions:
        print(f"[SUPPRESSION PROPOSÉE] {deletion.path}\n  Raison: {deletion.reason}")
    print(f"\nRésumé: {report.videos_found} vidéo(s), {report.subtitles_found} sous-titre(s), "
          f"{sum(r.status == 'proposed' for r in report.renames)} renommage(s) proposé(s), "
          f"{len(report.deletions)} suppression(s) proposée(s), {len(report.ignored)} ignoré(s), "
          f"{len(report.conflicts)} conflit(s)/ambiguïté(s), "
          f"{len(report.missing_subtitles)} vidéo(s) sans sous-titres.")


def main(argv: list[str] | None = None) -> int:
    # Import locally to keep the low-level engine usable on its own while both
    # public interfaces share the same validated scan/apply/undo API.
    from . import api as public_api

    # Windows consoles may default to a legacy code page that cannot print
    # Japanese, Korean, or other Unicode media filenames.  Keep reports
    # readable instead of failing partway through a dry-run.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description="Renomme localement vidéos et sous-titres, sans Internet.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="affiche le plan sans modifier de fichier")
    mode.add_argument("--apply", action="store_true", help="exécute seulement les renommages sûrs")
    mode.add_argument("--undo", metavar="FICHIER", help="annule un journal d'annulation")
    parser.add_argument("--undo-scope", type=Path, metavar="DOSSIER", help="limite --undo aux opérations sous ce dossier")
    parser.add_argument("path", nargs="?", default=".", help="dossier à analyser (défaut : .)")
    recursion = parser.add_mutually_exclusive_group()
    recursion.add_argument("--recursive", dest="recursive", action="store_true", default=True)
    recursion.add_argument("--no-recursive", dest="recursive", action="store_false")
    parser.add_argument("--movies", action="store_true")
    parser.add_argument("--series", action="store_true")
    parser.add_argument("--include-extras", action="store_true")
    parser.add_argument(
        "--delete-sidecars",
        action="store_true",
        help="propose related image/NFO deletion (off by default)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    if args.movies and args.series:
        parser.error("--movies et --series ne peuvent pas être utilisés ensemble")
    if args.undo:
        if args.undo_scope:
            count, errors = undo(Path(args.undo), args.undo_scope)
        else:
            undo_result = public_api.undo(Path(args.undo))
            count, errors = undo_result.restored, list(undo_result.errors)
        print(f"Annulation: {count} fichier(s) restauré(s).")
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    if args.undo_scope:
        parser.error("--undo-scope nécessite --undo")
    root = Path(args.path)
    if not root.is_dir():
        parser.error(f"dossier introuvable: {root}")
    try:
        if args.config:
            # Custom configuration is retained as an advanced legacy CLI
            # feature. The standard path below is the shared public API.
            report = build_report(
                root,
                args.recursive,
                "movies" if args.movies else "series" if args.series else None,
                args.include_extras,
                args.config,
                args.delete_sidecars,
            )
            scan_report = public_api.ScanReport(
                public_api.ScanOptions(
                    root.resolve(),
                    recursive=args.recursive,
                    media_type=(
                        public_api.MediaScope.MOVIES
                        if args.movies
                        else public_api.MediaScope.SERIES
                        if args.series
                        else public_api.MediaScope.ALL
                    ),
                    include_extras=args.include_extras,
                    include_sidecars=args.delete_sidecars,
                ),
                report,
            )
        else:
            scan_report = public_api.scan(
                public_api.ScanOptions(
                    root,
                    recursive=args.recursive,
                    media_type=(
                        public_api.MediaScope.MOVIES
                        if args.movies
                        else public_api.MediaScope.SERIES
                        if args.series
                        else public_api.MediaScope.ALL
                    ),
                    include_extras=args.include_extras,
                    include_sidecars=args.delete_sidecars,
                )
            )
            report = scan_report.engine_report
    except (ValueError, NotADirectoryError) as exc:
        parser.error(str(exc))
    print_report(report, args.verbose)
    if args.apply:
        selected = {
            rename.source: rename.destination.name
            for rename in report.renames
            if rename.status == "proposed"
        }
        try:
            result = public_api.apply(
                scan_report,
                selected,
                delete_sidecars=args.delete_sidecars,
                selected_sidecars=(
                    deletion.path for deletion in report.deletions
                ),
                history_dir=root.resolve(),
            )
        except (OSError, public_api.InvalidEdits) as exc:
            print(f"Erreur de renommage: {exc}", file=sys.stderr)
            return 1
        print(
            f"Journal: {result.log_path}\n"
            f"Annulation: {result.history_entry}"
        )
    return 0
