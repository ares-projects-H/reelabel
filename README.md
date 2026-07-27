# Media Renamer

Media Renamer is a safe, offline desktop utility for cleaning movie, series,
subtitle filenames, and their containing release folders. It always previews
proposed changes first, preserves media contents, and refuses ambiguous or
conflicting operations.

> Current milestone: functional alpha (validation 2). Use a copy of your media
> while testing this development version.

## Interface preview

![Media Renamer functional alpha](docs/screenshots/interface-alpha.png)

The functional alpha includes:

- folder selection and drag-and-drop;
- movie, series, recursion, and extras options;
- a cancellable background scan;
- an editable before/after preview with working Ready, Review, and Ignored filters;
- editable folder-name proposals for movies, series, and other media collections;
- optional same-folder propagation after correcting a title or season pattern
  in one episode proposal;
- cross-platform filename, extension, path, and collision validation;
- partial selection and all-or-nothing rename application;
- app-data history with safe Undo;
- related image/NFO deletion shown only when requested, unchecked by default,
  and protected by a second confirmation.

## Run from source

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
media-renamer-gui
```

On Windows, activate the environment with `.venv\Scripts\activate`.
The source version still needs Python; the standalone installers are planned
for validation 3.

## Command line

The original conservative command-line workflow is retained:

```bash
media-renamer --dry-run "/path/to/media"
media-renamer --apply "/path/to/media"
media-renamer --undo "/path/to/rename_undo_TIMESTAMP.json"
```

Related images and NFO files are never proposed unless
`--delete-sidecars` is passed explicitly.

## Safety principles

- No Internet access or analytics.
- No media content changes.
- Folder renames are always previewed, editable, and individually selectable.
- No overwriting existing files.
- No automatic image/NFO deletion.
- Conflicts and uncertain subtitle matches are reported instead of guessed.
- An apply failure triggers automatic restoration of already staged renames.

## Project checkpoints

- [Validation 1 — interface prototype](docs/validation-1.md)
- [Validation 2 — functional alpha](docs/validation-2.md)
- Validation 3 — Windows 10/11 x64 EXE, macOS DMGs, Linux AppImage, and
  GitHub release (not started yet)

## License

Media Renamer is available under the [MIT License](LICENSE).
