---
name: emil-design-eng
description: Apply Emil Kowalski's design-engineering principles to UI polish, component feedback, and interaction quality. Use when implementing or assessing interface details; route focused motion tasks to the specialized animation skills.
---

# Design Engineering

Start from the user's requested outcome and the existing product conventions. Apply only the
principles relevant to the component; selecting this skill does not require a full UI audit,
new dependencies, a browser harness, or a prescribed review report.

## Route by task

- For implementing web motion, use `animate`; for React Native motion, use `animate-expo`
  when available.
- For an explicitly requested motion review, use `review-animations`; for a codebase motion
  audit or plan, use `improve-animations`.
- For broader component polish, read the relevant sections of
  [the craft guide](references/craft-guide.md): Component Building Principles, Accessibility,
  The Sonner Principles, or Cohesion.
- For gestures or performance, read Gesture and Drag Interactions and Performance Rules in
  that guide. Verify API support and behavior against the project's library version.
- `prototype` and `pick-ui-library` remain explicit-only; do not invoke them automatically.

## Working principles

Preserve the project's tokens, dependencies, scope, and explicit user choices. Give feedback
promptly, preserve interruption and cancellation, and keep controls accessible by keyboard.
Choose motion for a concrete purpose and usage frequency; ordinary UI should be quick and
restrained. Prefer transform and opacity where they fit, with measured layout exceptions for
interactions such as accordions. Honor reduced motion and pointer capabilities.

The guide's curves and timings are starting points, not mandatory replacements for deliberate
product choices. Its review table is useful for comparisons when requested; otherwise use the
output format that best answers the user. A documented style preference is not automatically
a defect. Do not claim hardware acceleration or verified feel solely from code.

For an authorized change, implement the smallest coherent improvement and run the project's
relevant checks. Report what changed, evidence, and any visual or device behavior still unverified.
For a discussion or review request, provide the requested analysis without modifying source.
