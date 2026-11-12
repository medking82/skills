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
Impeccable playbooks. Select only those relevant to the requested scope; use more than
one when the user asks for distinct outcomes. Explicit user selections take
precedence, including `$design layout <target>` and requests naming an Impeccable
playbook. A negated playbook or forbidden action is not selected or performed.
When the scope is unclear, choose conservatively; do not infer several playbooks from a
general request to improve a UI. Playbook selection precedes the general mode
table and ambiguous mode selection; neither overrides an explicit user choice.

| Name | Category | Intent and examples | Impeccable playbook |
| --- | --- | --- | --- |
| `critique` | Evaluate | UX design review, find and rank issues; 设计审查、设计评审、找问题 | [critique](references/impeccable/upstream/reference/critique.md) |
| `audit` | Evaluate | technical checks: accessibility, contrast, performance, responsive; 无障碍、对比度、上线前技术检查 | [audit](references/impeccable/upstream/reference/audit.md) |
| `layout` | Enhance | spacing, grouping, alignment, rhythm; 间距、分组、对齐、布局 | [layout](references/impeccable/upstream/reference/layout.md) |
| `typeset` | Enhance | fonts, type scale, text hierarchy; 字体、字号、排版层级 | [typeset](references/impeccable/upstream/reference/typeset.md) |
| `colorize` | Enhance | add strategic color to a grey or dull UI; 配色太灰、更有活力 | [colorize](references/impeccable/upstream/reference/colorize.md) |
| `animate` | Enhance | add purposeful motion to a UI; 加动效 | [animate](references/impeccable/upstream/reference/animate.md) |
| `delight` | Enhance | personality and memorable touches; 小惊喜、记忆点细节 | [delight](references/impeccable/upstream/reference/delight.md) |
| `overdrive` | Enhance | push past conventional limits, only when asked; 突破常规 | [overdrive](references/impeccable/upstream/reference/overdrive.md) |
| `distill` | Refine | simplify, remove clutter and complexity; 精简、去冗余、太复杂 | [distill](references/impeccable/upstream/reference/distill.md) |
| `quieter` | Refine | tone down loud, busy or overstimulating designs; 太吵、太花、收敛 | [quieter](references/impeccable/upstream/reference/quieter.md) |
| `bolder` | Refine | amplify a safe, bland or forgettable design; 太平淡、太保守、更大胆 | [bolder](references/impeccable/upstream/reference/bolder.md) |
| `polish` | Refine | final consistency pass before shipping; 上线前打磨、细节收尾 | [polish](references/impeccable/upstream/reference/polish.md) |
| `harden` | Refine | make UI production-ready: errors, empty data, long text, i18n; 处理错误/空状态/超长文字/多语系 | [harden](references/impeccable/upstream/reference/harden.md) |
| `onboard` | Refine | first-run flows, empty states, activation; 新用户引导、首次使用 | [onboard](references/impeccable/upstream/reference/onboard.md) |
| `clarify` | Fix | UX copy, labels, error messages; 文案、按钮文字、错误讯息看不懂 | [clarify](references/impeccable/upstream/reference/clarify.md) |
| `adapt` | Fix | other devices and screen sizes; 平板、手机、响应式 (native: adapt.native.md) | [adapt](references/impeccable/upstream/reference/adapt.md) |
| `optimize` | Fix | diagnose and fix UI performance; 页面卡顿、渲染慢 | [optimize](references/impeccable/upstream/reference/optimize.md) |
| `shape` | Build | plan UX and UI before code; 先规划流程和页面结构、不写程序 | [shape](references/impeccable/upstream/reference/shape.md) |
| `extract` | Build | pull shared tokens and components into a design system; 抽成 design tokens、共用元件 | [extract](references/impeccable/upstream/reference/extract.md) |
| `document` | Build | write DESIGN.md from existing code, only when asked | [document](references/impeccable/upstream/reference/document.md) |
| `init` | Build | capture product context in PRODUCT.md, only when asked | [init](references/impeccable/upstream/reference/init.md) |
| `live` | Iterate | browser variant iteration, only when explicitly requested | [live](references/impeccable/upstream/reference/live.md) |
| `generate` | Iterate | variants of a named element in the live browser, only when explicitly requested | [generate](references/impeccable/upstream/reference/generate.md) |

