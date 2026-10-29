# Design Routing And Live Acceptance — 2026-10-29

The installed skill was exercised by an independent model in a fresh agent turn.
The host receipt `a15f4785908947e3836433619e4c3476` correlated to turn
`01a185e9-fc98-7251-8d6a-e04a72246c30`: `status: ok`, `source: explicit`, skill
`design`, with no design-mode recommendation. This proves that turn's skill routing;
it does not prove that all future ordinary requests cause remote Jev calls.

| Synthetic Request | Observed LLM Selection | Jev |
| --- | --- | --- |
| Text hierarchy and phone tap/scroll; preserve motion | Impeccable `typeset` plus Emil `mobile-native` | No choice needed for independent outcomes |
| Drawer motion feels wrong; no frame profile | Emil `animate` after checking performance guidance | One request; `status: ok`, `source: fallback`, `mode: emil-design-eng`, `reason_code: low_confidence` |
| Explicit typeset only | Impeccable `typeset` only | Explicit selection needs no call |

The ambiguous case sent a remote request and received a structurally valid response
(`jev-1.14.0`, reported 380 input tokens), but confidence was below the adapter threshold.
The advice was not accepted. The LLM continued without retrying. No raw confidence
value was retained. An earlier successful helper request is separate evidence.

The operational chain is host skill selection, then LLM playbook/mode selection,
then a Jev second opinion only for a useful unresolved mode choice. Ordinary hook
abstention is expected; the model can still select the skill and invoke its helper.
No Codex hook, model, permissions or scheduling configuration was changed for this test.

A second fresh agent received a concrete UI implementation request without any skill
name: a phone settings card with readable type hierarchy, touch feedback and no motion.
It independently read `design`, Impeccable `typeset` and Emil `mobile-native`, then
created an isolated HTML fixture. No Jev call was needed for these independent outcomes.
This verifies implicit LLM selection in that execution. No correlated host hook receipt
was available for this second turn, so it does not establish a host-generated mode hint.
Its static/mock checks are not phone or rendered-browser evidence.

Live was tested in a real browser against pinned engine `0.1.18+engine`. A minified
HTML page contained two identical headings without ids/classes in separate parent
sections. A real Generate event reported `insufficient_locator`. The new read-only
source adapter identified the selected second heading from its structure and parent
context. Three variants appeared. Accept and reload changed only that heading;
the first heading, both paragraphs and adjacent Unicode content remained intact.
A second Generate/Discard/reload restored the previous heading. Native cleanup left
no variant wrappers; it can retain blank lines around the edited block.

The initial test exposed native accept deleting same-line neighbors. Isolating the
wrapper markers on their own lines fixed that case. A native-engine regression now
checks both accept and discard, including neighboring markup and Unicode. Run it on
Windows by setting `IMPECCABLE_TEST_ENGINE_WRAPPER` to the installed `run-engine.ps1`
and running `python -B -m unittest discover -s tests -p test_live_locator_engine.py`.
Without this opt-in, that integration test skips; unit tests remain portable.

## Inline And Repeated-Sibling Follow-Up

A second real-browser fixture used minified HTML containing
`Before<span>Same</span><span>Same</span>After &amp; 中文`. Neither span had an id/class.
An init-script capture at the native context-clone seam recorded the exact Generate
session and body-relative element path, including the selected second sibling.
The production capture script also passed Node VM checks for session correlation,
later unrelated clones, missing captures, disposal and late-install refusal.

Inline previews lived only under `.impeccable/live/previews/`, with compact span
shells and a locally scoped display override. Real computed styles showed only the
chosen slot as `display:contents`, all other slots hidden. Visible text remained
`BeforeSameSameAfter & 中文`; source hashes were unchanged throughout preview and
native Accept. The native missing-marker result was expected and inspected.

After Accept of variant 2, the source adapter replaced only the second span under a
file lock and hash/range guard. Exact byte comparison against the expected one-range
replacement passed. Reload showed two span elements, surrounding text nodes unchanged,
and font weights 400/600. No wrapper or whitespace node was added to source.

A further browser test clicked the first identical sibling, used ArrowDown to select
the second, and generated again. Capture still reported sibling index 1. Discard
left true-source bytes exactly unchanged; explicit discarded acknowledgement cleared
the cycle, with no residual wrappers. Native-engine regression covers detached
Accept/Discard source safety and exact inline promotion; portable tests cover source
drift, DOM/source mismatch and byte preservation. Browser capture was disposed and
test servers stopped after acceptance.

