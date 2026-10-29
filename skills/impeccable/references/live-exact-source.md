# Exact HTML Source Editing In Live

Use only with verified true HTML source. The adapter does not interpret JSX, framework
templates, generated HTML, implicit/optional HTML closures or table/select parsing.
For React JSX/TSX compiled into generated HTML, use the separate
[compiler-backed source workflow](live-jsx-source.md).
Never infer a sibling index from identical text. On mismatch or ambiguity, stop that
operation without writing source.

## Capture Repeated Siblings

Before Live initializes, install `../scripts/capture-live-selection.js` as a browser
init script for the app page, using the browser tool's supported script mechanism.
No Codex hook or vendor file edit is needed. If Live already initialized, finish or
abort its current cycle before navigating with the init script. Do not reload an
ambiguous active preview and rely on the native first-match recovery heuristic.

The shim observes the DOM helper's clone at Generate time, keyed by the actual session
id. This captures the selected node after pointer or keyboard navigation. It changes
no page nodes or event payloads. After receiving `generate`, evaluate
`window.__DESIGN_LIVE_SELECTION__.forEvent({id: event.id, element: event.element})`
and save the returned object as `sourceLocator` in the saved generate-event JSON.
Pass actual event data, never an invented path. Missing/mismatched capture requires
a fresh pick, not an ordinal guess. Keep this same page/session connected until resolution.

## Locate

Run the available Python interpreter through the Windows hidden runner:

```text
scripts/live-locate.py --file true-source.html --event generate.json
```

The read-only result compares element structure/attributes/text, parent context and,
when supplied, the exact captured body-relative DOM path plus parent structure. Save
the complete result as a receipt. Offsets are half-open Python Unicode character
offsets. Decode/encode UTF-8 without newline conversion and recheck `sourceSha256`
before any publication. A changed source requires locating again.

For `publishToSource: true`, splice all variants and scoped CSS into `wrapperBlock`
and replace only the returned source range in one edit, retaining its boundary newlines.
Then follow normal upstream done/accept/discard cleanup. Use `--detached` to opt into
the source-untouched workflow below for block elements too.

## Detached Inline Preview

For `publishToSource: false`, NEVER insert the scaffold into real source. Publish it
only to `.impeccable/live/previews/SESSION.html`, creating the directory as needed.
Keep the receipt outside scanned source too. Use compact span variant slots with
`display:contents`, containing exactly one replacement element of the original tag.
Do not add whitespace between slots or outside the replacement. Keep the supplied
wrapper-contained CSS: it overrides native block display while native hidden-slot
rules still hide every other slot. Add variant CSS inside the wrapper. Limit changes
to the selected element; bake any parameters into the accepted permanent element.

Only after the preview file exists, reply `done --file <preview-path>` and resume
polling. Check the rendered inline flow and that true-source bytes remain unchanged.
Verify the session capture still exists before accepting a recovered preview.

Native poll still calls accept/discard. For this detached session, require
`_acceptResult.handled: false` with `Session markers not found for id: SESSION`.
Source intentionally has no wrappers. Any other result needs inspection; never apply
on top of an unexpected native mutation. `_completionAck` alone proves no source write.

On accept, extract only `variantId`'s single replacement element, with params baked
and no live wrapper/CSS markers. Save it without a trailing newline, then run:

```text
scripts/live-locate.py --file true-source.html --receipt receipt.json --replacement chosen.html --session-id SESSION
```

Use the actual accept event's session id. The command requires the same session,
file/hash/range, locks the existing file, rechecks its
bytes and replaces exactly the range while preserving neighboring bytes and file
permissions. It refuses source drift. Independently verify the accepted source and
absence of live markers before replying `complete --file <true-source-path>`. That
reply updates the journal's source path; it does not run native cleanliness checks.
On discard, leave true source untouched and reply `discarded` explicitly (native
discard's missing-marker result is an error acknowledgement). Then poll again.

On exit, call `window.__DESIGN_LIVE_SELECTION__?.dispose()` and follow normal Live
server cleanup. No permission or scheduling changes are part of this workflow.
