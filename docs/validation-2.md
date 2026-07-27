# Validation 2 — Functional alpha

This checkpoint connects the approved interface to the local rename engine.
The source build is ready for controlled testing on copies of real media
folders. Standalone installers are intentionally deferred to validation 3.

![Media Renamer functional alpha](screenshots/interface-alpha.png)

## What now works

- Choose or drop a media folder and run a read-only scan.
- Cancel a long scan without changing files.
- Filter the table with All, Ready, Review, and Ignored.
- Uncheck individual proposals or edit a proposed filename.
- Revalidate edits for unsupported Windows characters, reserved names,
  changed extensions, existing destinations, case collisions, duplicate
  destinations, and missing source files.
- Apply selected valid renames as one transaction.
- Restore renamed files from History / Undo when their original paths are free.
- Optionally show related image/NFO files. They remain unchecked by default and
  require a separate permanent-deletion confirmation.

## Suggested validation

Always begin with a copied test folder.

1. Open the app and choose the copied folder.
2. Select the correct media type and click **Preview changes**.
3. Click each status filter and confirm that only matching rows remain visible.
4. Uncheck one Ready row and edit another proposed name.
5. Click **Apply selected changes** and verify only checked files changed.
6. Open **History / Undo**, select the latest entry, and restore it.
7. Run a second preview and confirm the original filenames returned.

## Current boundary

This is still a source build. It requires Python and PySide6 on the development
machine. Validation 3 will create standalone packages so end users do not need
Python or Codex.