Boundaries: use well-formed true HTML source and a fresh session-correlated capture
for indistinguishable siblings. Missing captures, parser/browser disagreement,
framework templates, generated HTML and parser-sensitive table/select targets still
require the source-aware fallback. Detached cycles must not rely on the native
first-match recovery heuristic after reload. Source drift refuses the write.

## React JSX/TSX And Generated HTML Follow-Up

The user selected React/Next.js as the priority framework. A development-only Babel
plugin now emits per-file provenance manifests and compiled DOM markers from original
JSX/TSX AST ranges. A webpack pre-loader preserves the existing JSX/TSX compiler and
passes through a source map. Original component files receive no instrumentation.
The capture includes the compiler marker and actual DOM occurrence count.

Two actual runtime paths were exercised:

- **Generated static HTML:** Babel 7.28.5 compiled a TSX component, then React 19
  `renderToStaticMarkup` generated ignored `dist/index.html`. The selected second span
  mapped to its real TSX range. Preview and native Accept left component bytes unchanged.
  After parser validation, the locked writer changed only that range. Exact byte
  comparison preserved neighboring source, both `{label}` bindings and handlers.
  Rebuilding regenerated the page with weights 400/600 and intact adjacent content.
- **Next.js 16.4.3 webpack dev:** a real App Router client component hydrated, and its
  click handler incremented a counter. Live selected the second span, displayed three
  detached variants and accepted variant 2 into `app/page.jsx`. Exact source comparison
  passed. Fast Refresh displayed the chosen class/weight; the target still incremented
  the counter from 0 to 1. Adjacent paragraph text and aside remained intact. Browser
  console reported no errors after the source write. This used `next dev --webpack`,
  not Turbopack; no production Next build was claimed.

Compiler tests exercised JSX and TSX, astral-character offset conversion, static style
edits, preservation/refusal of expressions/handlers/structure, stale source rejection,
manifest sharding and production no-op behavior. A real React render of a loop produced
two DOM nodes from one compiler marker; single-instance mapping correctly refused.
The byte writer also rejects missing/mismatched compiler validation and wrong sessions.

Scope: verified original JSX/TSX, local development provenance, static UI edits with
existing structure/bindings. Uninstrumented generated files, shared runtime instances,
Other template languages and structural/dynamic expression changes are not
claimed as supported by this bridge. They require their native source-aware workflow.

## Next.js Turbopack Follow-Up

Actual Next.js 16.4.3 `next dev --turbopack` was exercised without switching to webpack
or broadening `turbopack.root`. The existing loader already receives the required
`this.mode` and callback/map contract. The change adds the validated configuration
and regression coverage rather than an extra loader implementation.

Development-only rules targeted app JSX/TSX and excluded foreign modules. A bare
`app/**/*.tsx` glob missed the nested fixture's workspace-prefixed path; a scoped
path condition matched correctly. Both server-rendered layout JSX and hydrated client
TSX received provenance markers and per-file manifests.

Real browser Live selected the second identical span in `app/Client.tsx`. Three inline
variants rendered without changing source. Accept of variant 2 passed AST/binding
validation and the locked range writer. Exact-byte comparison preserved all neighboring
source, TypeScript annotations, both `{label}` expressions and handlers. Turbopack hot
refresh showed weights 400/600; the target still incremented its counter from 0 to 1,
with unchanged adjacent text/aside and no browser console errors.

After stopping/restarting the dev server with its existing cache/state, fresh browser
Generate still located the current source hash/range. A further preview/Discard left
source bytes exactly unchanged and no wrappers in the DOM.

`next build --turbopack` compiled and type-checked successfully and prerendered all
three fixture pages. An initial type-check failure identified a loose `chosen.tsx`
snippet being included as project source. Moving snippets to `.impeccable/live/*.txt`
fixed this and the skill instructions now use that convention. Production HTML/JS
contained no provenance markers; dev manifests and target source were unchanged.

The Next schema/loader regression validates scoped rules, rejects webpack `enforce`,
checks the available loader API subset and Babel map/source contents, and validates
JSX/TSX snippet text independently of its `.txt` extension. Set
`DESIGN_TURBOPACK_TEST_PROJECT` to an installed Next/Babel fixture to run it. This
regression and real production build are separate evidence; it does not claim browser
debugger source-map resolution was verified. Missing/stale provenance, shared runtime
instances and dynamic/structural edits retain their previous refusal boundaries.

