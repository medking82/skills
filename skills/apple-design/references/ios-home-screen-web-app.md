# iPhone Home Screen web apps

Use this profile for mobile web apps that should remain excellent in a browser and feel complete
when launched from an iPhone Home Screen. Treat “app-like” as a product-shell and lifecycle
quality bar, not permission to imitate native chrome or promise native capabilities.

## Contents

- [Start with the requested mode](#start-with-the-requested-mode)
- [Map the live app before editing](#map-the-live-app-before-editing)
- [Preserve the browser baseline](#preserve-the-browser-baseline)
- [Define identity and launch behavior](#define-identity-and-launch-behavior)
- [Build a complete shell without browser chrome](#build-a-complete-shell-without-browser-chrome)
- [Own the viewport, safe areas, rotation, and keyboard](#own-the-viewport-safe-areas-rotation-and-keyboard)
- [Make touch and scrolling feel direct](#make-touch-and-scrolling-feel-direct)
- [Design lifecycle, offline, and update states](#design-lifecycle-offline-and-update-states)
- [Earn optional capabilities](#earn-optional-capabilities)
- [Keep the Apple character restrained](#keep-the-apple-character-restrained)
- [Implementation order](#implementation-order)
- [Home Screen readiness checklist](#home-screen-readiness-checklist)
- [Primary references](#primary-references)

## Start with the requested mode

- For an audit or review, report evidence and prioritized gaps. Do not edit the target app.
- For an authorized build or change, implement the smallest complete capability in the target
  app. Do not stop at a checklist or generic advice.
- Keep browser behavior as the baseline. Use standalone mode and optional APIs as progressive
  enhancements.
- Separate shared-skill work from product implementation into different changesets and reviews.

## Map the live app before editing

Trace the actual runtime path from public URL to rendered shell. Record concrete files and owners
for:

1. host, middleware, rewrites, redirects, and the live route;
2. root metadata, nested layouts, viewport, theme color, and icon declarations;
3. authentication entry, return URL, logout, and session persistence;
4. top-level navigation, browser history, deep links, and external handoffs;
5. fixed, sticky, draggable, fullscreen, toast, modal, sheet, and keyboard-adjacent surfaces;
6. network state, retained drafts, caches, Service Worker registration, and update prompts; and
7. observability and the existing verification path.

Do not patch a retired or redirect-only route because its name appears canonical. Prefer a few
route-aware choke points over page-by-page fixes. Establish one explicit owner for each of app
identity, viewport/theme integration, standalone detection, safe-area tokens, navigation,
offline/reconnect state, and Service Worker updates.

Preserve the target framework's router, metadata APIs, authentication model, data flow, styling
system, and existing lifecycle safeguards. Add only the files that framework needs; do not drop a
generic PWA template into a brownfield app.

## Preserve the browser baseline

Core tasks must work from an ordinary tab without installation or privileged APIs. Standalone
mode may refine chrome, navigation, safe-area layout, launch behavior, and supported OS
integrations, but it must not fork the product into two inconsistent applications.

Detect the applied display mode, not a guessed OS version:

```js
const standalone = window.matchMedia('(display-mode: standalone)').matches;
```

Use CSS for visual differences where possible:

```css
@media (display-mode: standalone) {
  .browser-only-install-help { display: none; }
}
```

Feature-detect Service Workers, Notifications, Push, Badging, Wake Lock, orientation locking, and
other optional APIs at the point of use. A missing capability must leave the main task intact.
Never make a parsed iOS version the primary branch condition.

## Define identity and launch behavior

Use the framework's native metadata or manifest mechanism to provide the equivalent of:

- a stable `id` that does not change with tracking parameters or incidental routes;
- `name` and a concise `short_name` that remain recognizable under truncation;
- a deliberate `start_url` and `scope` aligned with authentication and deep-link behavior;
- `display: "standalone"` unless the product has a demonstrated reason for another mode;
- `theme_color` and `background_color` that match the first rendered frame in light and dark
  contexts; and
- tested, purpose-appropriate icons with no critical artwork outside the safe zone.

On applicable Safari/iOS versions, an HTML `apple-touch-icon` takes precedence over manifest
icons. Treat it as an intentional compatibility asset, not a second uncontrolled brand source.
Legacy Apple web-app meta tags are fallbacks only; prefer the standards-based manifest.

Do not claim that a manifest or Service Worker is universally required for iOS installation.
iOS/iPadOS 26 can open any Home Screen site as a web app by default, while earlier applicable
versions use manifest or legacy metadata to request standalone behavior. The manifest still owns
useful identity and launch configuration.

## Build a complete shell without browser chrome

When the URL bar and browser controls disappear, the product must supply the missing orientation
and escape routes:

- Keep current location and top-level destinations understandable.
- Provide visible back, close, cancel, or done actions where browser chrome previously supplied
  the only exit. Never trap the user.
- Keep navigation URLs real and deep-linkable. Preserve forward/back history instead of replacing
  it with visual-only panels.
- Restore useful context after relaunch when appropriate, but do not bypass authentication or
  revive sensitive state without consent.
- Treat out-of-scope links, OAuth, payments, file viewers, and other external transitions as
  lifecycle boundaries. Preserve the intended return URL and reconcile state on return.
- Avoid standalone-only navigation that makes the same URL mean something materially different
  in a browser.

## Own the viewport, safe areas, rotation, and keyboard

Only opt into edge-to-edge layout deliberately. If using `viewport-fit=cover`, define shared
tokens at the shell and let feature surfaces consume them:

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

Use the same tokens for shared headers, tab bars, floating controls, sheets, dialogs, banners,
toasts, and update prompts. Keep critical controls clear of rounded corners, sensor housings, the
home indicator, and system edge gestures. Do not fix one page while a shared overlay remains
unsafe.

Test portrait and landscape rather than assuming inset values. Prefer modern dynamic viewport
units where they fit the layout. For keyboard-adjacent experiences, observe the actual visible
viewport when necessary; do not freeze layout to an initial `window.innerHeight`. Keep the focused
field and its primary action visible, and avoid double-applying keyboard and safe-area offsets.

## Make touch and scrolling feel direct

Apply the core skill's response, gesture, and interruptibility rules, plus these shell constraints:

- Give primary touch targets enough physical area and separation; do not rely on hover.
- Show pressed feedback immediately and commit on release, preserving cancel-by-dragging-away.
- Use platform scrolling and overscroll behavior unless a custom interaction has a concrete need.
- Prevent accidental selection only on controls or drag handles, never across readable content.
- Keep a visible button alternative for swipe-only actions.
- Do not claim the system's left or bottom edge for a custom gesture without a compelling need and
  a tested conflict strategy.
- Keep input zoom, text selection, copy/paste, password managers, and form autofill working.

## Design lifecycle, offline, and update states

A Home Screen icon raises expectations but does not make the network or process persistent. Define
visible loading, empty, offline, reconnecting, error, and update-ready states. Distinguish “offline”
from “server error” and “not authorized.”

If the product needs offline continuity:

- choose an explicit, bounded cache policy rather than caching every response;
- avoid retaining sensitive records by default;
- identify which reads work offline and which writes queue, fail, or remain as local drafts;
- make sync status and conflicts understandable; and
- preserve unsent work across recoverable failures when practical.

A Service Worker is an enhancement, not proof of offline correctness. Keep its ownership and
registration singular. Do not install a second updater beside an existing update coordinator.
When a new worker is ready, preserve dirty-state guards and let the user reload at a safe point;
never surprise-reload merely because an update exists. Test first load, controlled update, failed
fetch, reconnect, relaunch, and stale-data behavior separately.

## Earn optional capabilities

Install education, notifications, push, badges, wake lock, and orientation lock are optional. Add
them only when the product has a real task that benefits.

- Explain the value before presenting install guidance; do not repeatedly nag after dismissal.
- Request notification permission only from a clear user action and at a moment when the benefit
  is understandable. Accept refusal without degrading unrelated features.
- Use notifications for timely utility, not re-engagement noise.
- Feature-detect `navigator.setAppBadge` and `navigator.clearAppBadge`. On iOS/iPadOS, badge
  visibility is tied to notification permission even though code may set a count earlier.
- Request wake or orientation behavior only during the task that needs it; release or recover it
  when visibility changes.

## Keep the Apple character restrained

Use translucent or Liquid Glass-like treatment as a functional layer for important controls and
navigation, not as the content background. Keep content on stable, readable surfaces. Adapt
contrast and material weight to what moves underneath, provide solid fallbacks for reduced
transparency and increased contrast, and avoid stacked glass.

Do not reduce Apple-like design to blur, oversized corner radii, copied status bars, fake home
indicators, or native-looking controls that behave unlike their web equivalents. Familiarity,
clarity, feedback, and respect for user agency matter more than visual mimicry.

Support text scaling with `rem`/`em`-based layout, readable reflow, screen-reader names and state,
logical focus order, visible focus, external keyboards, reduced motion, reduced transparency,
increased contrast, and orientation changes. Do not disable zoom to protect a brittle layout.

## Implementation order

For an authorized target-app change:

1. Freeze the live-route map, required contexts, allowed files, and non-goals.
2. Establish identity and launch metadata through framework-native owners.
3. Establish shared standalone and safe-area contracts at the shell.
4. Integrate navigation/history, auth return, storage, network, and update behavior.
5. Audit every shell consumer and only then fix exceptional leaf surfaces.
6. Add optional capabilities only after the baseline is complete.
7. Run deterministic framework checks, then verify the relevant context matrix on real or
   representative devices. Report contexts not exercised.

## Home Screen readiness checklist

- [ ] Core tasks work in a normal browser without optional APIs.
- [ ] The manifest identity, launch URL, scope, display mode, colors, and icons are intentional.
- [ ] Browser and applied standalone modes are detected by capability or media query.
- [ ] Launch, relaunch, deep links, back/close paths, and external returns preserve orientation.
- [ ] Authentication redirects return to a coherent, authorized state.
- [ ] Portrait, landscape, safe areas, system edges, and the home indicator do not cover controls.
- [ ] The software keyboard keeps focused fields and primary actions reachable.
- [ ] Shared fixed/sticky controls, overlays, sheets, toasts, and update prompts use one inset
      contract.
- [ ] Loading, empty, offline, reconnecting, error, and update-ready states are distinct.
- [ ] Unsent work and dirty-state guards survive recoverable reconnect/update paths where practical.
- [ ] Cache and retained-draft policies are bounded, privacy-conscious, and product-specific.
- [ ] Install, notification, push, and badge prompts follow understandable user intent.
- [ ] Touch targets, pressed feedback, scroll, selection, zoom, autofill, and system gestures work.
- [ ] Text scaling, screen readers, focus, external keyboards, reduced motion, reduced
      transparency, increased contrast, and rotation are covered.
- [ ] Tested contexts and known gaps are reported explicitly.

## Primary references

- [WebKit: WebKit Features in Safari 26.0](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)
- [WebKit: Web Push for Web Apps on iOS and iPadOS](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [WebKit: Badging for Home Screen Web Apps](https://webkit.org/blog/14112/badging-for-home-screen-web-apps/)
- [WebKit: Designing Websites for iPhone X](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)
- [W3C: Web Application Manifest](https://www.w3.org/TR/appmanifest/)
- [Apple Human Interface Guidelines: Layout](https://developer.apple.com/design/human-interface-guidelines/layout)
- [Apple Human Interface Guidelines: Materials](https://developer.apple.com/design/human-interface-guidelines/materials)
