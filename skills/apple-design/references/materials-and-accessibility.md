# Materials and accessibility

Translucency can establish a floating layer, but it is not automatically clearer. Use blur and
alpha only after checking the content underneath. WebKit documents current `backdrop-filter`
behavior in [Safari 18 features](https://webkit.org/blog/15865/webkit-features-in-safari-18-0/).

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
