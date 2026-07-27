# Contributing to Media Renamer

Thank you for helping improve Media Renamer. The project favors conservative,
explainable filename changes over aggressive guessing.

## Before opening a change

- Search existing issues to avoid duplicate work.
- Use an issue for behavior changes that could rename files differently.
- Never add network metadata lookup, analytics, or media-content modification
  without prior project discussion.
- Keep the public interface and documentation in English.

## Development setup

Media Renamer requires Python 3.10 or newer for source development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,build]"
```

On Windows, activate with `.venv\Scripts\activate`.

Run the checks:

```bash
ruff check src tests scripts packaging/entrypoint.py
QT_QPA_PLATFORM=offscreen pytest
```

## Code expectations

- Add regression tests for every rename rule or safety change.
- Preserve extensions and never overwrite existing files.
- Keep images/NFO unchecked by default.
- Add English comments or docstrings for non-obvious rules, safety mechanisms,
  and public APIs.
- Keep GUI and command-line behavior on the shared public API.

## Pull requests

Describe what changed, why it is safe, representative before/after filenames,
and the checks you ran. Keep unrelated changes in separate pull requests.

By contributing, you agree that your contribution is provided under the MIT
License included in this repository.
