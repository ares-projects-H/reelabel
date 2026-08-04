# Safe GitHub maintenance guide

This guide explains how to accept community contributions without giving
unknown contributors control of the official application.

## What contributors can and cannot do

A contributor can create an issue, fork the public repository, change their
fork, and propose those changes in a pull request.

A pull request does **not** change the official repository by itself. Only a
maintainer with permission can approve and merge it. Contributors also cannot
publish an official Reelabel release unless the owner grants that permission.

## Safe pull-request workflow

For every pull request:

1. Read the description and inspect **Files changed** before running anything.
2. Reject unrelated binaries, media files, secrets, unexplained generated
   files, or changes to release permissions.
3. Check changes to `.github/workflows` especially carefully.
4. Confirm that safety tests were added for rename-engine changes.
5. Wait for Windows, macOS, and Ubuntu checks to pass.
6. Test risky filesystem behavior only with copied files or in a disposable VM.
7. Merge only when the source, tests, and user-visible behavior are understood.

Do not run an executable supplied by a contributor. Build from reviewed source
using the official GitHub Actions workflow.

## Protecting GitHub credentials

- Never paste a password, token, recovery code, tax document, or bank detail
  into an issue, pull request, repository file, or Actions log.
- Keep two-factor authentication enabled.
- Give collaborators the lowest permission they need.
- Remove access when it is no longer required.
- Treat requests to disable security checks or expose Actions secrets as
  suspicious.

Fork pull requests should not receive repository secrets. Avoid workflow
designs that run unreviewed fork code with elevated repository permissions.

## Repository protections

Keep the free protections for this public repository enabled:

- Dependabot alerts;
- secret scanning and push protection;
- private vulnerability reporting.

Protect `main` so normal changes require a pull request and the Windows, macOS,
and Ubuntu checks. The repository owner may retain a documented emergency
bypass, but routine changes must use the pull-request workflow.

The empty `release-signing` environment reserves a protected boundary for
future signing credentials. Do not add a certificate or subscription until the
owner explicitly approves the relevant signing plan.

## Official releases

Official installers should be produced only by the committed
`.github/workflows/release.yml` workflow from a reviewed `main` commit or
version tag.

Before publishing:

1. Confirm all platform jobs passed.
2. Download and test the installers on copied media folders.
3. Verify SHA-256 checksums.
4. Verify each installer's GitHub attestation with:

   ```bash
   gh attestation verify PATH/TO/INSTALLER \
     --repo ares-projects-H/reelabel
   ```

5. Review release notes and installation instructions.
6. Publish only the files produced by the successful workflow.

Unsigned installers can trigger operating-system warnings. Do not suggest
disabling system security; explain verification and the normal one-time
approval instead. Follow the [signing roadmap](signing-roadmap.md) before
introducing any certificate or signing secret.
