# Installation

Reelabel works entirely offline after installation. It does not require
Python, Codex, an account, or a metadata service.

## Verify a download

Every release includes `SHA256SUMS.txt`. Compare its value with the downloaded
file before opening the installer.

On Windows PowerShell:

```powershell
Get-FileHash .\Reelabel-0.1.0-Windows-x64-Setup.exe -Algorithm SHA256
```

On macOS:

```bash
shasum -a 256 Reelabel-0.1.0-macOS-arm64.dmg
```

On Linux:

```bash
sha256sum Reelabel-0.1.0-Linux-x86_64.AppImage
```

## Windows 10/11 x64

1. Download `Reelabel-0.1.0-Windows-x64-Setup.exe`.
2. Open the installer and choose whether to create a desktop shortcut.
3. Launch **Reelabel** from the Start menu.

The first installer is unsigned. Windows SmartScreen may display **Windows
protected your PC**. Verify the SHA-256 value first, then use **More info** and
**Run anyway** only if the file came from the official GitHub release.

To uninstall it, open **Settings → Apps → Installed apps**, find **Reelabel**,
open its menu, and choose **Uninstall**.

## macOS Apple Silicon or Intel

1. Download the DMG matching your Mac:
   - `arm64` for Apple Silicon;
   - `x86_64` for Intel.
2. Open the DMG and drag **Reelabel** into **Applications**.
3. Open Reelabel from Applications.

The first application is unsigned. If macOS blocks the first launch, verify the
SHA-256 value, Control-click the app in Finder, choose **Open**, then confirm
**Open**. You only need this approval once.

To uninstall it, quit Reelabel and move **Reelabel** from **Applications** to
the Trash.

## Ubuntu 24.04 LTS x86_64

The DEB package is the easiest option on Ubuntu:

1. Download `Reelabel-0.1.0-Ubuntu-24.04-x86_64.deb`.
2. Double-click the downloaded file.
3. Choose **Install** in Ubuntu App Center.
4. Open **Reelabel** from the application menu.

You can also install it from a terminal:

```bash
sudo apt install ./Reelabel-0.1.0-Ubuntu-24.04-x86_64.deb
```

To uninstall the Ubuntu package:

```bash
sudo apt remove reelabel
```

Use `sudo apt purge reelabel` instead if you also want Ubuntu to remove
package-managed configuration. Personal History / Undo data is kept separately
to avoid silently removing recovery information.

## Portable AppImage for Linux x86_64

1. Download `Reelabel-0.1.0-Linux-x86_64.AppImage`.
2. An AppImage is a portable application rather than a traditional installer.
   Before the first launch, right-click it, open **Properties**, choose
   **Permissions**, and enable **Allow executing file as program**.
3. Double-click the AppImage to start Reelabel.

The equivalent terminal commands are:

```bash
chmod +x Reelabel-0.1.0-Linux-x86_64.AppImage
./Reelabel-0.1.0-Linux-x86_64.AppImage
```

If Ubuntu 24.04 reports a FUSE error, install its FUSE 2 compatibility library:

```bash
sudo apt install libfuse2t64
```

If FUSE cannot be installed, use the AppImage runtime's fallback:

```bash
./Reelabel-0.1.0-Linux-x86_64.AppImage --appimage-extract-and-run
```

An AppImage is not installed system-wide. To remove it, close Reelabel and
delete the downloaded `.AppImage` file.

## First safe test

For your first test, copy a small media folder so the original files remain
untouched.

1. Open Reelabel.
2. Drag the copied folder into the window, or click **Browse**.
3. Choose the media type and click **Preview changes**. Previewing does not
   rename anything.
4. Review every proposed change. Uncheck a row to exclude it.
5. To correct a name, double-click its cell in the **Proposed name** column,
   type the correction, and press Enter.
6. Drag a column divider to change its width, or click a text-column heading to
   switch between ascending and descending order.
7. Click **Apply selected changes** only after checking the complete preview.
8. Open **History / Undo** and restore the operation to confirm that undo works.

Related images and NFO files stay unchecked unless you select them explicitly.
