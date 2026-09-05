---
name: apple-design
description: Apple's interface principles translated for web work involving gesture-driven UI, spring motion, sheets, momentum, materials, typography, accessibility, or iPhone-focused PWAs. Use the smallest relevant reference for the request.
---

# Apple Design

Use this skill when interaction quality is part of the work. Treat Apple's Human Interface
Guidelines (HIG) as design heuristics; confirm each web capability against the platform before
depending on it. The aim is a responsive interface that is clear, forgiving, and physically
coherent, not an imitation of a native API.

## Route first

- For drag, swipe, sheet, carousel, or interruptible motion, read
  [`references/gestures-and-springs.md`](references/gestures-and-springs.md).
- For blur, translucency, contrast, focus, or reduced motion/transparency, read
  [`references/materials-and-accessibility.md`](references/materials-and-accessibility.md).
- For optical sizing, tracking, leading, or responsive type, read
  [`references/typography.md`](references/typography.md).
- For an iPhone Home Screen web app, standalone mode, safe areas, or app-shell behavior, read
  [`references/ios-home-screen-web-app.md`](references/ios-home-screen-web-app.md).

Do not load every reference for a simple request. A design discussion alone does not require a
browser inspection or code change. When implementing, establish an observable interaction bar:
feedback begins on input, the user can interrupt it, focus remains reachable, content does not
silently overflow, and reduced-motion behavior is testable.

## Shared principles

Feedback should be immediate and specific. Direct manipulation tracks the grabbed offset, keeps
the content and pointer together, and uses pointer capture where appropriate. A transition should
start from the current presented value and preserve velocity when the user reverses or releases;
do not disable input while an animation is running.

Use springs when the interaction has a changing target or momentum. Choose parameters by the
library's documented model: Apple describes damping ratio and response, while Motion and other
web libraries expose their own mappings. Do not claim that `duration`, `bounce`, stiffness, or
damping values are numerically interchangeable across libraries. Put the mapping and examples in
the gesture reference.

Use materials to express hierarchy only when they improve separation and legibility. Provide a
solid or higher-opacity fallback, check text contrast over the actual background, and feature
detect web effects. Typography should follow the platform system font and size-specific metrics;
manual tracking is an evidence-based adjustment, never a universal default.

Accessibility is part of the interaction: preserve keyboard focus and visible focus, honor
`prefers-reduced-motion`, `prefers-reduced-transparency`, and contrast preferences when available,
and keep the essential action understandable without motion, blur, sound, or haptics. Browser
Vibration/haptic support is optional; never make task completion depend on it.

## Verification prompts

For a changed interaction, verify with the narrowest available checks that:

1. Pointer/keyboard focus reaches the control and remains visible.
2. Long labels or enlarged text do not clip or create unintended horizontal overflow.
3. The reduced-motion mode removes large travel, parallax, and elastic overshoot while retaining
   status and completion feedback.
4. A missing blur, vibration, or motion API leaves a usable fallback.

Use a real prototype or consumer-specific test when visual behavior matters. Do not invent a
generic browser harness merely because this skill was selected.
