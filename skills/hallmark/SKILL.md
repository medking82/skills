---
name: hallmark
description: Build a new marketing, brand or campaign web page that does not look AI-generated, or audit a web page for AI tells, with Hallmark's floor, themes and sloplint.
---

# Hallmark: Pages That Do Not Look Generated

Use this mode for a new website or landing page built from scratch (marketing, brand,
campaign, product, booking, shop or event pages), a redesign the user names, or an explicit
audit of a web page for AI tells (去 AI 味, "looks AI-generated"). App UI such as dashboards,
admin screens, editors and tools stays with `impeccable` and `emil-design-eng`; an ordinary
refinement of an existing page uses the Impeccable playbooks.

The [upstream entrypoint](upstream/guide.md) holds the Floor, the Reflex and Finish gates, the
build flow and the theme catalog. Its relative links resolve inside `upstream/`, and
`<skill-dir>` in its commands means this mode's `upstream/` directory. Follow its Floor on
pages this mode builds. On an existing project, preserve the established design system,
fonts, tokens and the user's Title Case UI copy preference, and never invent metrics,
testimonials, logos or claims.

Boundaries that override the upstream text:

- Never touch an existing design unless the user names a redesign or audit of it.
- Floor item 15 (the Hallmark stamp in the first CSS lines) applies only to standalone pages
  this mode creates, never to an existing project's stylesheets; ignore sloplint gate 20 (the
  missing stamp) when auditing an existing page.
- The upstream `imagegen.mjs`, installers, hooks and maintainer scripts are not bundled. Skip
  the comp step and `references/comp.md` (signal 9) even when `TOGETHER_API_KEY` is set, and
  never add an edit hook to the user's agent settings.
- Do not run `theme.mjs index` or `theme.mjs scaffold`; they rewrite bundled files. `deal`,
  `draw`, `check`, `photos` and `log` may write `.hallmark/` in the project, which stays
  uncommitted unless the user asks.
- `sloplint.mjs` needs Node 18 or later. Its static scan writes nothing; `--render` also needs
  `puppeteer-core` and Chrome and writes `shots/`, `before/` and `compare.html` beside the
  target, and `capture.mjs` takes screenshots. Use them only when they are available and fit
  the user's tools, and say what was not checked otherwise.
- Photos come from the bundled Wikimedia Commons list with their credits; keep each credit.
- An audit reports findings and proposed fixes and stops; edit only when the user asks.

Local additions to the upstream flow:

- **Section by section.** Build the hero first, then the remaining sections in page order.
  A revision changes only the section at fault; never regenerate the whole page to fix one
  part, so the rest stays stable and the diff stays reviewable.
- **Ship check.** Before calling a standalone page done, confirm what the page needs from:
  a branded 404, privacy and terms links in the footer, a favicon, `<title>`, meta
  description and `og:image`, client-side validation on every form, and a way back from
  every page. Name any item left out and why in the handoff.
- **Chinese pages.** When the copy is Chinese, set a CJK fallback in the font stack (for
  Traditional Chinese, for example `"Noto Sans TC"`, `"PingFang TC"`, `"Microsoft JhengHei"`)
  and check the rendered glyphs, not just the Latin face. Keep body lines near 30 to 40
  characters, use line-height around 1.7 for body text, and check headline line breaks so a
  phrase is not split or a single character left alone on the last line.

Run the Impeccable `detect` scan alongside `sloplint` when both are available; they catch
different tells. The main LLM selects this mode within `$design`'s routing rules and owns the
result. Check the rendered page when available and authorized; otherwise state what was not
visually verified.
