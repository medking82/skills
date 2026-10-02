---
name: design
description: Design and polish web or native app interfaces, including motion, component feedback, mobile web, Apple interactions, Expo and Swift. Use for UI implementation or requested design audits, prototypes and UI library selection; not graphics, documents or backend work.
---

# Design

One entrypoint for the design-engineering collection. Choose the mode that answers the
request and read its linked guide; load additional modes only when the task crosses their
boundaries. Each guide's relative resources live beside it. Do not read this whole collection
for a component change.

## Choose the mode

| Request | Mode and guide |
| --- | --- |
| Component polish, feedback, spacing, cohesion or accessibility | [emil-design-eng](references/emil-design-eng/guide.md) |
| Implement web motion or transitions | [animate](references/animate/guide.md) |
| Implement React Native / Expo motion, gestures or haptics | [animate-expo](references/animate-expo/guide.md) |
| Name a described animation or effect | [animation-vocabulary](references/animation-vocabulary/guide.md) |
| Apple interaction principles, springs, materials, typography or iPhone Home Screen apps | [apple-design](references/apple-design/guide.md) |
| Fix mobile-web viewport, touch, scroll, safe-area or browser behavior | [mobile-native](references/mobile-native/guide.md) |
| Set up, style or troubleshoot Sonner toasts | [ask-sonner](references/ask-sonner/guide.md) |
| Swift implementation, concurrency or performance in a native-app task | [write-swift](references/write-swift/guide.md) |
| Find useful motion opportunities in existing UI | [find-animation-opportunities](references/find-animation-opportunities/guide.md) |
| Audit a codebase's existing motion and propose improvements | [improve-animations](references/improve-animations/guide.md) |
| Explicitly critique motion or review an animation diff | [review-animations](references/review-animations/guide.md) |
| Explicitly choose or compare UI libraries | [pick-ui-library](references/pick-ui-library/guide.md) |
| Explicitly explore different UI variants behind a visual picker | [prototype](references/prototype/guide.md) |

For general interface work, start with `emil-design-eng`. Prefer `ask-sonner` for a Sonner
problem and the platform-specific mode for mobile work. A naming question ends with the term;
an audit ends with findings or a plan. Implement when implementation is part of the request.

## Invocation and scope

The three explicit modes remain opt-in: `prototype`, `pick-ui-library`, and
`review-animations`. Mentioning `$design` alone does not select them. Select them when the
user asks for variants/prototyping, dependency recommendations/comparison, or a motion
critique/review respectively. Ordinary UI building or polish does not require a picker,
library-selection pass, codebase audit, or review.

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
