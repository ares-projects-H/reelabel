# First-time user guide

Reelabel's media workflow runs locally on your computer. It does not upload
filenames, search online metadata, modify media contents, or use analytics.

For your first test, use a copied media folder rather than your only copy.

## Menus and Settings

On macOS, open **Reelabel → Settings…** in the menu bar at the top of the
screen. **About Reelabel** and **Quit Reelabel** are in the same application
menu.

On Windows and Linux, open **File → Settings…** in the Reelabel window.
**About Reelabel**, **Check for Updates…**, and the offline user guide are under
**Help**.

Settings can remember:

- System default, Light, or Dark appearance;
- the default media type;
- whether new previews include subfolders;
- whether new previews include extras.

Settings are stored only on the current computer. Related images and NFO files
cannot be enabled by default and remain a deliberate choice for every session.
Reelabel does not check for updates or access the network in the background.
The Settings screen includes the installed version and a **Check for updates**
button. GitHub is contacted only after you click that button.

## 1. Choose a folder

Drag one folder onto the drop area, or choose **Browse**. Reelabel will show a
warning if you click **Preview changes** without first choosing a folder.

The scan options are:

- **All media**: include recognized movies and series.
- **Movies only**: ignore recognized series.
- **Series only**: ignore recognized movies.
- **Include subfolders**: scan inside folders below the selected folder.
- **Include extras**: include recognized trailers, samples, and other extras.

Choosing a folder and previewing it does not rename anything.

## 2. Read the preview

Each row contains:

- **Include**: checked rows will be included if you apply the preview.
- **Status**: `Ready`, `Review`, `Ignored`, or `Related`.
- **Original name**: the current filename or folder name.
- **Proposed name**: Reelabel's editable suggestion.
- **Type**: the file type, such as MKV, SRT, ASS, or FOLDER.

Use the `All`, `Ready`, `Review`, and `Ignored` buttons to filter the rows.
Drag a divider between column headings to change a column's width. Click a text
column heading once for ascending order and again for descending order.

## 3. Review and edit suggestions

Double-click a cell in the **Proposed name** column to edit it, then press
Enter.

When you correct a series title or season pattern, Reelabel can offer to update
the other episodes in that folder while keeping their episode numbers. When you
correct a movie title, it can offer to update related subtitles while keeping
language markers and extensions.

Nothing is changed automatically when this question appears. You can decline
the batch edit or review and edit every updated row afterward.

Rows marked **Review** need attention and are not applied until their problem
is resolved. Reelabel rejects invalid Windows names, path escapes, existing
destinations, case collisions, and extension changes.

## 4. Apply selected changes

Uncheck any row you do not want to apply. Choose **Apply selected changes**,
read the confirmation, and approve it only if the counts are correct. Select
**Don't show again** if you no longer need this rename reminder.
You can restore it later with **Show confirmation before applying selected
changes** in Reelabel Settings.

Reelabel applies a validated group of renames as one operation. If part of the
operation fails, it restores items already moved instead of leaving a partial
result. It never overwrites an existing file. These protections remain active
when the rename confirmation is hidden.

## 5. Restore names with History / Undo

Every successful operation creates a History / Undo entry in Reelabel's
application-data folder. Open **History / Undo**, select an available entry,
and restore it. **Undo selected** remains disabled until a restorable entry is
selected.

Undo refuses to overwrite a file that appeared after the original operation.

## Related images and NFO files

**Show related images / NFO** is off by default. When enabled, related files
appear separately and remain unchecked. Deleting selected related files
requires a second confirmation, with **Cancel** as its default action.

## Application menus and Settings

On macOS, application commands appear in the system menu bar at the top of the
screen:

- **Reelabel → Preferences…** opens the Reelabel Settings screen.
- **Reelabel → About Reelabel** shows the version, license, and privacy summary.
- **Reelabel → Quit Reelabel** safely closes the application.
- **File** contains Choose Folder, Preview Changes, and History / Undo.
- **Help → Reelabel User Guide** opens a concise offline guide.
- **Help → Check for Updates…** performs one manual check against the official
  GitHub release. It never downloads or installs anything automatically.

On Windows and Linux, these commands appear in the Reelabel window's menu bar.

Settings are stored only on the current computer. You can choose System
default, Light, or Dark appearance and set default media type, subfolder, and
extras options. You can also restore the rename confirmation after
choosing **Don't show again**. Related image/NFO discovery cannot be enabled as
a saved default, and its permanent-deletion confirmation cannot be disabled.

## Check for updates

Choose **Help → Check for Updates…**, or use the button in Settings. Reelabel
will show whether a newer public release is available. If one is available,
**Open download page** opens the verified official GitHub release in your
default browser.

This is Reelabel's only optional network operation. It sends the installed
version but no filenames, media paths, settings, or history. A failed check does
not affect scanning or renaming, which remain fully available offline. See
[PRIVACY.md](../PRIVACY.md) for details.

## Getting help

Before reporting a problem:

1. Confirm that you are using the latest Reelabel test or release.
2. Reproduce the problem with copied or disposable files.
3. Replace private filenames and paths with invented examples.
4. Open a GitHub bug report and include the operating system, Reelabel version,
   expected behavior, actual behavior, and safe reproduction steps.

Never post a security vulnerability publicly. Follow [SECURITY.md](../SECURITY.md)
instead.
