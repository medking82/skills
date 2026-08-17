# Shared SOP project shell

> Generic SOP implementations live in the adjacent `agent-sop-kit`, user-scoped shared
> skills, and the installed `peer-review-gate` plugin. This project keeps only policy wiring
> and product-specific adapters.

> Prime directive: for an authorized routine change, advance unattended through configured
> green stages toward commit-bound, verified production. A red or unknown gate blocks
> downstream advancement; auto-mode may remediate within the authorized scope and rerun
> deterministic checks. Routine diff review may continue only when `peer-review-gate`
> authorizes the next persisted round; reviewer failures are never retried and release
> requires approval bound to the current diff. Preserve
> low-bug delivery, one authoritative domain kernel, one canonical database field schema,
> registry-driven extension, and consistent typed database-field semantics without
> speculative abstraction.

- Root `CLAUDE.md`, `AGENTS.md`, and `.claude/rules/` own product, stack, data, deployment,
  and infrastructure rules.
- Before planning work that touches shared components, a kernel, schema, or data flow, read the
  root context map/glossary, relevant ADRs, and `docs/FRAMEWORK.md` or its linked equivalent.
  Name the authoritative owner, public boundary, existing reuse point, hidden complexity, and
  affected consumers. Prefer deep modules; do not replace duplication with a god object.
- For large initiatives, keep `WAYFINDER.md` as a lightweight ticket/status/path index and work on
  one ticket per fresh session. Preserve recurring out-of-scope decisions with their reason rather
  than reopening them in every session.
- Routine isolated work may use in-task success criteria and skips formal plan review unless the
  user, an active ticket, or repository policy explicitly requires it. Consequential cross-module,
  shared/kernel/schema/data-flow, schema/data migration, auth/infrastructure, broad or weakly
  verified production-data mutation, or unknown-blast-radius work uses one persisted plan-review
  run, with at most three rounds.
- Production write authorization and risk classification are separate. Production alone does not
  make work high risk. A repository-declared bounded correction to routinely mutable operational
  records stays routine when identity/evidence is authoritative, expected values/count guard the
  write, verification and rollback are exact, and failure impact is low; do not add a plan, staged
  SQL artifact, or cross-model review solely for its destination.
- `.sop/sop.py review` is the sole formal operator entry in a governed repository;
  `.peer-review/config.json` selects `peer-review-gate` as the only review authority behind it.
  Advisor and second-opinion output is `ADVISORY` and never approval. New projects
  default routine diff remediation to two persisted rounds; projects may configure one through
  five, and five remains the hard circuit breaker. Failures/timeouts are not retried and APPROVED
  must match the exact frozen changeset handed to autotrigger.
- Review round caps are circuit breakers, not targets. Group findings by stable root cause;
  continue with the durable unresolved ledger and target delta. `status`/`watch` are exceptional
  read-only attachment tools for an existing run; `recover` is only for a lost foreground handle.
  None is an extra daily review entry or permission to start another reviewer.
- `.sop/sop.py` and `.sop/workflow.json` own stage transitions. Stop at the first failed
  stage; do not skip, repeat, reorder, or bypass it.
- `.sop/workflow.json` defaults to `delivery.mode=manual`. Only an explicitly configured
  `autonomous_to_prod` repository may hand an APPROVED routine frozen diff directly to
  autotrigger; red/unknown gates, resume, rollback, and high-risk work remain human-gated.
- Use targeted tests and quick checks while editing. In an autonomous repository, Autotrigger
  owns the configured release full stage; run standalone full only for a manual gate, CI, or an
  explicit request. Do not start review, dogfood, deployment, or rollback without authorization.
- Treat delivery reports as decision surfaces: lead with the outcome, surface surprising choices
  or risks before routine detail, reuse the user and repository glossary, preserve exact technical
  terms needed for verification, and separate facts from assumptions or inference. Calibrate
  detail to the reader; brevity alone does not make an explanation clear.
- Full local-stack dogfood is optional and must not start automatically unless it is hermetic,
  bounded, and covers a material risk unavailable from deterministic tests.
- Do not busy-wait. Deterministic processes own background waiting and emit evidence.
- `sop update --check` is read-only apart from remote metadata. Apply, rollback, scheduler,
  plugin, and project-file changes require explicit authorization.
- Shared `$brownfield-change`, `$architecture-sweep`, `$triage-requests`, `$to-tickets`,
  `$ai-product-audit`, `$workflow-routing`, `$explain-output`, `$freshchat`, and `$autotrigger`
  skills are
  user-scoped; each solves one bounded problem and stops. Do not copy their implementations into
  this repository or assume that one skill must automatically invoke the next.
- Project-specific note: Preserve repository-specific operational boundaries and do not infer production authority from local SOP installation.

Reply convention: 中英混合.
