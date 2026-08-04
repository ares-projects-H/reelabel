# Signing roadmap

Reelabel v0.1.0 is unsigned. The project adds checksums and GitHub build
provenance before introducing operating-system publisher certificates. No
signing account, subscription, certificate, or signing secret is currently
required.

## Shared release rules

- Signing material must be stored only in the protected `release-signing`
  GitHub environment, never in the repository or an Actions artifact.
- Fork pull requests must never receive signing credentials.
- Signed builds must come from reviewed source on `main` and the official
  release workflow.
- Signing and notarization verification must finish before an installer is
  uploaded to a GitHub release.
- Enabling a paid service, adding credentials, tagging a version, and
  publishing installers each require an explicit maintainer decision.

## Windows

The selected distribution remains a downloadable GitHub EXE rather than a
Microsoft Store package.

1. Apply to SignPath Foundation for its open-source signing service.
2. If accepted, connect SignPath only to the official GitHub build and sign the
   packaged executables as well as the final Inno Setup installer.
3. Verify every signature and timestamp with Authenticode tooling on Windows.
4. If SignPath declines the project, stop. Azure Artifact Signing is the
   documented fallback, but must not be enabled without approval of its ongoing
   cost and identity-verification requirements.

A valid signature identifies the publisher and detects tampering. It does not
guarantee that Microsoft SmartScreen will immediately trust a newly released
file; reputation can still take time to develop.

Official reference: [Code signing options for Windows app developers](https://learn.microsoft.com/windows/apps/package-and-deploy/code-signing-options).

## macOS

macOS signing remains deferred until the maintainer chooses an Apple Developer
individual or organization identity.

The future workflow will:

1. sign every executable inside `Reelabel.app` with a Developer ID Application
   certificate and Hardened Runtime;
2. build separate Apple Silicon and Intel DMGs;
3. submit each DMG to Apple's notarization service;
4. staple the accepted notarization ticket;
5. verify the application with `codesign`, `spctl`, `stapler`, and `hdiutil`.

Official reference: [Signing Mac Software with Developer ID](https://developer.apple.com/developer-id/).

## Linux

The AppImage and DEB continue to use SHA-256 checksums and GitHub build
provenance. A directly downloaded Linux package has no single publisher-signing
experience shared by every distribution and desktop environment. Reelabel will
not create a GPG key or signed APT repository until there is a concrete need and
a documented key-management process.
