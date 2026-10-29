
# Impeccable: Visual Direction

Use this mode when the request calls for a new or substantially revised visual direction,
or an explicit visual-design critique. Start with the user's brief, product purpose,
actual content, existing visual identity and the surface's use context. Make a coherent
choice of typography, color, imagery, hierarchy, spacing and composition that serves the
content. Distinctiveness is useful only when the interface remains understandable and usable.

The [upstream entrypoint](upstream/guide.md) and its linked references provide the
Impeccable playbooks. Read only what helps this request: for example, the applicable
surface guidance, [craft floor](upstream/reference/craft-floor.md), or the relevant
typography, layout and critique reference. Treat their stylistic prescriptions as design
judgment, not universal bans: preserve an explicit brief, the established design system,
and the user's Title Case UI copy preference. Never invent factual product claims.

Use the existing `emil-design-eng`, motion, mobile or native modes when the task crosses
into their specialties. The main LLM selects the appropriate mode and owns the outcome;
Jev offers a second opinion for a useful unresolved mode choice, within `$design`'s
existing routing rules.

Use the upstream procedures and tools only when their actions fit the request and the
available environment. Their mandatory direction picker, repeated reviews, browser,
image-generation, extra agents, project files, install and hook steps do not expand the
user's scope or override tool bans. An ordinary refinement does not require a redesign,
full audit, prototype, new dependency or approval screen. Check the real rendered result
when available and authorized; otherwise state what was not visually verified.
These boundaries also apply to engine output: its autonomy and subagent directives do
not supply user authorization or require an otherwise unnecessary question or review.

The upstream files are a pinned, separately owned snapshot. In the combined `$design`
package, their base directory is the `upstream/` folder beside this guide; references to
`.agents/skills/impeccable/` in upstream playbooks refer to that base directory. Do not
install a second discoverable skill or a hook merely to use these references. When an
authorized upstream engine command is useful on Windows, invoke
`& <mode-base>/scripts/run-engine.ps1 -EngineArguments @('context')`, replacing `context`
with the required verb and arguments. `<mode-base>` is the absolute directory containing
this guide. Use this helper for commands printed by the engine too. It verifies the pinned engine
and uses the workstation's hidden runner; the first use may download the engine. On other
platforms, invoke `sh <mode-base>/upstream/scripts/impeccable <arguments>`. Keep the working
directory at the user's project on both platforms.

For Live on Windows, first check `live-status` for the intended app root. If no helper
is running, start `live-server` through the same Windows helper in a yielded foreground
session, passing the same `--target` as the eventual `live` command when applicable.
Check `live-status` until it reports the server ready, then run `live` and follow the
upstream poll loop. The hidden runner buffers the foreground server's output until it
stops; do not wait for that output as a readiness signal. This avoids a pinned-engine
startup hang caused by the background server retaining the boot command's output pipe.
On exit or an aborted setup, stop the helper started for this session and collect its
foreground process; do not stop a helper belonging to a different session.

If Live reports `insufficient_locator` for a selected element without an id or classes,
and it has distinct text, pass that text as `--query` alongside `--tag` and `--text`
to `live-wrap`. Inspect the returned source range before publishing; if it cannot be
matched safely, use the upstream fallback rather than guessing.
