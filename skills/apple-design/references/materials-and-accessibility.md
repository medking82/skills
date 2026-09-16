# Materials and accessibility

Translucency can establish a floating layer, but it is not automatically clearer. Use blur and
alpha only after checking the content underneath. Consult the current
[Apple Materials HIG](https://developer.apple.com/design/human-interface-guidelines/materials)
and [adoption guidance](https://developer.apple.com/documentation/technologyoverviews/adopting-liquid-glass)
for native design. The [Safari 18 note](https://webkit.org/blog/15865/webkit-features-in-safari-18-0/)
is historical browser compatibility context, not a claim of current Apple feature parity.

## Material choice

Apple separates Liquid Glass controls/navigation from standard materials in the content layer.
Use standard materials for content backgrounds; avoid spreading custom glass across every card.
The regular Liquid Glass variant prioritizes legibility; clear is intended for media-rich
backgrounds. Respect system contrast and transparency preferences. Choose native material roles
by purpose rather than hard-coding the tint seen in one screenshot.

## Platform implementation

Web `backdrop-filter` approximates a visual effect; it does not implement native Liquid Glass.
For desktop frameworks, verify the actual backend, supported OS version and achieved material,
not merely whether a transparency hint was accepted. AppKit's
[NSVisualEffectView](https://developer.apple.com/documentation/appkit/nsvisualeffectview)
is a native reference, not evidence that a cross-platform framework exposes the same behavior.

Change background alpha independently of text and controls. Whole-window opacity also fades
foreground content. Zero-alpha surfaces can change native hit testing: verify movement, resizing,
controls, and intentional mouse-through separately. Check real light, dark and textured backgrounds;
a screenshot alone does not prove input behavior. If an effect is unavailable, retain a usable solid
surface. Measure expensive blur/capture work in the target app before adopting continuous effects.

- Keep text and controls readable over the real background; add a solid or more opaque fallback.
- Do not stack translucent surfaces by default. Use contrast, spacing, and shadow before another
  effect.
- Feature detect `backdrop-filter`; preserve layout and meaning when it is absent.
- A modal may use a scrim; a non-blocking panel should not dim available work.

Motion and material effects are optional communication layers. Respect `prefers-reduced-motion` by
removing large travel, parallax, and elastic overshoot while retaining short opacity/color changes
or an equivalent static state. Where supported, respect `prefers-reduced-transparency` with a more
opaque surface. Maintain visible keyboard focus and a useful contrast mode. Sound and vibration
are optional, platform-dependent enhancements; never make them the only confirmation.

Check focus order, focus visibility, contrast, enlarged text, horizontal overflow, and the usable
fallback in the target browser. These are acceptance checks for the consumer, not a generic suite.
