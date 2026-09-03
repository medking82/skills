# Upstream sync

The `Sync upstream` GitHub Actions workflow checks `emilkowalski/skills:main` every six
hours, at 00:17, 06:17, 12:17 and 18:17 UTC (08:17, 14:17, 20:17 and 02:17 in
Malaysia). It can also be started from **Actions → Sync upstream → Run workflow**.
The schedule runs on GitHub and does not require this Windows checkout to be open.

The workflow runs only for `medking82/skills` on `main`. It uses GitHub's temporary
repository token with `contents: write`; no personal token or extra secret is needed.
Checkout does not retain credentials. The write token is passed to the publish
command; merge and validation commands receive no token. The workflow runs the sync regression tests, fetches upstream, prepares
a merge, validates the merged skill metadata, and then performs a normal push.

Only changes under `skills/`, plus `README.md` and `LICENSE`, are eligible for automatic
sync. Upstream changes to other paths need a manual merge so they cannot replace the
fork's workflow, hooks, scripts or executable validation. Fork-only commits and files
remain in the merge history. An already-synced upstream creates no commit.

A conflict or metadata validation failure aborts the merge and leaves the published
branch unchanged. An overlapping push is rejected without rewriting history; the
next scheduled run starts from the new `main`. Failures are visible in the Actions
run and use the account's existing Actions notification settings.

## Fork customizations

This fork keeps the iPhone Home Screen web-app profile in
[`apple-design`](../skills/apple-design/SKILL.md) and its
[reference](../skills/apple-design/references/ios-home-screen-web-app.md).
It also keeps Codex-compatible frontmatter and explicit invocation policies in
`agents/openai.yaml`. The README skill reference list follows upstream to reduce
conflicts when new skills are added.

GitHub sync does not install skills on a computer. This checkout remains the source
for explicit updates of installed user-scope copies, as described in the README.

## Validation and recovery

Run the repository checks with:

```text
python -B -m unittest discover -s tests
```

Tests use disposable local Git repositories to verify merged history, preservation
of fork customizations, no-op repeats, conflict recovery, invalid metadata,
protected automation paths, dirty checkouts, and concurrent pushes.

After a conflict or an upstream automation change, inspect the failed run, merge
upstream manually while preserving the fork customizations, run the checks, and
publish the resolved merge. Then use **Run workflow** to confirm sync resumes.
`scripts/sync-upstream.py` prepares a local merge and never pushes; run it only in a
clean disposable `main` checkout when reproducing a failure.

To stop automatic updates, disable **Sync upstream** in Actions. To undo a published
sync, inspect its parents and revert the merge with the fork's first parent as the
mainline; preserve later commits and do not force-push.

GitHub may delay scheduled runs and automatically disables schedules in public
repositories after 60 days without repository activity. If this occurs, select
**Enable workflow** in Actions. See the
[GitHub schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
