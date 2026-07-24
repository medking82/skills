# Apple Design WSL updater

## Intent

Add a native Linux check/apply path for the published
`medking82/skills@main/skills/apple-design` tree. Keep four independent installed
snapshots current without linking a live checkout into either desktop:

- `/home/marck/.agents/skills/apple-design` (WSL Codex)
- `/home/marck/.claude/skills/apple-design` (WSL Claude)
- `/mnt/c/Users/Marck/.codex/skills/apple-design` (Windows Codex Desktop)
- `/mnt/c/Users/Marck/.claude/skills/apple-design` (Windows Claude Desktop)

The existing PowerShell updater remains the Windows fallback.

## Context map

- The published fork `main` archive is authoritative. A local branch or working tree is
  never an implicit source, because it may contain unreviewed skill content.
- `scripts/sync-apple-design.py` owns Linux Check/Apply, archive validation, compatible
  manifest generation, and the four-scope transaction.
- `scripts/install-apple-design-update-timer.sh` previews or installs a user-level,
  check-only systemd timer. The timer never receives standing Apply authority.
- Each installed tree is a complete byte-for-byte snapshot. No destination is a symlink,
  junction, or live Git mount.
- Check and Apply report the same relative-path/length/SHA-256 manifest digest as the
  existing PowerShell updater.
- The Windows profile is accessed through `/mnt/c`. A missing/non-9p mount, missing
  `C:\Users\Marck` bridge, or missing `.codex`/`.claude` parent fails closed before any
  destination write.
- Apply stages inside each skills root so each rename stays on one filesystem. It retains
  all prior trees until every new tree has been swapped and verified, then removes backups.
  A pre-commit failure restores changed scopes in reverse order.

## Guardrails

1. Check downloads and validates published `main`, compares all four scopes, creates no
   destination roots, and exits `0` when current or `3` when missing/drifted.
2. Apply requires the exact 64-hex `source_sha256` emitted by a prior Check. A missing or
   mismatched digest performs zero destination writes.
3. Source and destination trees must contain only regular directories/files, must contain a
   regular `SKILL.md` declaring `name: apple-design`, and must contain no symlinks or special
   files.
4. Apply stages and verifies every changed scope before swapping any scope. It verifies all
   four post-swap manifests before declaring the transaction committed.
5. The Linux runner uses the published codeload archive by default. Local source and custom
   scope arguments are hidden test hooks, not supported operator inputs.
6. The timer installer is preview-first. Its generated service always invokes Check,
   treats drift exit `3` as an expected service result, logs to the user journal, and has no
   auto-apply option.
7. The Windows Scheduled Task remains enabled until a separate, explicit cutover after
   one manual Linux check/apply verification and one successful natural timer cycle.

## Allowed files

- `README.md`
- `docs/plans/apple-design-wsl-updater.md`
- `scripts/sync-apple-design.py`
- `scripts/install-apple-design-update-timer.sh`
- `tests/test-apple-design-updater.py`

## Do not touch

- `skills/**`
- Existing `scripts/*.ps1` and `tests/test-apple-design-updater.ps1`
- User-installed skill directories during repository implementation/tests
- Windows Scheduled Tasks or installed systemd units
- Git history, published branches, deployment, and review state

## Verification

1. Run `python3 tests/test-apple-design-updater.py`.
2. Parse the Python runner with `python3 -m py_compile` using a temporary bytecode cache.
3. Parse the installer with `bash -n`.
4. Run the existing PowerShell updater tests through Windows PowerShell 7.
5. Run a remote-source Check against temporary custom scopes and confirm its digest equals
   the current published-main digest without creating those scopes.
6. Confirm the frozen diff contains only the allowed files.

## One-time cutover and rollback

After this repository change is separately published:

1. Run Linux Check and review its `source_sha256` and four scope states.
2. Run one explicit digest-bound Apply.
3. Re-run Check, compare all four manifests, and verify fresh WSL Codex/Claude and Windows
   Desktop sessions can load `apple-design`.
4. Preview, then install the user timer. Trigger its service once manually and observe one
   natural 06:30 cycle before disabling the Windows task.

For scheduler rollback, disable the user timer and re-enable the still-preserved Windows task.
For content rollback, restore the previously approved content on published `main`, then repeat
Check and digest-bound Apply. Failed in-flight Apply operations restore prior snapshots
automatically.
