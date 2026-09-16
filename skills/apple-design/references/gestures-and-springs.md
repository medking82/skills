# Gestures and springs

Apple's motion guidance is a behavioral model: respond immediately, track continuously, carry
momentum, and let the user redirect motion. It does not define a web API or universal physics
constant. See [Apple Motion](https://developer.apple.com/design/human-interface-guidelines/motion/)
and [Pointer Events capture](https://www.w3.org/TR/pointerevents/#setting-pointer-capture).

## Direct manipulation

On `pointerdown`, record the grab offset and call `setPointerCapture` when the component owns the
gesture. Update the presented position continuously. Keep a short timestamped history so release
velocity is available. On interruption, cancel the old animation and read the live presented value;
starting from a stale target produces a jump. Carry release velocity into new motion when supported.

Pressed feedback starts on pointer-down; activation normally commits on release and can be
cancelled by moving away. Keep gesture recognition thresholds distinct from visual feedback:
the user should see a response while drag intent is still being resolved. Handle pointer cancellation
and lost capture so an interrupted drag cannot leave a stuck pressed state.

CSS transitions and keyframes are valid for simple state changes. For a gesture-driven value they
need explicit interruption handling and a current-value handoff; a spring library often supplies
that behavior. Do not ban CSS categorically, and do not lock input during a transition.

## Parameter vocabulary

Apple's SwiftUI spring documentation describes `response`, `dampingFraction`, and `blendDuration`:
[SwiftUI spring](https://developer.apple.com/documentation/swiftui/spring). Motion's spring API
uses a different parameterization; consult [Motion spring](https://motion.dev/docs/spring).
Treat a conversion as an approximation and record the library/version with the chosen values.

- Start ordinary repositioning with no overshoot and a short response.
- Reserve bounce for a gesture that supplied momentum or a deliberate playful affordance.
- Tune X and Y independently when their velocity or bounds differ.
- Project a flick only when the component has a clear snap model; clamp the result at safe bounds.

For snapping, select a target from the projected stopping position when momentum is part of the
interaction, then hand off velocity using the library's documented units. Do not import a UIKit
deceleration constant as a universal desktop value. Anchor popovers to their trigger and preserve
spatial continuity on dismissal; changing direction midway must not restart from the old endpoint.

```js
// Exact options depend on the selected library; velocity uses that library's units.
animate(element, { y: target }, {
  type: 'spring', bounce: 0, duration: 0.4, velocity: releaseVelocity
});
```

## Boundaries and verification

Use progressive resistance at a meaningful boundary and give the user a clear return path. Test
the actual component for pointer capture, cancel/reverse, keyboard operation, reduced motion, and
overflow at enlarged text. Avoid asserting a frame-perfect result when browser scheduling varies.
