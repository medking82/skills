# Peer-review alias policy migration

## Ticket and outcome

One downstream ticket: migrate this repository's tracked peer-review policy to the published
schema-v5 Claude alias contract. The repository remains in report mode, and no updater,
installation, scheduler, or skill behavior changes.

Observable success:

- `.peer-review/config.json` uses schema version 5;
- Claude review uses literal `fable` primary and `opus` quota fallback aliases;
- Claude routine and high-risk effort are both `max`;
- the existing Codex policy, plan roots, timeout policy, diff-review budget, and report mode remain
  byte-for-byte equivalent after JSON normalization; and
- the installed `peer-review-gate` 0.9.2 validator accepts the exact tracked policy.

## Context map

- Entry point and authoritative state: `.peer-review/config.json` is the repository's only tracked
  review policy and is consumed by the external `peer-review-gate` runtime.
- Runtime owner: published `peer-review-gate` 0.9.2 owns schema-v5 model compatibility, structured
  quota fallback, canonical model attestation, and within-run stability. This repository only
  selects literal policy tokens.
- Consumers: plan review under `docs/plans` / `docs/specs`, routine diff review, and any future
  enforce-mode release preflight. Current mode remains `report`.
- Existing application boundary: Apple Design Check/Apply scripts, tests, installed skill trees,
  Windows Scheduled Task, and systemd timer are independent of reviewer configuration.
- Rollback: revert this policy migration commit; no application or installed state is touched.

## Contract evidence and executable discovery

The external authority is intentionally not vendored into this skills repository. Its published
contract is nevertheless commit-bound and locally discoverable:

- `medking82/peer-review-gate@47cc33e` is release 0.9.2. Its
  `.claude-plugin/plugin.json` declares `0.9.2`; `scripts/config_loader.py` defines schema-v5
  Claude's exact `model`, `effort`, `high_risk_effort`, and `quota_fallback_model` keys and requires
  distinct, non-empty model tokens; and its README documents `fable` / `opus` as the official
  latest aliases.
- `medking82/agent-sop-kit@9c670f6`, `DECISIONS.md` decision 36 and the project-initialization
  section of `README.md`, publishes the downstream alias contract used by this migration.

Validation discovers the installed authority by running `claude plugin list --json`, selecting
the exact plugin ID `peer-review-gate@peer-review-gate-marketplace`, and requiring version `0.9.2`.
It then imports `<installPath>/scripts/config_loader.py` and calls `load_path()` on the tracked
config. A missing plugin, different version, missing loader, or normalized-policy mismatch is a
hard validation failure; no fallback path or network install is allowed by this ticket.

## Guardrails

Required policy:

1. Change only the schema-v5 Claude routing fields required by the published alias contract.
2. Preserve literal aliases; never canonicalize `fable` / `opus` to version pins.
3. Preserve all existing non-Claude policy values, including Codex effort and high-risk effort.
4. Validate with the installed 0.9.2 config loader and assert the complete normalized object, not
   selected fields only.

Allowed files:

- `.peer-review/config.json`
- this plan

Do not touch or execute:

- `skills/**`, `scripts/**`, `tests/**`, or `README.md`;
- Apply mode, installed user skill directories, Windows Scheduled Tasks, or systemd timers;
- upstream synchronization, plugin installation/update, or repository merge.

## Validation and review

Targeted validation:

- parse the tracked file as JSON;
- discover the installed peer-review-gate 0.9.2 path through `claude plugin list --json` and load
  the policy through that installation's `scripts/config_loader.py:load_path()`;
- deep-compare the normalized policy with the exact expected schema-v5 object;
- confirm the diff changes only the allowed paths.

Repository regression validation:

- `python3 tests/test-apple-design-updater.py`;
- parse `scripts/sync-apple-design.py` with a temporary bytecode cache;
- `bash -n scripts/install-apple-design-update-timer.sh`;
- run `tests/test-apple-design-updater.ps1` through Windows PowerShell 7 as the repository's
  explicitly Windows-only regression check.

After targeted validation, stage the exact two-file diff and invoke one routine diff review through
the repository's sole peer-review authority. Delivery is manual: commit, push, and Draft PR are
authorized by this ticket; Apply, installation, timer changes, and merge are not.
