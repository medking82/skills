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
