# Installation

Media Renamer works entirely offline after installation. It does not require
Python, Codex, an account, or a metadata service.

## Verify a download

Every release includes `SHA256SUMS.txt`. Compare its value with the downloaded
file before opening the installer.

On Windows PowerShell:

```powershell
Get-FileHash .\Media-Renamer-0.1.0-Windows-x64-Setup.exe -Algorithm SHA256
```

On macOS:

```bash
shasum -a 256 Media-Renamer-0.1.0-macOS-arm64.dmg
```

On Linux:

```bash
sha256sum Media-Renamer-0.1.0-Linux-x86_64.AppImage
```

## Windows 10/11 x64

1. Download `Media-Renamer-0.1.0-Windows-x64-Setup.exe`.
2. Open the installer and choose whether to create a desktop shortcut.
3. Launch **Media Renamer** from the Start menu.

The first installer is unsigned. Windows SmartScreen may display **Windows
protected your PC**. Verify the SHA-256 value first, then use **More info** and
**Run anyway** only if the file came from the official GitHub release.

## macOS Apple Silicon or Intel

1. Download the DMG matching your Mac:
   - `arm64` for Apple Silicon;
   - `x86_64` for Intel.
2. Open the DMG and drag **Media Renamer** into **Applications**.
3. Open Media Renamer from Applications.

The first application is unsigned. If macOS blocks the first launch, verify the
SHA-256 value, Control-click the app in Finder, choose **Open**, then confirm
**Open**. You only need this approval once.

## Linux x86_64

1. Download `Media-Renamer-0.1.0-Linux-x86_64.AppImage`.
2. Make it executable:

   ```bash
   chmod +x Media-Renamer-0.1.0-Linux-x86_64.AppImage
   ```

3. Run it:

   ```bash
   ./Media-Renamer-0.1.0-Linux-x86_64.AppImage
   ```

Some distributions require FUSE 2 compatibility to run AppImages.

## First safe test

For your first test, copy a small media folder so the original files remain
untouched.

1. Open Media Renamer.
2. Drag the copied folder into the window, or click **Browse**.
3. Choose the media type and click **Preview changes**. Previewing does not
   rename anything.
4. Review every proposed change. Uncheck a row to exclude it.
5. To correct a name, double-click its cell in the **Proposed name** column,
   type the correction, and press Enter.
6. Click **Apply selected changes** only after checking the complete preview.
7. Open **History / Undo** and restore the operation to confirm that undo works.

Related images and NFO files stay unchecked unless you select them explicitly.
