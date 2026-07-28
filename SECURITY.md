# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest published release | Yes |
| Older releases | No |
| Unofficial forks or modified builds | No |

## Reporting a vulnerability

Do not open a public issue for a vulnerability that could cause unintended
file deletion, overwrite, path escape, or arbitrary code execution.

Use GitHub's private vulnerability reporting after it is enabled for the public
`ares-projects-H/reelabel` repository:

1. Open the repository's **Security and quality** tab.
2. Choose **Report a vulnerability**.

Include the affected version, operating system, reproduction steps, expected
behavior, and impact. Do not include personal media filenames unless they are
necessary and safe to share.

You should receive an acknowledgement within seven days. Please allow time for
a fix and coordinated release before public disclosure.

If the private reporting button is not available, open a public issue asking
for a private contact method without including any vulnerability details.

## Scope

Security reports are especially useful when they concern:

- overwriting or deleting a file without explicit approval;
- escaping the selected media folder;
- executing code through a filename, configuration, or history file;
- leaking private filenames or paths;
- bypassing validation, rollback, or History / Undo.

Incorrect rename suggestions without a security impact should use the normal
bug-report template.
