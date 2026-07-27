# Media Renamer

Media Renamer is a safe, offline desktop utility for cleaning movie, series,
and subtitle filenames. It always previews proposed changes first, preserves
media contents and folders, and refuses ambiguous or conflicting operations.

> Current milestone: interface validation. The desktop Apply button is
> intentionally disabled until the functional alpha is reviewed.

## Interface preview

![Media Renamer interface preview](docs/screenshots/interface-preview.png)

The first prototype includes:

- folder selection and drag-and-drop;
- movie, series, recursion, and extras options;
- an editable before/after preview table;
- Ready, Review, and Ignored filters;
- related image/NFO deletion disabled by default;
- a clearly disabled Apply action during the visual validation milestone.

## Run from source

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
media-renamer-gui
```

On Windows, activate the environment with `.venv\Scripts\activate`.

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
- No folder renaming.
- No overwriting existing files.
- No automatic image/NFO deletion.
- Conflicts and uncertain subtitle matches are reported instead of guessed.

## License

Media Renamer is available under the [MIT License](LICENSE).

