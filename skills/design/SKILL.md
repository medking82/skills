---
name: design
description: Design and polish web or native app interfaces, including distinctive visual direction, motion, component feedback, mobile web, Apple interactions, Expo and Swift. Use for UI implementation or requested design audits, UI data stress tests, prototypes and UI library selection; not graphics, documents or backend work.
---

# Design

One entrypoint for the design-engineering collection. Choose the mode that answers the
request and read its linked guide; load additional modes only when the task crosses their
boundaries. Each guide's relative resources live beside it. Do not read this whole collection
for a component change.

## Choose the mode

| Request | Mode and guide |
| --- | --- |
| Distinctive visual direction, broader UI composition or an explicitly requested visual critique | [impeccable](references/impeccable/guide.md) |
| Component polish, feedback, spacing, cohesion or accessibility | [emil-design-eng](references/emil-design-eng/guide.md) |
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
direction matters. For focused interface polish, start with `emil-design-eng`. Prefer
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
