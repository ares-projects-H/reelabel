# Contributing to Reelabel

Thank you for helping improve Reelabel. The project favors conservative,
explainable filename changes over aggressive guessing.

You do not need direct access to the repository to contribute. GitHub reviews
changes through a **pull request** before they can become part of the project.
The project owner decides whether each pull request is accepted.

## Your first contribution

If this is your first GitHub contribution, these terms may help:

- A **fork** is your own copy of the repository on GitHub.
- A **branch** is a separate workspace for one change.
- A **pull request** asks the project owner to review your branch. It does not
  change the official project automatically.

The usual workflow is:

1. Open an issue describing the bug or improvement.
2. Fork the repository on GitHub.
3. Clone your fork to your computer.
4. Create a branch for one focused change.
5. Make the change and add or update tests.
6. Run the checks described below.
7. Push your branch to your fork.
8. Open a pull request and explain what you changed.

## Before opening a change

- Search existing issues to avoid duplicate work.
- Use an issue for behavior changes that could rename files differently.
- Never add network metadata lookup, analytics, or media-content modification
  without prior project discussion.
- Keep the public interface and documentation in English.
- Use invented media titles in tests, examples, and screenshots. Do not include
  personal media libraries, copyrighted artwork, or media files.

## Development setup

Reelabel requires Python 3.10 or newer for source development:

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
and the checks you ran. Use invented filenames in public examples. Keep
unrelated changes in separate pull requests.

Opening a pull request does not give a contributor permission to publish a
release or write directly to the official repository. Every change is reviewed
before it is merged.

By contributing, you agree that your contribution is provided under the
[GNU General Public License v3.0 or later](LICENSE) used by this repository.
