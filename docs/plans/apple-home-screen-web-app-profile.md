# Apple Home Screen web-app experience profile

## Intent

Extend `apple-design` with an iOS-focused profile for mobile web apps that people add to
the Home Screen. The profile should help an agent design and implement a web app that remains
sound in a browser and feels coherent, responsive, and trustworthy when launched in standalone
mode, without pretending that a PWA has every native-app capability.

The primary target is a standards-based mobile Web/PWA experience on iPhone. Native SwiftUI,
UIKit, App Store packaging, and a macOS profile are separate future decisions.

When a user asks for a change rather than advice, the skill must be able to inspect the target
web app's existing framework and implement the PWA/app-shell capability in that app. This
repository changes only the reusable skill guidance; applying it to Johorindustry or another
product remains a separate frozen changeset in that product repository.

## Context map

- Request entry point: prompts such as “make this mobile site feel like an app,” “optimize this
  PWA for Add to Home Screen,” “make the installed web app feel native on iPhone,” or requests
  involving standalone mode, safe areas, app icons, offline continuity, push, or badging.
- Skill routing: `skills/apple-design/SKILL.md` frontmatter decides whether the skill loads. Its
  body currently routes no platform-specific references and is primarily a fluid-motion guide.
- New knowledge surface: `skills/apple-design/references/ios-home-screen-web-app.md`, loaded only
  for mobile web/PWA/Home Screen work.
- Shared behavior: the existing response, direct-manipulation, interruptibility, material,
  typography, accessibility, and design-principle guidance remains authoritative for motion and
  craft. The new profile adds product-shell and lifecycle guidance; it must not duplicate the
  existing motion reference.
- Canonical persistence: the complete `skills/apple-design/` tree in this repository. The existing
  updater already manifests and copies the complete tree, so a reference file needs no updater
  change.
- Downstream consumers: future Codex and Claude installations after an explicit digest-bound
  Apply. Publishing this repository alone does not update installed snapshots.
- External platform dependencies: iOS/iPadOS Home Screen web-app behavior, Web App Manifest,
  Service Workers, safe-area environment variables, Web Push, Notifications, and Badging APIs.
  Guidance must use feature detection and progressive enhancement rather than version sniffing.
- Relevant operational boundary: the installed Home Screen app is still web content with browser
  storage, network, lifecycle, and API constraints. The profile must preserve a usable browser
  experience and must not promise native-only behavior.
- Rollback: before publication, revert only the allowed documentation/skill files. After
  publication, installed copies remain unchanged until a human accepts the new tree digest and
  explicitly runs Apply.
- Motivating brownfield evidence: a read-only audit of Johorindustry at commit `d7476533` found
  mobile safe-area and viewport fixes distributed across leaf components, while no manifest,
  Service Worker, Home Screen identity, or shared standalone lifecycle was present. Its retired
  `/johorpro` layout still owns viewport/theme fixes even though the route immediately redirects
  into `/data-entry/johorpro`, demonstrating why the profile must trace the live route and shared
  shell before adding local patches. These product-specific details are evidence, not content to
  copy into the general skill.

## Evidence and platform facts

- WebKit states that iOS/iPadOS 26 opens every site added to the Home Screen as a web app by
  default, while the user can choose to add a browser bookmark instead. A manifest remains useful
  for identity, icons, and app configuration.
  <https://webkit.org/blog/17333/webkit-features-in-safari-26-0/>
- On earlier supported iOS/iPadOS versions, `display: standalone` or `fullscreen` in a manifest
  produces the standalone Home Screen experience. Home Screen web apps appear separately in the
  App Switcher. Manifest `id`, Web Push, and Badging are supported on applicable versions.
  <https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/>
- A Service Worker is not an iOS installability requirement, but WebKit identifies it as an
  important enhancement. The skill should require a deliberate offline/update strategy when the
  product needs continuity, not claim that installation itself depends on a Service Worker.
- Apple’s layout guidance requires respect for safe areas and hardware/system features such as
  rounded corners and Dynamic Island.
  <https://developer.apple.com/design/human-interface-guidelines/layout>
- Apple’s current materials guidance confines Liquid Glass primarily to the functional layer of
  controls and navigation and warns against using it throughout the content layer.
  <https://developer.apple.com/design/human-interface-guidelines/materials>

## Observed gaps

1. The `apple-design` description does not mention PWA, Add to Home Screen, standalone mobile web
   apps, safe areas, app identity, offline continuity, or install-specific capabilities, so the
   skill may not trigger for the target request.
2. The skill begins with motion rather than deciding the product surface and display mode.
3. It has no contract for browser mode versus standalone mode, launch/resume, navigation without
   browser chrome, offline/error/update states, install education, or notification permission.