## Structural JSX And Dynamic Template Follow-Up

An explicit `--mode structural` validator now permits layout changes around an
ordered projection of protected bindings. The default static lane still refuses
tree changes. Dynamic conditionals/map callbacks allow recursive changes only to
their JSX islands: all surrounding JavaScript remains byte-identical. Protected
elements retain their tag, ordered dynamic attributes and binding ownership;
custom components stay opaque. Spread-bearing elements freeze all ordered props.
Key/ref island roots cannot be wrapped below a new unkeyed boundary.

The compiler regression reproduces the default structural refusal, then accepts
passive wrappers, conditional branch layouts and layout inside keyed map items.
It rejects expression loss/duplication/rewrites, handler transfer/tag changes,
evaluation reordering, changed conditions/callback parameters/data sources,
key loss or wrapper displacement, custom-component changes and spread overrides.
A source-context guard now rejects callback/nested-function selections at locate
and validate, including a loop reporting only one current DOM occurrence.

Real Next.js 16.4.3 Turbopack browser Live exercised a unique section containing
stateful conditionals, a keyed list, selection output and handlers. Detached
preview showed three variants; only the active slot was visible. Accept of
variant 2 left native source untouched until Babel validation and the locked
writer replaced exactly the selected range. Exact source comparison preserved
all preceding/following bytes, expressions and handlers. The accepted JSX added
a header wrapper, changed the conditional branch layout and wrapped list button
contents without moving their keys or handlers.

After hot refresh and a clean reload, the accepted section retained its class,
2px border and header. Real clicks toggled both conditional branches, selected
Beta, appended a third item and selected the newly generated Added button.
All three dynamic list labels rendered in their new nested markup. Adjacent
paragraph/aside remained unchanged; the browser had no warning/error messages.
A second Generate/preview/Discard cycle on the updated source left bytes exactly
unchanged and removed every preview wrapper. Capture was disposed, Live exited,
and both local servers were stopped.

`next build --turbopack` compiled and passed TypeScript, then prerendered all four
fixture outputs, including `/structural`. The fixture's existing multiple-lockfile
workspace-root warning remains; no bundler-root or dependency configuration was
changed for this follow-up.

The full 84-test suite passed with real project Babel/Next and pinned native-engine
checks enabled. Bundle freshness, skill metadata and whitespace checks passed.
Production server/static output contained no Live/provenance markers.

Scope: structural layout within the validated React/Next source contract, with
unchanged executable expressions/handlers. Other template languages, custom
component internals, arbitrary JavaScript changes and unresolved shared-source
reuse are not covered. Parsing/projection do not prove equivalent DOM semantics,
focus, component reconciliation or event propagation for arbitrary reparenting;
project runtime checks remain necessary.

## Shared Instances And Repeated Components Follow-Up

The compiler adapter now distinguishes source templates from supported local
component callsites. Development-only instance props/DOM markers identify static
same-module function-component uses without changing original JSX/TSX. Scope defaults
to `instance`; unique `jsx-instance` receipts target only `<Card .../>` props proven
directly forwarded to its intrinsic root. Static className/style/title overrides
preserve all other callsite props, handlers and children. Explicit `--scope template`
at both locate and validate enables shared intrinsic/callback source edits. Receipts
carry scope and observed count; the writer binds each validator to the correct scope.

Real Next.js 16.4.3 Turbopack browser Live selected the second of two visually
identical Card roots. Both shared one template ID and had distinct callsite IDs.
Detached preview/Accept, Babel validation and the locked writer changed exactly that
second callsite to class `instance-chosen` and font-weight 600. The shared Card
definition, first callsite and all neighboring bytes stayed unchanged. Real clicks
returned First and Second from their respective handlers. A third instance mounted
afterward remained weight 400 with no instance class, as did the first.

A separate explicit template cycle wrapped the shared heading in a header and added
a template marker. Only the shared intrinsic source range changed; all callsites and
the second callsite's unique style remained intact. Both existing roots and the
subsequently mounted third root received the header and template marker, retaining
weights 400/600/400. Their handlers returned First, Second and Third. Adjacent
paragraph/aside remained unchanged; browser console had no errors or warnings.
The template preview intentionally represented one selected example, not every
instance at once. The scope was stated before publication.

