# Combined Design skill

`skills/design` is the self-contained `$design` entrypoint for this collection's 16 modes.
Its short `SKILL.md` selects a mode; mode guides and their original supporting resources
are loaded only for the current request. No separately installed specialist Skills are needed.
Prototype exploration, library selection, motion review and worst-case UI data testing
(`break-ui`) remain explicitly requested modes. Mentioning `$design` alone does not invoke
them. `break-ui` uses dev-only fixtures/toggles and reports before fixing unless fixes are
requested; its standalone entrypoint also disables implicit invocation.

The original `skills/<mode>` folders remain the maintained sources for upstream merges and
individual installations. Do not edit the generated `skills/design/references` copies.
After changing a source guide or resource, rebuild and validate:

```text
python -B scripts/build-design-skill.py
python -B scripts/build-design-skill.py --check
python -B -m unittest discover -s tests
```

The builder preserves the guide body and supporting resource layout, removes specialist
discovery frontmatter, and records source hashes in the generated manifest. Only the root
`SKILL.md` is discoverable in the combined package. New modes also need a route and invocation
boundary in that root entrypoint before they can be bundled.

The Emil upstream sync rebuilds combined references with the fork's trusted builder before
metadata and freshness validation, then includes those generated files in the merge commit.
Accepted source updates therefore refresh the bundle automatically. New unregistered modes,
router mismatches, generated-file drift, and validation failures still stop publication and
abort the merge. Upstream changes to the builder or other automation require manual review.
The Impeccable fork and snapshot stages follow the separate review boundaries described in
[upstream sync](upstream-sync.md); both upstreams are checked every six hours.

For a combined installation, copy the whole `skills/design` directory to
`<codex-home>/skills/design`. Disable previously installed specialist entrypoints using their
exact `SKILL.md` paths in `[[skills.config]]`; keep their files for recovery. Do not disable
other design, image or document tools. Restart Codex after changing `config.toml`.

Repository publication and installed-copy updates are separate actions. GitHub sync alone
does not install or refresh `$design` on a workstation.
Windows Codex can opt into the dedicated [local auto-updater](codex-design-sync.md),
which follows the published bundle every 30 minutes and includes new routed modes automatically.
