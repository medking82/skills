# Upstream Sync

Two upstreams feed the maintained `/design` package through GitHub Actions. These
are the configured six-hour schedules; a local workflow file does not establish
that it is published, enabled, or successfully running on GitHub.

| Stage | Workflow And Repository | UTC Schedule | Malaysia Schedule |
| --- | --- | --- | --- |
| Emil → Skills | `Sync upstream` in `medking82/skills` | 00:17, 06:17, 12:17, 18:17 | 08:17, 14:17, 20:17, 02:17 |
| Impeccable → Personal Fork | `Sync Personal Fork` in `medking82/impeccable` | 00:07, 06:07, 12:07, 18:07 | 08:07, 14:07, 20:07, 02:07 |
| Personal Fork → Bundle | `Sync Impeccable References` in `medking82/skills` | 00:37, 06:37, 12:37, 18:37 | 08:37, 14:37, 20:37, 02:37 |

The workflows also accept manual dispatch on their repository's `main` branch.
The two Skills workflows share `sync-upstream-main` concurrency with cancellation
disabled. Staggered times are not a dependency guarantee: a delayed fork run can
leave the bundle stage one cycle behind. The next run checks the latest fork head.

## Emil Merge And Rebuild

[`sync-upstream.yml`](../.github/workflows/sync-upstream.yml) checks
`emilkowalski/skills:main`. It runs regression tests, prepares a merge, rebuilds
combined references with the fork's trusted `scripts/build-design-skill.py`, and
validates metadata and bundle freshness before a normal push. Generated references
and their manifest are committed with the merge. An already-merged upstream is a no-op.

Only upstream changes under `skills/`, plus root `README.md` and `LICENSE`, are
eligible. Top-level scripts, tests, hooks, workflows, and other automation require
manual review; upstream cannot replace the executed builder or validator through
this automatic path. This is the existing Emil allowlist, not the Impeccable-specific
script/license policy below. New unregistered modes, missing routes, generated-file
drift, invalid metadata, and merge conflicts still halt publication and abort the
merge. Review new modes and explicitly update the accepted inventory and router.

The fork retains the iPhone Home Screen web-app profile in
[`apple-design`](../skills/apple-design/SKILL.md), Codex-compatible frontmatter,
and invocation policies in `agents/openai.yaml`. Fork-only commits remain in history.

## Impeccable Fork And Bundle

`sync-personal-fork.yml` in the personal fork fetches `pbakaus/impeccable:main`
and merges normally, preserving personal commits. Changes to `.github/workflows`
between merge base and upstream head stop before merge, including additions,
edits, deletions, and renames. Conflicts abort without publication. This job does
not execute upstream builds, engine scripts, package installs, or inherited workflows.
Review inherited workflows, including Sheriff, separately; do not enable them just
to activate the personal sync workflow.

[`sync-impeccable.yml`](../.github/workflows/sync-impeccable.yml) checks out the
personal fork as data. Root-anchored non-cone sparse patterns materialize the entire
`.agents/skills/impeccable/` tree, root `LICENSE`, and root `NOTICE.md`. The ancestry
API comparison must be `ahead:0` or `identical:0` relative to the commit recorded in
`skills/impeccable/upstream/source.json`. History rewrites, divergence, and API
failures halt the import.

The importer checks provenance and ownership before writing. Changes to imported
`scripts/`, imported `agents/`, `LICENSE`, or `NOTICE.md` require manual review;
automatic runs never pass `--allow-code-updates`. Upstream `agents/openai.yaml` is
deliberately excluded and cannot replace the bundle's invocation policy; other
imported agent files remain protected. Guidance changes are imported, all combined
references are rebuilt, and the full test suite must pass. The commit includes the
owned snapshot and entire generated references directory, keeping every rebuilt
mode consistent with the manifest.

GitHub's temporary repository token is passed only to the ancestry API check and
publication. Importer, builder, tests, and merge commands receive no token environment.
Checkout credential persistence is disabled; no extra secret or personal token is
needed. Every push is normal: a concurrent remote update rejects publication
without rewriting history, and the next run starts from the new `main`.