This table lists every current Impeccable command (`craft` is a deprecated alias for
ordinary new work). Read the linked playbook directly; the Impeccable mode guide and the
upstream command table are not required first. `harden` fixes edge cases inside the
requested work; `break-ui` only stress-tests with worst-case data and stays opt-in.
Smoother or janky existing motion (流畅、丝滑、掉帧) belongs to the motion modes below
(`animation-performance`, `improve-animations`), not `animate`, which adds new motion.
Choose the playbook or mode from the request before looking for project files. Honor
aliases and platform-specific references in the
[upstream command table](references/impeccable/upstream/guide.md#commands).
Combine an Impeccable playbook with an Emil mode when both contribute to the requested
work; a shared name does not force an either-or choice. `live` and
`generate` remain available for requested visual iteration, within the user's tool
permissions; an ordinary design request does not start them.

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
why they fit. Read each selected playbook, and the Impeccable mode guide when a new or
substantially revised visual direction is involved. Only
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
- “让配色更有活力” → `colorize`; “改善新用户引导” → `onboard`.
- “修复手机页面的触控和布局” may combine `adapt` with `mobile-native`.
- “How should I simplify this screen?” may consult `distill` for advice, but
  does not edit. “不要改字体，只调整间距” selects `layout`, not `typeset`.
- “Review the animation” uses the explicit motion-review mode, not an automatic
  full design critique. A non-UI backend request does not invoke these playbooks.

## Choose the mode

| Request | Mode and guide |
| --- | --- |
| Distinctive visual direction, broader UI composition or an explicitly requested visual critique | [impeccable](references/impeccable/guide.md) |
| New marketing, brand or campaign web page or landing page from scratch, a named Hallmark redesign, or an audit of a web page for AI tells (去 AI 味) | [hallmark](references/hallmark/guide.md) |
| Component feedback, cohesion or accessibility outside selected playbooks | [emil-design-eng](references/emil-design-eng/guide.md) |
| Implement web motion or transitions | [animate](references/animate/guide.md) |
| Coordinate several elements that move together: stagger, sequencing, entrances, view swaps or multi-step transitions | [choreograph](references/choreograph/guide.md) |
| Build or fix web drag, swipe, sheet, drawer, fling or hold-to-confirm interactions that must track the finger and stay interruptible | [gestures](references/gestures/guide.md) |
| Implement React Native / Expo motion, gestures or haptics | [animate-expo](references/animate-expo/guide.md) |
| Fix janky or dropping-frame web animation, or work inside the frame budget | [animation-performance](references/animation-performance/guide.md) |
| Remove excessive or unnecessary motion | [remove-animations](references/remove-animations/guide.md) |
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
| Explicitly capture design corrections and preferences from the current session in DESIGN.md | [learn-taste](references/learn-taste/guide.md) |

The [mode inventory](references/sources.json) lists all bundled modes, including
new modes from upstream, with descriptions, guide paths and invocation policy.
When the table does not cover the request or the user names another mode, inspect
the inventory's `modes` section and read the relevant guide. Respect
`allow_implicit_invocation: false` and the user's scope. The main LLM can select a
newly bundled mode as soon as the inventory lists it.

For a new or substantially redesigned interface, start with `impeccable` when its visual
direction matters. A new marketing, brand or campaign web page built from scratch uses
`hallmark` instead; app UI such as dashboards, admin screens, editors and tools stays with
`impeccable`, and Hallmark never takes over an existing design unless the user names it or
asks for an AI-tell audit. For focused component work outside selected playbooks, use `emil-design-eng`. Prefer
`ask-sonner` for a Sonner problem and the platform-specific mode for mobile work. A naming
question ends with the term; an audit ends with findings or a plan. Implement when
implementation is part of the request.

## Ambiguous Mode Selection

When two or more modes plausibly fit, the main LLM chooses the mode itself. Recheck the
request, opt-in constraints and the candidate guides' descriptions once, then choose the
mode and read its guide. No external routing helper or second opinion is involved.
Explicit mode names, clear single-mode requests and ordinary component polish need no
extra routing deliberation; choose from the table above directly.

For an unresolved choice involving `remove-animations` or a newly indexed mode, compare
only the relevant allowed mode names and descriptions from the inventory, and keep a
no-match outcome available when none fits. Explicit modes and independent requested
outcomes need no choice.

Give a concise, truthful routing receipt with the selection: name the chosen mode and
why it fits. The main LLM selects both the mode guides and the applicable Impeccable
playbooks. Neither selection grants permission or proves work.
If a selected playbook leaves a genuine choice between additional mode guides,
choose between them the same way; a playbook selection does not suppress that choice.

Candidates exclude the four explicit modes below unless the actual user request
authorizes one; mode selection does not expand task scope. Preserve the user's model,
effort, Fast, tool bans and UI copy preferences. The main LLM owns the final route,
design judgment and validation. `native-review` remains the owner of admitted code
review; a routing ambiguity does not start one.

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
