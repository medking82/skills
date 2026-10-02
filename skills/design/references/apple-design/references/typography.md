# Typography

Apple's [Typography HIG](https://developer.apple.com/design/human-interface-guidelines/typography/)
supports hierarchy that adapts to size and context. Start with the platform system font and let
its metrics do the work. Use `rem`/`em` spacing where text can scale, and test with large user text.

- Set line height by reading size and script, not one global constant.
- Treat tracking as size-specific. Large display text may need slight negative tracking; dense or
  small text may need a small positive adjustment. Body text often stays near the font default.
- Change weight, size, and leading together to establish hierarchy.
- Use `font-optical-sizing: auto` when the selected font supports it.
- Add manual `letter-spacing` only for a measured visual problem and record the context.

```css
:root { font: 100%/1.5 system-ui, sans-serif; }
.display {
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1.05;
  letter-spacing: -0.02em;
  font-optical-sizing: auto;
}
```

Verify wrapping, clipping, focus visibility, and horizontal overflow at the largest supported
text size. Do not trade readable text for a visual match at the default viewport.
