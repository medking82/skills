---
name: design
description: Design and polish web or native app interfaces, including distinctive visual direction, motion, component feedback, mobile web, Apple interactions, Expo and Swift. Use for UI implementation or requested design audits, UI data stress tests, prototypes and UI library selection; not graphics, documents or backend work.
---

# Design

One entrypoint for the design-engineering collection. Choose the mode that answers the
request and read its linked guide; load additional modes only when the task crosses their
boundaries. Each guide's relative resources live beside it. Do not read this whole collection
for a component change.

## Impeccable playbook selection

For a UI design task, match the user's actual intent in Chinese or English to the
playbooks below. Select only those relevant to the requested scope; use more than
one when the user asks for distinct outcomes. Explicit user selections take
precedence, including `$design layout <target>` and requests naming an Impeccable
playbook. A negated playbook or forbidden action is not selected or performed.
When the scope is unclear, choose conservatively; do not infer all five from a
general request to improve a UI. Playbook selection precedes the general mode
table and Jev mode selection; Jev cannot override an explicit user choice.

| Name | Intent and examples | Impeccable playbook |
| --- | --- | --- |
| `layout` | spacing, grouping, alignment and layout; 间距、分组、布局 | [layout](references/impeccable/upstream/reference/layout.md) |
| `typeset` | font choices, text hierarchy and reading; 字体、字号、排版层级 | [typeset](references/impeccable/upstream/reference/typeset.md) |
| `distill` | simplify clutter, remove redundancy; 精简、去冗余 | [distill](references/impeccable/upstream/reference/distill.md) |
| `polish` | final refinement and consistency before shipping; 上线前打磨、一致性收尾 | [polish](references/impeccable/upstream/reference/polish.md) |
| `critique` | assess a design and identify issues; 设计评审、找问题 | [critique](references/impeccable/upstream/reference/critique.md) |

Consider intent and context, not isolated keyword matches. A typography request
is not automatically a layout request, and a request for component feedback is
not automatically a full shipping polish. Explicit animation review still uses
`review-animations` unless the user selects an Impeccable playbook too. Keep the
other opt-in modes and the general mode table below available for their actual
purposes. For multiple selected playbooks, follow any stated order; otherwise
choose a sensible order within scope. Clarify only an actual unresolved conflict.
A request for critique or a question seeking advice or comparison alone is not
authorization to edit; answer or review without implementation unless the user
requests changes too. An action request phrased as a question, such as “能帮我
调整间距吗？”, is a request to make that change.

Before using the selected playbooks, give one concise sentence naming them and
why they fit. Read the Impeccable mode guide and each selected playbook. Only
say a playbook was loaded after its file was successfully read. If a file is
missing or unreadable, say which one failed and use the applicable general design
mode as a clearly identified fallback; do not claim the playbook was followed.
Report the concrete checks and actual verification performed; guidance or a
clean detector result alone is not evidence of rendered or device behavior.
Selection does not automatically start a browser, live mode, external reviewer or publication, or expand project changes or other permissions.
Follow the user's tools, scope, explicit choices, and the mode guide's boundaries.

Examples are routing expectations, not a claim that a model has been tested:

- “调整间距和布局” → `layout`; “Improve the type scale” → `typeset`.
  “能帮我调整间距吗？” is an action request → `layout` with implementation.
- “精简设置页并优化字号” → `distill` + `typeset`.
- “Review this design, then polish the issues” → `critique` then `polish`;
  critique alone remains review-only.
- “How should I simplify this screen?” may consult `distill` for advice, but
  does not edit. “不要改字体，只调整间距” selects `layout`, not `typeset`.
- “Review the animation” uses the explicit motion-review mode, not an automatic
  full design critique. A non-UI backend request does not invoke these playbooks.

## Choose the mode

| Request | Mode and guide |
| --- | --- |
| Distinctive visual direction, broader UI composition or an explicitly requested visual critique | [impeccable](references/impeccable/guide.md) |
| Component feedback, cohesion or accessibility outside selected playbooks | [emil-design-eng](references/emil-design-eng/guide.md) |
| Implement web motion or transitions | [animate](references/animate/guide.md) |
| Implement React Native / Expo motion, gestures or haptics | [animate-expo](references/animate-expo/guide.md) |
| Fix janky or dropping-frame web animation, or work inside the frame budget | [animation-performance](references/animation-performance/guide.md) |
| Name a described animation or effect | [animation-vocabulary](references/animation-vocabulary/guide.md) |
| Apple interaction principles, springs, materials, typography or iPhone Home Screen apps | [apple-design](references/apple-design/guide.md) |
| Fix mobile-web viewport, touch, scroll, safe-area or browser behavior | [mobile-native](references/mobile-native/guide.md) |
| Set up, style or troubleshoot Sonner toasts | [ask-sonner](references/ask-sonner/guide.md) |
| Swift implementation, concurrency or performance in a native-app task | [write-swift](references/write-swift/guide.md) |
| Find useful motion opportunities in existing UI | [find-animation-opportunities](references/find-animation-opportunities/guide.md) |
| Audit a codebase's existing motion and propose improvements | [improve-animations](references/improve-animations/guide.md) |
| Explicitly stress-test UI with worst-case data or find data edge cases | [break-ui](references/break-ui/guide.md) |
| Explicitly critique motion or review an animation diff | [review-animations](references/review-animations/guide.md) |
| Explicitly choose or compare UI libraries | [pick-ui-library](references/pick-ui-library/guide.md) |
| Explicitly explore different UI variants behind a visual picker | [prototype](references/prototype/guide.md) |

