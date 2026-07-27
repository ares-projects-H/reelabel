"""Allow ``python -m media_renamer`` to launch the command-line interface."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())