## Review And Recovery

Inspect the failed step and exact upstream diff before retrying:

- Workflow/top-level automation changes: reconcile manually in a clean review
  checkout, preserving the personal sync workflow and trusted validation code.
  Keep inherited workflows disabled until separately reviewed.
- Impeccable script, agent, or attribution changes: review additions and deletions
  at the exact fork SHA. In a clean Skills review checkout, run
  `scripts/sync-impeccable.py --source <clean-fork-checkout> --commit <full-SHA> --allow-code-updates`
  only for reviewed changes, then rebuild and test. Never add this override to automation.
- History rewrites, ownership drift, or conflicts: reconcile source commits and owned
  files explicitly. Do not delete manifests or force-push to bypass checks.

Publish reviewed changes through the repository process, then manually dispatch the
affected workflow to verify recovery. Revert a merge using the fork's first parent
as mainline after inspecting its parents; revert a snapshot commit normally. Preserve
later work. Disable the specific workflow in Actions when pausing a stage.

## Windows Delivery And Observable Health

GitHub publication and local installation are separate. The enrolled
[Windows design updater](codex-design-sync.md) follows published `medking82/skills`
every 30 minutes and at current-user logon. It atomically refreshes only the combined
package and stops on local drift. Its hidden launcher uses the actual `python.exe`;
changes to the updater implementation require reinstalling its trusted runtime helper.
The disabled shared SOP updater is separate.

Check each stage's latest completed Actions run, result, and published commit.
Compare the bundle's Impeccable source SHA with the personal fork head, and check
`skills/design/references/sources.json` hashes. A successful no-op is healthy only
when the relevant source is represented; an old green run is not evidence of freshness.

On Windows, inspect `%USERPROFILE%\.codex\design-sync\last-run.json` for `enrolled`,
`updated`, `unchanged`, or `attention`, alongside its timestamp and details. Inspect
`state.json`, Task Scheduler's last result, and `launcher-error.log` for startup
failures. Preserve enrollment state when resolving drift. GitHub delays, disabled
schedules, a signed-out Windows user, and a stopped task can interrupt delivery.
Adding workflow files alone does not verify those runtime conditions.

The design routing contract keeps the main LLM's final decision, with Jev as a
second opinion where applicable. Maintenance does not change that contract or the
user's Title Case preference for visible English UI copy.

## Local Validation

Run the builder freshness check and full suite from the canonical Windows checkout
through the hidden runner:

```powershell
$repo = 'C:\github\SOP\skills'
$runner = 'C:\Users\Marck\.codex\bin\invoke-hidden.ps1'
$python = (Get-Command python.exe -CommandType Application).Source
& $runner -FilePath $python -ArgumentList @('-B', 'scripts/build-design-skill.py', '--check') -WorkingDirectory $repo
& $runner -FilePath $python -ArgumentList @('-B', '-m', 'unittest', 'discover', '-s', 'tests') -WorkingDirectory $repo
```

`tests/test_impeccable_workflows.py` runs the real workflow shell using native Git
Bash on Windows (bash on Linux), offline synthetic repositories, mocked API replies,
and local bare publication targets. It covers ancestry rejection, complete shallow
sparse checkout, preserved history, no-op repeats, workflow review stops, conflict
abort, complete generated-reference staging, and concurrent push rejection. No
credential or GitHub mutation is needed. Fork-specific tests use the canonical
sibling workflow, or `IMPECCABLE_FORK_WORKFLOW`; they explicitly skip if unavailable
in a Skills-only CI checkout. Hosted Actions still require a real run to verify
permissions and scheduling.

The Emil tests cover accepted-source rebuilds, trusted builder preservation,
unknown-mode rejection, rollback after metadata failure, dirty checkouts, and
concurrent pushes. `scripts/sync-upstream.py` never pushes; reproduce a failure in
a clean disposable `main` checkout, not one containing user work.
