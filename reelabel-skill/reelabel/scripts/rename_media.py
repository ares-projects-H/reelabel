#!/usr/bin/env python3
"""Rename video files and matching subtitles conservatively.

Use --dry-run first.  This program never needs network access and never
changes media contents; --apply only renames files that passed all checks.
"""

from reelabel.core import main

if __name__ == "__main__":
    raise SystemExit(main())