For a new or substantially redesigned interface, start with `impeccable` when its visual
direction matters. For focused component work outside selected playbooks, use `emil-design-eng`. Prefer
`ask-sonner` for a Sonner problem and the platform-specific mode for mobile work. A naming
question ends with the term; an audit ends with findings or a plan. Implement when
implementation is part of the request.

## Jev-Assisted Mode Selection

When the unified `$jev` skill is available and two or more modes plausibly fit, use its
`design` helper with a short description of the current request as a second opinion on
the main LLM's mode choice. Reuse a design-mode recommendation already supplied by the
Jev turn hook. On same-layer disagreement, recheck the request, opt-in constraints and
guide evidence once, then choose the mode and read its guide without another Jev call.
Explicit mode names, clear single-mode requests and ordinary component polish need no
extra routing call. If Jev abstains or is unavailable, choose from this table normally.

Give a concise, truthful routing receipt with the selection: say whether this
turn reused its hook recommendation, called the helper, or needed or allowed no
call. For an actual hook or helper result, include only the returned `status`,
`mode`, `source`, and `requests` when present. A helper invocation is not
necessarily a remote Jev request: `source:local` with `requests:0` is local;
`source:fallback` / `status:fail_open` is an abstention. Reusing a hook result
is not a new call. An absent result stays absent; Jev `status`
reports a previous observation and is not evidence that this turn called Jev.
Send only minimal non-sensitive context to the helper, respecting tool bans and
explicit model, effort, Fast, and scope choices. On failure, low confidence,
malformed response, or local fallback, treat the result as an abstention, choose
locally, and report the fallback without retrying. Jev selects among mode guides,
not the five individual playbooks, and never grants permission or proves work.
If a selected playbook leaves a genuine choice between additional mode guides,
apply the same one-call Jev rule; a playbook selection does not suppress it.

The helper's default candidate set excludes the four explicit modes below. Include one
in `allowed_modes` only when the actual user request authorizes it; a Jev recommendation
does not expand task scope. Preserve the user's model, effort, Fast, tool bans and UI copy
preferences. The main LLM owns the final route, design judgment and validation.
Jev abstention or local fallback is not disagreement. `native-review` remains the owner
of admitted code review; a routing disagreement does not start one.

## Invocation and scope

The four explicit modes remain opt-in: `prototype`, `pick-ui-library`,
`review-animations`, and `break-ui`. Mentioning `$design` alone does not select them. Select
them when the user asks for variants/prototyping, dependency recommendations/comparison,
a motion critique/review, or UI stress-testing with worst-case data or data edge cases
respectively. Ordinary UI building or polish does not require a picker, library-selection
pass, codebase audit, motion review, or adversarial data test.

`break-ui` changes fixtures at the existing data boundary and uses a dev-only data toggle.
It reports failures and proposed fixes, then stops; apply fixes only when the user asks.
A request to stress-test alone does not authorize redesign or production controls.

Names of other design Skills inside the guides refer to the modes in the table above.
Follow the local guide link when a mode change is warranted; no separate Skill installation
is required. Do not automatically chain modes or invoke a mode outside the user's scope.
`review-animations` provides design evidence and does not replace a repository's code-review
or release owner.

## Apply guidance to the actual project

Preserve the user's framework, dependencies, tokens, design system and explicit choices.
Treat curated style, frequency, timing and library advice as defaults with a reason; do not
turn a deliberate, justified product choice into a defect. Check the project's actual
toolchain and current official API documentation before using version-sensitive examples,
particularly Expo/Reanimated and Swift. A guide's release claims are historical context,
not proof of current compatibility.

Apply keyboard, pointer, reduced-motion and contrast guidance where relevant to the changed
interaction. Use the project's relevant checks and available visual/device evidence; state
what remains unverified. A code inspection or desktop emulation alone does not establish
real-device feel or frame performance.
