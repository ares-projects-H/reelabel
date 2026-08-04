# Reelabel v0.2.0

Second feature release of the privacy-focused Reelabel desktop application.

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
- Check for a newer official GitHub release only after an explicit click in
  Help or Settings, without downloading or installing anything automatically.
- Keep scans, previews, renames, History / Undo, and command-line operations
  fully offline with no analytics, telemetry, or metadata lookups.
- Use one application-version source across the interface and every installer.
- Publish GitHub build-provenance attestations alongside SHA-256 checksums.
- Document the privacy boundary, security invariants, and future publisher
  signing roadmap.

## Downloads

- **Windows 10/11 x64:** `Reelabel-0.2.0-Windows-x64-Setup.exe`
- **macOS Apple Silicon:** `Reelabel-0.2.0-macOS-arm64.dmg`
- **macOS Intel:** `Reelabel-0.2.0-macOS-x86_64.dmg`
- **Ubuntu 24.04 x86_64:** `Reelabel-0.2.0-Ubuntu-24.04-x86_64.deb`
- **Other Linux x86_64:** `Reelabel-0.2.0-Linux-x86_64.AppImage`

These installers remain unsigned. Windows SmartScreen or macOS Gatekeeper
may show a warning. Verify the matching SHA-256 value in `SHA256SUMS.txt`
and the GitHub attestation before opening a download.
