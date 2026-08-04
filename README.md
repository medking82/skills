<a href="https://animations.dev/">
<img width="320" height="168" alt="opengraph-image-pwu6ef" src="https://github.com/user-attachments/assets/a405a37f-1a1a-4e8d-8fd6-269ee6d4fba6" />
</a>

# Skills For Designers and Engineers

[![skills.sh](https://skills.sh/b/emilkowalski/skills)](https://skills.sh/emilkowalski/skills)

For designers and engineers to help them build better user interfaces.

Knowing whether you made a right choice when it comes to animations, or design in general, is hard. These skills aim to help you get to those right decisions faster.

They are based on my years of experience working at companies like Vercel and Linear.

All the skills here are a side-effect of domain-expertise. AI doesn’t replace such expertise, it amplifies what you can get out of it and makes you way better relative to others.

So learn to code, design, or develop expertise in any other field. It’s extremely valuable.

You can stay up to date with my skills here:

[Sign Up To The Newsletter](https://animations.dev/skills)

## Install

```bash
npx skills@latest add emilkowalski/skills
```

### Keep the forked Apple Design skill current in Codex and Claude

This fork includes a deterministic updater for the user-scoped copies consumed by Codex and
Claude. The fork is the canonical source; each workstation still needs its own checkout and
bootstrap because installed skills are snapshots, not live GitHub mounts.

```powershell
# Preview whether either installed copy differs from medking82/skills@main.
pwsh scripts/sync-apple-design.ps1 -Mode Check

# Copy the reported source_sha256, then bind Apply to that exact reviewed manifest.
pwsh scripts/sync-apple-design.ps1 -Mode Apply -ExpectedSourceSha256 <64-hex-source-sha256>

# Preview, then register, a daily 06:30 check-only Scheduled Task on Windows.
pwsh scripts/install-apple-design-update-task.ps1
pwsh scripts/install-apple-design-update-task.ps1 -Execute
```

Scheduled checks write daily logs under
`%LOCALAPPDATA%\AppleDesignSkillUpdate\`. A detected update does not overwrite either installed
copy; run `Apply` explicitly with the exact manifest SHA-256 reported by `Check` after reviewing
the fork change. A missing or mismatched digest fails before either installed scope is written.
Syncing this GitHub fork from its upstream repository remains a separate manual decision.

#### Linux check/apply and timer

The Linux updater always downloads the published `medking82/skills@main` archive. It never
uses the current checkout as skill content, so an unpublished feature branch cannot become an
installed skill accidentally. Its default `wsl` scope profile compares or replaces four
independent snapshots:

- `/home/marck/.agents/skills/apple-design`
- `/home/marck/.claude/skills/apple-design`
- `/mnt/c/Users/Marck/.codex/skills/apple-design`
- `/mnt/c/Users/Marck/.claude/skills/apple-design`

```bash
# Check all four scopes. Exit 3 means at least one is missing or drifted.
python3 scripts/sync-apple-design.py --mode Check

# After reviewing published main, bind the one-time Apply to Check's exact digest.
python3 scripts/sync-apple-design.py --mode Apply \
  --expected-source-sha256 <64-hex-source-sha256>

# Verify all four scopes are current.
python3 scripts/sync-apple-design.py --mode Check

# Preview, then install, a daily 06:30 check-only systemd user timer.
scripts/install-apple-design-update-timer.sh
scripts/install-apple-design-update-timer.sh --execute
```

On a bare-metal Linux host with no `/mnt/c`, select the explicit `linux` scope profile. It
validates and manages only that Linux user's Codex and Claude snapshots under `~/.agents` and
`~/.claude`:

```bash
# Check, review the digest, apply once, then verify the two Linux snapshots.
python3 scripts/sync-apple-design.py --scope-profile linux --mode Check
python3 scripts/sync-apple-design.py --scope-profile linux --mode Apply \
  --expected-source-sha256 <64-hex-source-sha256>
python3 scripts/sync-apple-design.py --scope-profile linux --mode Check

# Preview, then install, a Linux-only daily check timer.
scripts/install-apple-design-update-timer.sh --linux-only
scripts/install-apple-design-update-timer.sh --linux-only --execute
```

Omitting `--scope-profile` and `--linux-only` preserves the four-scope WSL behavior.

Apply stages all changed scopes before swapping any of them and restores the previous snapshots
if a swap or verification fails. The default WSL profile also fails before destination writes
when `/mnt/c` is not the expected WSL Windows mount or the Windows profile/consumer directories
are unavailable. The Linux profile does not inspect or require `/mnt/c`.

The timer never runs Apply. Its output goes to the user journal:

```bash
journalctl --user -u apple-design-skill-update.service
```

Keep the Windows Scheduled Task as the fallback until a manual Linux Check/Apply, fresh
Codex/Claude load checks, a manual service run, and one natural timer cycle have all succeeded.
Only then disable the Windows task in a separate, explicit cutover.

## Why use it?

Agents don’t have great taste

I have seen plenty of times that agents don’t pick the right ingredients for an animation. An `ease-in` easing for an enter animation when it’s supposed to be `ease-out` ([here’s why](https://emilkowal.ski/ui/7-practical-animation-tips#4.-choose-the-right-easing)). Or they choose a solid border instead of a semi-transparent shadow for your UIs.

All these small things compound and make your interface either amazing, or just... not that great.

As explained in [Agents with Taste](https://emilkowal.ski/ui/agents-with-taste), these skills list all the little mistakes agents can potentially make and explain how to fix them.

This is your shortcut to great interfaces. A shortcut to stand out in a sea of slop.

## Reference

- **[emil-design-eng](./skills/emil-design-eng/SKILL.md)** — The main skill that consists of mostly animation, but also some design advice.
- **[review-animations](./skills/review-animations/SKILL.md)** — Review your animations in a strict way, based on my rules.
- **[improve-animations](./skills/improve-animations/SKILL.md)** — Audit all the animations in your codebase and get prioritized, self-contained plans that any agent can execute.
- **[find-animation-opportunities](./skills/find-animation-opportunities/SKILL.md)** — Search your UI for places that would genuinely benefit from motion, while also telling you what not to animate.
- **[animation-vocabulary](./skills/animation-vocabulary/SKILL.md)** — Get better animations from an AI by telling it exactly what you want by using the right words.
- **[apple-design](./skills/apple-design/SKILL.md)** — Apple’s principles for interface design and fluid motion, distilled from their WWDC design talks and translated for the web.
- **[pick-ui-library](./skills/pick-ui-library/SKILL.md)** — Have your agent pick the right library for the task based on libraries I use and trust, instead of letting AI hand-roll a toast component or install an abandoned package.
- **[prototype](./skills/prototype/SKILL.md)** — Build multiple different versions of a UI piece you describe and go through them using a switcher.
