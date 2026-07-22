# Apple Design multi-scope updater

## Intent

Make `medking82/skills@main/skills/apple-design` the canonical source for the user-scoped
Codex and Claude installations on each workstation. Provide a deterministic check/apply
workflow and an optional Windows scheduled check so the installed snapshots do not drift
silently.

## Context map

- Entry points: `sync-apple-design.ps1` owns the Check/Apply engine;
  `invoke-apple-design-update.ps1` is the scheduled/logging wrapper; and
  `install-apple-design-update-task.ps1` only previews or registers the check-only task.
- Canonical state: the complete `skills/apple-design/` directory from `medking82/skills@main`.
- Consumers:
  - `$HOME/.codex/skills/apple-design`
  - `$HOME/.claude/skills/apple-design`
- Current state: both consumers are independent downloaded snapshots. Updating the GitHub fork
  does not update either consumer or another device.
- Transport: download the public fork archive over HTTPS, extract to a temporary directory, and
  validate the skill before comparing or applying it.
- Operational surface: an optional per-user Windows Scheduled Task runs check-only every day at
  06:30 local time, with `StartWhenAvailable` enabled. Each device must bootstrap the checkout and
  task independently.
- Rollback: apply stages complete replacement directories first, retains both previous directories
  until both swaps and post-write verification succeed, and restores them if a swap or verification
  fails.

## Required behavior

1. `Check` compares a deterministic relative-path/SHA-256 manifest for the complete canonical
   skill directory against both installed scopes. It performs no installation writes and reports
   the canonical manifest SHA-256 plus current, missing, or drifted status for each scope.
2. `Apply` downloads and validates the source before touching either destination, stages a complete
   copy for both scopes, and requires `-ExpectedSourceSha256` to match the canonical manifest digest
   reported by `Check`. It replaces both installations as one rollback-capable transaction, verifies
   both manifests, then removes backups. A missing or mismatched expected digest performs zero
   destination writes.
3. Validation requires a regular `SKILL.md` whose frontmatter declares `name: apple-design`.
   Reject symlinks/reparse points in either source or an existing destination tree, unsafe relative
   paths, empty downloads, and destination roots that resolve outside the requested skill roots.
4. Scheduled installation is preview-first and registers a per-user, check-only task. It must never
   schedule `Apply` or silently overwrite local edits.
5. Exit codes are stable: `0` means current or successfully applied, `3` means check detected drift,
   and other non-zero codes mean operational failure.
6. README instructions cover first-device and additional-device bootstrap, manual apply, scheduled
   check, log location, and the fact that upstream-to-fork sync remains separate.

## Allowed changes

- `.peer-review/config.json`
- `README.md`
- `docs/plans/apple-design-multiscope-updater.md`
- `scripts/sync-apple-design.ps1`
- `scripts/invoke-apple-design-update.ps1`
- `scripts/install-apple-design-update-task.ps1`
- `tests/test-apple-design-updater.ps1`

## Non-goals and do-not-touch boundaries

- Do not modify any skill content, Johorindustry/JBFactory files, user-installed skill directories
  during implementation, or the upstream `emilkowalski/skills` repository.
- Do not automatically sync the GitHub fork from upstream.
- Do not create symlinks/junctions or require administrator privileges.
- Do not add background auto-apply, retry loops, plugin updates, deployment, or rollback commands.
- Do not generalize this into an updater for every skill.

## Verification

- Run `tests/test-apple-design-updater.ps1` against temporary source and destination roots.
- Cover missing installs, check-only zero-write behavior, apply to both scopes, idempotence, source
  update propagation, local drift detection, invalid frontmatter rejection, and transactional
  restoration after an injected second-scope swap failure. Exercise the logging wrapper with a
  drift result and require it to preserve exit code `3` while recording the evidence.
- Parse every PowerShell file with the PowerShell parser.
- Confirm the scheduled-task preview invokes only `Check` and does not register a task.
- Freeze only the allowed files and run one formal routine diff review.

## Delivery

This repository has no `.sop/workflow.json`; delivery is manual. The user has authorized completing
the updater, but commit/push remains a separate repository-release action unless explicitly covered
by the current request.