A full reload after the first source write removed the browser init capture. A
Generate without capture was rejected and acknowledged as an error without source
writes; a fresh init script/selection supplied the next valid receipt. No current-DOM
ordinal or native first-match fallback reconstructed that missing capture. A final
instance preview/Discard left source bytes unchanged and removed all preview wrappers.
Capture was disposed, Live exited and both test servers stopped.

Regression covers lexical shadowing, reassignment/aliases, wrong-root and cross-paired
markers, spread precedence, transformed/dynamic presentation props, duplicate/changed
bindings, callback callsites (including one current item), repeated parents, scope
mismatches, stale source and writer validator crossover. Actual Babel plus React SSR
also demonstrates isolated callsite output versus template-wide output. Exported
reusable component modules require template scope when local instance provenance is
missing; App Router default page entries retain their unique-surface flow.

`next build --turbopack` passed compilation, TypeScript and all five fixture outputs,
including `/instances`. The existing multiple-lockfile workspace-root warning remains.
Single-instance support is bounded to verified local presentation props: cross-module
callsite resolution, arbitrary helper/HOC reuse, single loop-item data overrides and
instance-only structural specialization are not claimed. Unsupported instance scope
refuses instead of being promoted to a shared-template write.

The final full suite passed all 86 tests with project Babel/React/Next and pinned
native-engine coverage enabled. Bundle freshness, skill metadata and whitespace
checks passed. Production server/static output contained no provenance/Live markers.

## Cross-Module, HOC And Keyed Item Follow-Up

Read-only lexical resolution now follows relative local imports, aliases, named/default
exports, namespace imports and unambiguous barrels. React import bindings identify
memo/forwardRef; simple HOC factories must prove unchanged prop forwarding. Receipts
bind caller, component, barrel and HOC hashes. The writer locks these sources through
flush; Windows read sharing prevents writes, appends and path replacement without ACL
changes. Contention/drift refuses before writing.

Direct synchronous map items use React-normalized keys. Index/duplicate keys, duplicate
key attrs, spreads, nested shared parents and mismatched dependencies/scopes refuse.
The canonical patch constructs the original element, then cloneElement overrides only
the selected key's presentation props. Both component and intrinsic rows are covered.
A needed React helper/type import and expression change commit in one write. Reorder
retains identity; prior specializations can be selected again and helpers are reused.

Project Babel/React SSR exposed that automatic JSX evaluates props before its separate
key argument. An initial pre-key cache design would have changed getter order and was
replaced before installation. Final checks compare original and specialized getter
order/count under classic and automatic transforms, repeated edits and reorder. Other
checks cover dependency drift, helper/type shadowing, normalized key collisions,
read/write contention, append/rename prevention and exact multi-edit source bytes.

Real Next.js 16.4.3 Turbopack Live selected the second identical static Card through
caller → barrel → memo/forwardRef component plus a separate pass-through HOC. Accept
changed only that callsite to 600. First Card and loop rows stayed 400. Exact source
comparison and hashes preserved component, barrel, HOC and all neighboring source.

Another real cycle selected loop key b (Beta). Its canonical patch added only the React
helper/type import and selected expression wrapper. Beta rendered at 700; Alpha stayed
400 and the static pair stayed 400/600. Reverse Items moved Beta ahead of Alpha without
transferring style; Add Item mounted Gamma at 400. Actual handlers returned Static
First, Static Second, a, b and c. Adjacent paragraph/aside were unchanged, with no browser
console warnings/errors. A fresh capture selected the keyed specialization again;
preview/Discard left source bytes unchanged and removed preview wrappers. Live then
reported no pending sessions; capture and both test servers were stopped.

`next build --turbopack` passed compilation, TypeScript and all six fixture outputs,
including `/module-items`. The existing multiple-lockfile warning remains. Support is
verified presentation props, not data/handler changes, structural specialization,
config/package aliases, opaque HOCs or custom memo comparators. Unsupported instance
identity is never widened into a template write.

The final full suite passed all 88 tests with actual project Babel/React/Next and
pinned native-engine checks enabled. Bundle freshness, skill metadata and whitespace
checks passed. Production server/static output contained no provenance/Live markers.
