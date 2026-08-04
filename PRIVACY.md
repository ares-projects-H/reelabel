# Privacy

Reelabel is designed to rename local media without collecting information about
its users or their libraries.

## Local data

Scans, previews, renames, and History / Undo operations run on the current
computer. Reelabel does not upload filenames, folder paths, media contents,
settings, or history entries.

The application stores only its preferences and rename history in the normal
application-data location provided by the operating system. This information
is not sent anywhere.

## Manual update check

Reelabel does not connect to the Internet at startup or in the background. It
contacts GitHub only after the user chooses **Check for Updates**.

That action sends one HTTPS request to the official Reelabel releases API. The
request identifies the installed Reelabel version through its User-Agent, but
does not include media filenames, paths, settings, or history. GitHub may
process standard connection information such as the user's IP address under
GitHub's own privacy terms.

Reelabel validates the returned release link and never downloads or installs
an update automatically. Opening the download page always requires a separate
user action and uses the computer's default web browser.

## Analytics and advertising

Reelabel contains no analytics, telemetry, advertising, tracking pixels, or
background update service.

Questions about this policy can be opened as a normal GitHub issue. Security
or privacy vulnerabilities should be reported privately as described in
[SECURITY.md](SECURITY.md).
