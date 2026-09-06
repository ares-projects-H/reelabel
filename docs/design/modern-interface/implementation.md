# Modern desktop interface — implementation and validation

Branch: `feature/modern-interface`, based on public v0.2.0 (`f85fde2`).
The owner approved the direction in [Validation 1](README.md).
This work is a **0.3.0 test candidate**, not a published release. Early interface
builds displayed 0.2.0; the owner requested a distinct version after macOS validation.
Use the version, commit and build-run manifest to identify the latest candidate.

## User-visible changes

- Compact source panel, one row of filters, filename search, and a larger preview.
- A clearly outlined welcome area accepts a folder anywhere inside it, including
  over its instructions/button. It shares the source panel's validation and busy
  lockout; a drop selects the folder without scanning or modifying it.
- Explicit **Edit name** and F2, while preserving double-click editing and optional
  episode/subtitle propagation. Only proposed rename cells are editable.
- Stable source-path identities under sorting, filtering, editing, and partial selection.
  The selection summary explicitly counts checked rows hidden by a filter.
- Source/option changes clear stale previews and require another scan before Apply.
- Theme-aware dividers, checkbox marks, status text/icons, focus and disabled states.
- Scrollable Settings with bounded media choices and reversible System/Light/Dark
  preview. System appearance follows Qt's OS appearance notifications.
- Separate, unchecked related images/NFO list; permanent deletion retains its own
  confirmation even when ordinary rename confirmations are hidden.
- Clearer history entries and scope-specific Undo confirmation. Malformed, missing,
  or changed history records cannot initiate an unnoticed restoration.
- Background Apply/Undo without interruption, with serialized operations and safe
  shutdown. Scan is cancellable. Updates have separate progress feedback and retain
  both Help and Settings routes; no startup/background checks were added.

## Maintenance boundaries

The GUI now separates workspace layout, preview-table presentation, theme tokens
and system appearance, reusable controls/assets, history display, batch-name
transforms, finite workers, and the update controller. MainWindow coordinates
the existing public `scan`, `validate_edits`, `apply`, and `undo` functions.
No new runtime dependency or framework change was introduced.

Two small API corrections turn invalid path edits into validation issues rather
than exceptions, and reject reserved Windows basenames with multiple extensions.
Per-pass directory indexes replace repeated full listings during collision checks.
They are discarded after each pass; Apply still validates again, and execution
still uses the existing no-overwrite/rollback primitives. The bundled optional
Codex skill has byte-identical API/engine sources, checked by tests.

## Reproducible verification

Local result: **129 passed**, Ruff passed, `git diff --check` passed. The
layout checks also passed at each additional simulated scale (125%, 150%, 200%).
The rebuilt local macOS executable passed the scan/assets/Settings package smoke.
The initial Windows CI run caught construction-time dropdown font measurements.
Choices now refit after final font/style changes while staying bounded, with
regression checks at two font sizes. Superseded candidate builds are not for use.

```sh
ruff check src tests scripts packaging/entrypoint.py
QT_QPA_PLATFORM=offscreen pytest -ra
git diff --check
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.25 pytest tests/test_gui_layout.py
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 pytest tests/test_gui_layout.py
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 pytest tests/test_gui_layout.py
python scripts/capture_modern_ui.py
```

The suite includes real disposable-file GUI Apply → History → Undo, partial
selection after sorting/filtering, folder renames, batch propagation, injected
move failure with rollback, invalid names, per-pass collision freshness, stale
preview ownership, read-only columns, malformed history, live-theme cancellation,
offline startup/settings/scan, update result/error feedback, and subprocess tests
that prove the application exits after Scan, Apply, Undo, Update, or Scan+Update.

Visual checks cover actual production widgets in light/dark at 1024×620 and
1280×820, Settings scrolling, dropdown labels, confirmations, and empty History.
Scale tests simulate Qt scaling; they do not certify every native monitor or
assistive technology. Public screenshots use invented names and no media artwork.

The local macOS Apple Silicon bundle was also opened through native application
control: source selection, preview, theme preview, confirmation, real Apply and
Undo on four temporary files, and closing. User media was not used. Native review
found and prompted a fix for focused history-item layout; automated review found
and fixed shutdown during update and sorting after manual edits.

Installer diagnostics now exercise assets (including bundled SVGs), read-only
scan, and the actual Settings menu action with isolated temporary preferences.
They exit nonzero for missing assets, scan errors, wrong dialogs, exceptions, or
timeout. Explicit checks survive PyInstaller's optimized bytecode. They do not
connect to GitHub or rename media.

## Local performance observation

Single unprofiled passes on this Mac, local temporary files, Qt offscreen:

| 1,000 files in one folder | Before | After |
| --- | ---: | ---: |
| Scan | 1.87 s | 0.09 s |
| Validate selected proposals | 0.95 s | 0.05 s |
| Populate GUI including validation | 0.96 s | 0.12 s |

These are indicative local timings, not performance guarantees for network
shares or other hardware. Tests assert directory-read behavior, not timings.

## Candidate handoff and limits

Prepare a draft PR and run the existing installer workflow on the branch, never
a tag. Confirm all three OS test jobs pass for the candidate commit and that the
workflow's **Publish GitHub release** job is skipped. Keep installers under a
separate commit-named test folder, with SHA-256 sums and build provenance.

The owner must test the exact Windows 10/11 x64 EXE, macOS Apple Silicon DMG and
Ubuntu 24.04 DEB. Intel DMG and AppImage retain automated build/startup checks;
manual testing needs matching hardware/environment. Offscreen runner success is
not proof of native appearance, installer UX, FUSE availability, or OS warnings.
Existing signatures, GitHub security settings, and Sponsors remain unchanged.

No merge, tag, or public release is authorized by this implementation.

## macOS feedback: welcome drop area and version

After the owner validated the macOS interface, they reported that the central
drop instructions did not match the active target (only the top panel accepted
drops). The complete central outline now uses the same DropZone component.
Sixteen new checks cover the center, labels, button, edge and top panel; Unicode
paths; invalid/multiple/file/remote inputs; drag highlighting; busy lockout;
disappearing folders; and compact light/dark geometry. No folder is moved or
copied: the handler selects its path and reports a non-move drag action.

Installer smoke now sends drag/drop events to the actual central widget, then
scans and checks that Settings displays the package's single-source version.
Version 0.3.0 distinguishes this candidate from the published 0.2.0 installers.