4. Its material guidance can be read as encouragement to make all bars and sheets translucent;
   the Home Screen profile needs the stricter functional-layer boundary from current HIG guidance.
5. It has no Home Screen acceptance checklist or explicit anti-patterns for “native cosplay.”
6. It does not require an agent to locate the live route, root metadata, authentication boundary,
   shared navigation shell, update coordinator, or storage owner before editing. Without that map,
   viewport and safe-area fixes can land in a retired route or be repeated inconsistently in leaf
   components.

## Required behavior

### Trigger and routing

1. Expand the `apple-design` frontmatter description just enough to trigger for mobile web apps,
   PWAs, Add to Home Screen, standalone mode, and app-like iPhone experience. Preserve all existing
   motion, typography, material, and accessibility triggers.
2. Add a short platform-profile router near the start of `SKILL.md`. For a mobile Web/PWA/Home
   Screen request, require reading `references/ios-home-screen-web-app.md` before proposing or
   implementing the interface.
3. Do not load the Home Screen reference for a motion-only request with no app-shell or mobile-PWA
   concern.

### Home Screen experience contract

4. Require progressive enhancement: core tasks must work in a normal browser; standalone mode may
   refine navigation, chrome, safe-area layout, launch behavior, and supported OS integrations.
5. Cover app identity and launch configuration: manifest `id`, `name`/`short_name`, `start_url`,
   `scope`, `display`, theme/background colors, and suitable icons. Note that `apple-touch-icon`
   takes precedence over manifest icons on relevant Safari/iOS versions.
6. Require feature detection for standalone display, safe-area support, Service Workers,
   Notifications, Push, and Badging. Never branch primarily on a parsed iOS version.
7. Define a complete shell without browser chrome: visible wayfinding and back/close affordances,
   stable top-level navigation, deep-link-safe history, no dead ends, and preservation of user
   context across relaunch where appropriate.
8. Respect `env(safe-area-inset-*)`, status/navigation areas, device rotation, the software
   keyboard, system edge gestures, and reachable primary actions. Do not place critical controls
   under the home indicator, sensor housing, or gesture zones.
9. Specify touch-first behavior: adequate hit areas, immediate pressed feedback, restrained
   gestures with visible alternatives, native-feeling scroll, no accidental text selection, and
   no custom gesture that steals a system navigation gesture without a compelling reason.
10. Require explicit loading, empty, offline, reconnecting, error, and update-ready states. Preserve
    unsent user work when practical; never surprise-reload merely because a new Service Worker is
    available.
11. Treat install education, notification permission, push, and badging as earned capabilities.
    Ask in response to understandable user intent, explain the value, accept refusal, and avoid
    badges or notifications that do not convey timely utility.
12. Apply Liquid Glass/translucency only to a restrained functional layer. Keep content readable
    and structurally clear with standard surfaces; Apple-like design must not reduce to blur,
    oversized corner radii, or copied system chrome.
13. Preserve accessibility across Dynamic Type-like text scaling, reduced motion, reduced
    transparency, increased contrast, screen readers, external keyboards, and orientation changes.

### Output contract

14. When using this profile, identify the tested contexts: browser mode, installed standalone
    mode, online/offline transition, relaunch, rotation, keyboard-open state, and applicable
    accessibility preferences.
15. Separate required baseline behavior from optional enhancements such as push, badging, wake
    lock, or orientation lock. Recommend only enhancements supported by the product’s actual need.
16. Include a compact Home Screen readiness checklist in the reference so an agent can audit an
    implementation without inventing new criteria.

### Target-app implementation contract

17. Distinguish the user's requested mode: audit/report requests produce findings only; build or
    change requests implement the smallest complete capability in the target web app. Do not stop
    at generic advice when implementation is requested and authorized.
18. Before editing a target app, trace the live host and route through middleware/rewrites, root
    metadata, nested layouts, authentication redirects, navigation/history shell, global fixed
    controls, storage, network state, and update behavior. Do not patch a legacy or redirect-only
    route simply because its name looks canonical.
19. Prefer a few route-aware choke points over scattered page fixes. Establish explicit owners for:
    app identity/manifest, viewport and theme/status integration, standalone detection, safe-area
    tokens, navigation/history, service-worker lifecycle, offline/reconnect state, and update UX.
20. Adapt to the target framework's native conventions. For example, use framework metadata and
    route APIs where they exist, preserve the existing router/auth/data model, and add only the
    files required by that framework. Do not force a generic PWA template over a brownfield app.
