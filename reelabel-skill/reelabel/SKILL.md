---
name: reelabel
description: Safely rename local video and subtitle files with the bundled Reelabel script. Use when a user asks to clean, standardize, preview, apply, undo, or report missing subtitles for media files and folders.
---

# Reelabel

Use the bundled local script at `scripts/rename_media.py`. It has no network or media-content dependency and supports Unicode paths on Windows, macOS, and Linux.

## Workflow

1. Always run a dry-run first unless the user explicitly provides `--apply` or clearly authorizes execution.
2. Run `python scripts/rename_media.py --dry-run "<folder>"` and report proposed renames, ignored files, conflicts, and missing external subtitles.
3. Run `--apply` only when explicitly authorized. It renames only safe files and creates `rename_log_*.json` plus `rename_undo_*.json` in the selected root. Image/NFO sidecars remain untouched unless `--delete-sidecars` is also provided explicitly.
4. Use `python scripts/rename_media.py --undo "<undo-json>"` to undo an apply operation without overwriting existing files.

## Commands

```text
python scripts/rename_media.py --dry-run "<folder>"
python scripts/rename_media.py --apply "<folder>"
python scripts/rename_media.py --undo "<undo-json>"
```

Options: `--no-recursive`, `--movies`, `--series`, `--include-extras`, `--delete-sidecars`, `--verbose`, `--config <json>`.

## Safety

- Never run `--apply` from a vague request.
- Never add `--delete-sidecars` unless the user explicitly requests deletion.
- Do not alter folders, extensions, media contents, or unrelated files.
- Do not force or manually resolve conflicts; report them.
- Do not use Internet metadata.
- Preserve subtitle-language/type suffixes and pair `.idx` with `.sub`.
