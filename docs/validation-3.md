# Validation 3 — Installers and publication

This checkpoint packages Reelabel as a standalone application and records the
validation completed for the public version 0.1.0 release built by GitHub
Actions.

## Deliverables

- Windows 10/11 x64 installer EXE.
- Separate macOS DMGs for Apple Silicon and Intel.
- Ubuntu 24.04 x86_64 DEB package.
- Portable Linux x86_64 AppImage.
- SHA-256 checksums for every download.
- Automated tests on Windows, macOS, and Linux.
- Packaged-application startup tests on every build platform.
- Release artifacts and public release notes.

## Application icon

The source launcher sets the icon on both Qt's application object and the
native main window. Packaged builds also embed:

- `reelabel-icon.ico` in Windows executables and the installer;
- `reelabel-icon.icns` in the macOS application bundle;
- `reelabel-icon.png` in both Linux packages.

## Signing status

Version 0.1.0 is unsigned. This is expected for the first public release and may
trigger Windows SmartScreen or macOS Gatekeeper. The release provides SHA-256
checksums and documents the warning instead of bypassing operating-system
security.

## Validation status

The owner has validated the private packages on:

- macOS Apple Silicon;
- Windows 11 x64;
- Ubuntu 24.04 x86_64 using the recommended DEB package.

The AppImage and separate macOS Intel package were built and smoke-tested
automatically, but were not manually confirmed because matching test hardware
was unavailable. For future releases, repeat this short final check on freshly
built packages whenever the required systems are available:

1. Install and start the application without Python or Codex.
2. Confirm the application logo appears in the Dock, taskbar, or application
   menu.
3. Preview, edit, and apply a small selection.
4. Confirm a containing-folder rename.
5. Restore the operation from History / Undo.
