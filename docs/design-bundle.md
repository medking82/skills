# Combined Design skill

`skills/design` is the self-contained `$design` entrypoint for this collection's 13 modes.
Its short `SKILL.md` selects a mode; mode guides and their original supporting resources
are loaded only for the current request. No separately installed specialist Skills are needed.
Prototype exploration, library selection and motion review remain explicitly requested modes.

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

The existing upstream-sync metadata validation also checks bundle freshness when the bundle
is present. An upstream source change that needs a bundle rebuild stops publication until a
maintainer reconciles it and reruns validation. The sync runner and workflow remain unchanged.

For a combined installation, copy the whole `skills/design` directory to
`<codex-home>/skills/design`. Disable previously installed specialist entrypoints using their
exact `SKILL.md` paths in `[[skills.config]]`; keep their files for recovery. Do not disable
other design, image or document tools. Restart Codex after changing `config.toml`.

Repository publication and installed-copy updates are separate actions. GitHub sync alone
does not install or refresh `$design` on a workstation.
