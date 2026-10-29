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

Boundaries: the adapter supports uniquely matched, well-formed true HTML block source.
Identical siblings without a distinguishing parent, inline-sensitive elements,
framework templates, generated HTML, and parser/browser structural disagreement
require the existing source-aware fallback. It refuses rather than guessing.
