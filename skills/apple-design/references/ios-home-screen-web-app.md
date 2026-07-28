# iPhone Home Screen web apps

Use this profile for web apps that must remain excellent in a browser and feel complete when
launched from an iPhone Home Screen. Treat “app-like” as a product-shell and lifecycle quality
bar, not permission to imitate native chrome or promise native capabilities.

## Contents

- [Start with both modes](#start-with-both-modes)
- [Own identity and launch](#own-identity-and-launch)
- [Replace missing browser chrome](#replace-missing-browser-chrome)
- [Design for the physical screen](#design-for-the-physical-screen)
- [Handle lifecycle and optional capabilities](#handle-lifecycle-and-optional-capabilities)
- [Keep the Apple character restrained](#keep-the-apple-character-restrained)
- [Readiness checklist](#readiness-checklist)

## Start with both modes

- Keep core tasks usable in an ordinary browser. Enhance standalone mode without creating a
  second, inconsistent application.
- For an audit, report evidence and gaps. For an authorized change, implement the smallest
  complete capability instead of stopping at generic advice.
- Before editing, locate the live route and the existing owners of root metadata, navigation,
  authentication returns, fixed UI, storage, network state, and Service Worker updates. Prefer
  shared shell fixes over repeated page-level patches.
- Detect capabilities and applied display mode rather than parsing an iOS version:

```js
const standalone = window.matchMedia('(display-mode: standalone)').matches;
```

Use `@media (display-mode: standalone)` for presentation-only differences. Feature-detect
Service Workers, Notifications, Push, Badging, Wake Lock, and orientation APIs at the point of
use. Missing optional APIs must not block the main task.

## Own identity and launch

Use the framework's manifest or metadata mechanism to define:

- a stable `id`;
- recognizable `name` and `short_name`;
- deliberate `start_url` and `scope` values that preserve authentication and deep links;
- `display: "standalone"` unless another mode has a demonstrated purpose;
- `theme_color` and `background_color` that match the first rendered frame; and
- tested icons whose important artwork remains inside the safe zone.

On iOS and iPadOS 26, users can open any Home Screen site as a web app; earlier applicable
versions use the manifest `display` value or legacy metadata to request standalone behavior.
A manifest still provides identity and launch configuration, and a Service Worker is not an
iOS installation requirement. If both are present, `apple-touch-icon` takes precedence over
manifest-declared icons, so keep the two sources intentional and consistent.

## Replace missing browser chrome

When browser controls disappear:

- Keep the current location and top-level destinations understandable.
- Provide visible back, close, cancel, or done actions where browser chrome supplied the only
  exit. Never trap the user.
- Preserve real URLs, deep links, and browser history.
- Treat OAuth, payments, downloads, and external links as lifecycle transitions. Preserve the
  intended return URL and reconcile state on return.
- Restore useful context after relaunch when appropriate, without bypassing authentication or
  reviving sensitive state unexpectedly.

## Design for the physical screen

Opt into edge-to-edge layout deliberately. If using `viewport-fit=cover`, expose shared safe-area
tokens from the shell:

```css
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
}

.app-shell {
  padding-inline: max(1rem, var(--safe-left)) max(1rem, var(--safe-right));
}
```

Apply the same contract to headers, tab bars, floating controls, sheets, dialogs, banners,
toasts, and update prompts. Test portrait, landscape, the software keyboard, and dynamic viewport
changes; do not freeze layout to the initial viewport height or double-apply keyboard and safe-area
offsets.

Give touch targets adequate area and separation, respond visually on touch-down, and preserve
cancel-by-dragging-away. Keep visible alternatives for swipe actions, avoid stealing system edge
gestures, and preserve selection, zoom, copy/paste, password managers, and autofill.

## Handle lifecycle and optional capabilities

Define distinct loading, empty, offline, reconnecting, error, and update-ready states. Preserve
unsent work across recoverable failures when practical.

If offline continuity matters, choose a bounded cache policy, identify which reads and writes
work offline, avoid retaining sensitive data by default, and make sync conflicts understandable.
Keep one Service Worker/update owner. Never surprise-reload merely because a new worker is ready;
respect dirty-state guards and reload at a safe point.

Treat install education, notifications, push, badges, wake lock, and orientation lock as earned
enhancements:

- Explain the value before prompting and accept dismissal.
- Request notification permission only from a clear user action.
- Use notifications and badges for timely utility, not re-engagement noise.
- Feature-detect `setAppBadge` and `clearAppBadge`; on iOS and iPadOS a badge appears only after
  notification permission is granted.

## Keep the Apple character restrained

Use translucent or Liquid Glass-like treatment on the functional layer of controls and
navigation, not across content. Prefer clarity, feedback, and familiar behavior over copied
system chrome, fake home indicators, blur, or oversized corner radii.

Support text scaling, screen readers, logical focus, external keyboards, reduced motion, reduced
transparency, increased contrast, zoom, and orientation changes. Report which contexts were
actually tested.

## Readiness checklist

- [ ] Core tasks work in browser and applied standalone modes.
- [ ] Manifest identity, launch URL, scope, colors, and icons are intentional.
- [ ] Launch, relaunch, deep links, back/close paths, and external returns preserve orientation.
- [ ] Safe areas, rotation, the software keyboard, and system gestures do not cover controls.
- [ ] Shared fixed UI and overlays consume one inset contract.
- [ ] Loading, offline, reconnecting, error, and update-ready states are distinct.
- [ ] Unsent work, cache policy, and Service Worker updates have explicit behavior.
- [ ] Install, notification, push, and badge prompts follow understandable user intent.
- [ ] Touch, scrolling, selection, zoom, autofill, and accessibility preferences work.
- [ ] Tested contexts and known gaps are reported.

## Primary references

- [WebKit: WebKit Features in Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)
- [WebKit: Web Push for Web Apps on iOS and iPadOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [WebKit: Badging for Home Screen Web Apps](https://webkit.org/blog/14112/badging-for-home-screen-web-apps/)
- [WebKit: Designing Websites for iPhone X](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [W3C: Web Application Manifest](https://www.w3.org/TR/appmanifest/)
