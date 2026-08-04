# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest published release | Yes |
| Older releases | No |
| Unofficial forks or modified builds | No |

## System and scope

Reelabel is a local desktop and command-line application that previews and
renames media files and their containing folders. This policy covers the rename
engine, GUI, CLI, History / Undo records, manual update check, packaging code,
and official GitHub Actions workflows.

The media workflow does not require a network connection. The only application
network request is a user-triggered check of the official GitHub release. The
application does not download or execute an update.

## Threat model and trust boundaries

Treat media filenames, directory names, subtitle names, symbolic links,
filesystem changes made after a preview, imported history records, GitHub API
responses, pull requests, and build inputs as untrusted.

The selected media folder is the authorization boundary for scan, apply, and
undo operations. GitHub Actions and the protected `release-signing` environment
are the boundary for official release artifacts and any future signing
credentials.

## Security invariants

- A rename or undo operation must not read, move, delete, or restore an item
  outside its explicitly authorized folder scope.
- Reelabel must never overwrite an existing file or silently accept a
  case-insensitive collision.
- Every apply operation must revalidate the preview and restore already staged
  renames if the operation cannot finish safely.
- Media contents and file extensions must not be modified by a rename.
- Image and NFO deletion must remain unchecked by default, explicitly selected,
  and protected by a separate confirmation that cannot be disabled.
- History / Undo must reject untrusted locations, path escapes, and destinations
  that appeared after the original operation.
- No network request may occur at startup, during a scan, or in the background.
  The manual update check must accept only the official HTTPS Reelabel release
  URL and must never download or execute an installer.
- Fork pull requests and unreviewed code must not receive release or signing
  credentials.

## Reportable findings and severity context

Security reports are especially useful when they concern:

- unintended overwrite, deletion, or movement outside the selected folder;
- arbitrary code execution through a filename, configuration, history record,
  update response, or build workflow;
- bypass of validation, rollback, explicit selection, or confirmation controls;
- exposure of private filenames, paths, release credentials, or future signing
  material;
- a background or undisclosed network request;
- acceptance or opening of an untrusted update URL.

Issues that allow arbitrary code execution, broad unintended deletion, or theft
of release credentials generally have higher impact than a denial of service or
a safely rejected rename.

## Out of scope and known limitations

- Incorrect or unattractive rename suggestions without a security impact should
  use the normal bug-report template.
- Operating-system warnings caused solely by the currently unsigned installers
  are a documented release limitation, not a vulnerability by themselves.
- Unofficial forks and modified builds are not supported by this project.

Current releases use SHA-256 checksums. Releases starting with v0.2.0 also use
GitHub build-provenance attestations. Publisher signing for Windows and macOS is
planned but is not currently enabled.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Include the affected version, operating system, safe reproduction steps,
   expected behavior, actual behavior, and likely impact.

Do not include personal media filenames unless they are necessary and safe to
share. You should receive an acknowledgement within seven days. Please allow
time for investigation, a fix, and a coordinated release before disclosure.