21. Treat leaf-level safe-area values as consumers of the shell contract. Audit every fixed,
    sticky, draggable, fullscreen, toast/banner, modal/sheet, and keyboard-adjacent surface; ensure
    the shared header, tab/navigation bars, floating controls, and update prompts obey the same
    insets as feature components.
22. Preserve useful existing behavior such as non-blocking update prompts, dirty-state guards,
    durable session choices, and feature-specific offline fallbacks. Appification must integrate
    them rather than replacing them with a second lifecycle system.
23. Keep product code and shared-skill development in separate changesets and reviews. Findings
    from one product may sharpen the generic profile, but product names, routes, tokens, auth
    assumptions, and UI branding must not leak into the reusable skill.

## Allowed changes

- `docs/plans/apple-home-screen-web-app-profile.md`
- `skills/apple-design/SKILL.md`
- `skills/apple-design/references/ios-home-screen-web-app.md`
- `README.md` only to update the existing one-line `apple-design` description if the final skill
  scope would otherwise be misleading

## Non-goals and do-not-touch boundaries

- Do not add a top-level `ios`, `ios-macos`, or macOS skill in this changeset.
- Do not add native SwiftUI, UIKit, AppKit, Xcode, signing, App Store, or packaging guidance.
- Do not build or modify an actual product PWA, manifest, Service Worker, icon, screenshot, or
  application asset in this repository changeset. The finished skill may implement those artifacts
  later when a user invokes it for an authorized target-app change.
- Do not change the updater, scheduler, tests for the updater, peer-review configuration, other
  skills, installed user-scoped skills, or the upstream repository.
- Do not add scripts, templates, `agents/openai.yaml`, README files inside the skill, or speculative
  configuration.
- Do not promise platform parity, guaranteed offline behavior, background execution, silent push,
  or native APIs that the web platform does not provide.
- Do not automatically sync upstream, Apply the skill, install it, run dogfood, deploy, resume,
  rollback, purge memory, or clean historical worktrees.

## Compatibility, security, and availability constraints

- Prefer current standards and feature detection; mention legacy Apple meta tags only as a
  compatibility fallback, not the primary model.
- Never recommend requesting notification permission on first launch or without direct user intent.
- Keep offline caches and retained drafts bounded and privacy-conscious; do not imply that sensitive
  data should be cached by default.
- Treat external links and OAuth/payment handoffs as lifecycle transitions that must return people
  to a coherent app state; detailed auth/payment implementation is outside scope.
- Preserve the existing skill name and relative install path so current updater validation and
  consumers remain compatible.

## Verification

Targeted checks after implementation:

1. Run the skill-creator `quick_validate.py` against `skills/apple-design`.
2. Parse frontmatter and confirm `name: apple-design` remains unchanged.
3. Confirm every new relative reference from `SKILL.md` exists and that the profile is one level
   below the skill, with no duplicate copy of the existing motion guidance.
4. Check the profile against four static scenarios:
   - a mobile site that should remain excellent without installation;
   - an installed iPhone Home Screen app launched without browser chrome;
   - a temporary offline/reconnect/update transition with unsent work;
   - a brownfield app whose named legacy route redirects into a different live shell, ensuring the
     agent maps the live route and shared choke points before editing;
   - a motion-only request that should continue using the current core without loading PWA detail.
5. Confirm the documented checklist covers browser/standalone, safe areas, navigation, keyboard,
   offline/error/update, accessibility, and permission timing.
6. Run `git diff --check` and confirm the frozen diff contains only allowed files.

No full repository test, updater test, live Home Screen dogfood, installed-skill Apply, or deployment
is authorized by this plan. Any of those requires separate user authorization.

## Review, delivery, and rollback

- Risk: medium. The changes are documentation-only but alter a shared skill’s trigger and guidance
  for future generated interfaces.
- Base commit: `abaf55561806c84dd09e38fbcddc974f6aab50d5`.
- Run at most one plan-review round, only after explicit user authorization. Failure, timeout, or
  disagreement stops the workflow; do not retry or resubmit automatically.
- After implementation and targeted checks, freeze the allowed diff and run one formal diff-review
  process only when explicitly authorized. Authorized remediation may remain in that same review
  run; do not start an independent second review automatically.
- This repository has no `.sop/workflow.json`; commit, push, installed-skill Apply, and other
  delivery actions remain manual and separately authorized.
- Rollback is limited to the allowed files on this branch. Never rewrite `main` or mutate installed
  skills as part of rollback.

<!-- peer-reviewed: 2026-07-22T01:43:37Z reviewer=claude rounds=1 verdict=approved sha256=e54fd1536564a7689449225e3c480621ff85aeefedcd17127c2904f1c35751c3 -->
