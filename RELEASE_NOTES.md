# Reelabel v0.1.0

First public release of the offline Reelabel desktop application.

## Highlights

- Preview and edit movie, series, subtitle, and containing-folder rename proposals.
- Resize preview columns and sort text columns in ascending or descending order.
- Apply only checked changes, with collision checks and automatic restoration on failure.
- Propagate a corrected title or season pattern to other episodes in the same folder.
- Propagate a corrected movie title to its related subtitle files after confirmation.
- Restore file and folder names from History / Undo.
- Require an explicit media-folder scope for command-line Undo and reject
  inconsistent or out-of-scope history records.
- Escape terminal control characters in untrusted filenames.
- Run entirely offline with no analytics or metadata lookups.

## Downloads

- **Windows 10/11 x64:** `Reelabel-0.1.0-Windows-x64-Setup.exe`
- **macOS Apple Silicon:** `Reelabel-0.1.0-macOS-arm64.dmg`
- **macOS Intel:** `Reelabel-0.1.0-macOS-x86_64.dmg`
- **Ubuntu 24.04 x86_64:** `Reelabel-0.1.0-Ubuntu-24.04-x86_64.deb`
- **Other Linux x86_64:** `Reelabel-0.1.0-Linux-x86_64.AppImage`

These first installers are unsigned. Windows SmartScreen or macOS Gatekeeper
may show a warning. Verify the matching SHA-256 value in `SHA256SUMS.txt`
before opening a download.
