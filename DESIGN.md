---
name: Reel Oracle
description: A YouTube intelligence platform styled as a classified field-intelligence dossier
colors:
  oxblood-stamp: "#a3341f"
  oxblood-stamp-hover: "#c94427"
  ops-room-charcoal: "#17140f"
  folder-shadow: "#1c1810"
  case-surface: "#221d15"
  border-ink: "#362c1f"
  border-ink-strong: "#4c4030"
  cream-dossier: "#f2ead9"
  muted-parchment: "#b3a488"
  dim-ledger-label: "#a89b7f"
  body-ink: "#d9cdb0"
  aged-paper: "#efe4c8"
  folder-manila: "#ece0bf"
  charcoal-ink: "#241c10"
  classified-red: "#ff8f66"
  verified-green: "#9dc47c"
  caution-amber: "#d9a441"
  accent-contrast: "#fbf3e6"
  accent-soft: "rgba(163,52,31,.22)"
  accent-glow: "rgba(163,52,31,.5)"
  danger-soft: "rgba(255,143,102,.18)"
typography:
  display:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "2.6rem"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "0.01em"
  displaySm:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "0.01em"
  heroDisplay:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "clamp(2rem, 4.2vw, 3.1rem)"
    fontWeight: 600
    lineHeight: 1.06
    letterSpacing: "-0.005em"
  sectionHead:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "clamp(1.4rem, 2.6vw, 1.9rem)"
    fontWeight: 600
    lineHeight: 1.18
    letterSpacing: "-0.005em"
  title:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.03em"
  lead:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.94rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  meta:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "0.72rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.06em"
  data:
    fontFamily: "Courier Prime, Courier New, ui-monospace, monospace"
    fontSize: "0.85rem"
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: "normal"
  control:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "0.76rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.05em"
  small:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  dataSmall:
    fontFamily: "Courier Prime, Courier New, ui-monospace, monospace"
    fontSize: "0.82rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "0.68rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.06em"
  micro:
    fontFamily: "Oswald, Arial Narrow, sans-serif"
    fontSize: "0.64rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.06em"
rounded:
  sm: "2px"
  md: "3px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "22px"
  xl: "30px"
components:
  button-primary:
    backgroundColor: "{colors.oxblood-stamp}"
    textColor: "{colors.accent-contrast}"
    typography: "{typography.control}"
    rounded: "{rounded.md}"
    padding: "11px 20px"
  button-primary-hover:
    backgroundColor: "{colors.oxblood-stamp-hover}"
  badge-stamp:
    backgroundColor: "{colors.accent-soft}"
    textColor: "{colors.oxblood-stamp}"
    typography: "{typography.label}"
    rounded: "{rounded.sm}"
    padding: "3px 10px"
---

# Design System: Reel Oracle

## Overview

**Creative North Star: "The Field Intelligence Dossier"**

Reel Oracle refuses the two ruts a YouTube analytics tool falls into by default: a reskinned YouTube Studio (near-black canvas, YouTube red, Roboto/Inter) or a generic blue-accent SaaS dashboard. Instead every screen reads as a classified case file assembled for a decision-maker — the product's actual job (turning raw YouTube data into a verdict) made literal. A folder-tab strip stands in for the app's navigation; every panel and card carries a cut top-right corner, like a dog-eared folder; results arrive as stamped exhibits, not neutral cards; loading states redact rather than shimmer.

This is an Operate-mode surface (a working dashboard, not a marketing page), so restraint governs: one accent color, workhorse body type, and density kept scannable. The personality lives in structure and material — the corner cut, the stamp motion, the typewritten data — not in ornament layered on top of a generic shell.

**Confirmed rejection:** no YouTube-red/near-black reskin, no glass/gradient SaaS-dashboard default, no kicker/eyebrow labels, no emoji or unicode glyphs standing in for icons.

**Key Characteristics:**
- One accent (oxblood stamp red) carrying verdicts, primary actions, and active states — never decorative
- A single structural signature (cut top-right corner) repeated at every scale: hero, panel, card, table container
- Three-role typography: Oswald for structure/labels, Inter for reading, Courier Prime for data
- Motion is disciplined: spring/bounce easing reserved for exactly one moment (the ink-stamp impact on badges and the masthead stamp); everything else uses a clean exponential ease-out

## Colors

Warm and low-saturation everywhere except the single oxblood accent, which is the only fully saturated color on screen.

### Primary
- **Oxblood Stamp** (`#a3341f`): the one accent. Carries primary buttons, active tab underline, badge borders/text, focus rings, the masthead stamp, and the quota-meter fill. Never used for large background fields — always in a bordered, textual, or narrow role, so it reads as ink, not paint.
- **Oxblood Stamp Hover** (`#c94427`): hover state for the above.
- **Accent Contrast** (`#fbf3e6`): text color for anything sitting directly on an Oxblood fill (primary buttons).
- **Accent Soft** (`rgba(163,52,31,.22)` dark / `rgba(163,52,31,.12)` light) and **Accent Glow** (`rgba(163,52,31,.5)` dark / `rgba(163,52,31,.35)` light): alpha tints of Oxblood for badge fills and the active-tab underline glow — always derived from the one accent hue, never an independent color.

### Neutral — Ops-Room (dark theme, default)
- **Ops-Room Charcoal** (`#17140f`): page background. A warm near-black, not a true black or blue-black.
- **Folder Shadow** (`#1c1810`): panel/hero background, one step up from the page.
- **Case Surface** (`#221d15`): card/exhibit background, one step up from panel.
- **Border Ink** (`#362c1f`) / **Border Ink Strong** (`#4c4030`): hairlines and dividers.
- **Cream Dossier** (`#f2ead9`): primary text, headings.
- **Muted Parchment** (`#b3a488`): secondary text (subheads, notes).
- **Dim Ledger Label** (`#a89b7f`): small uppercase labels (field captions, stat labels) — deliberately lighter than a typical "dim" gray so 12px caps clear 4.5:1 against every surface tone in this system.
- **Body Ink** (`#d9cdb0`): list/paragraph body copy.

### Neutral — Declassified Daylight (light theme)
- **Aged Paper** (`#efe4c8`): page background.
- **Folder Manila** (`#ece0bf`): panel/hero/card background.
- **Charcoal Ink** (`#241c10`): primary text — the light theme is not an inversion of the dark palette, it's a second real material (paper + ink rather than screen + glow).

### Verdict Inks (semantic, not decorative palette expansion)
- **Classified Red** (`#ff8f66` dark / `#a3341f` light) — danger/risk text and backgrounds. A rubber-stamp "REJECTED" reading.
- **Danger Soft** (`rgba(255,143,102,.18)` dark / `rgba(163,52,31,.12)` light) — the alert-badge fill, an alpha tint of Classified Red.
- **Verified Green** (`#9dc47c` dark / `#3f6b28` light) — success/positive text and backgrounds. A rubber-stamp "APPROVED" reading.
- **Caution Amber** (`#d9a441` dark / `#71500d` light) — warning text (cold-start/misconfiguration banners).

### Named Rules
**The One Ink Rule.** Oxblood is the only saturated color anywhere in the interface. Verdict inks (red/green/amber) exist because the product must say "trust this" or "don't" at a glance, but they stay low-chroma and are never used for primary actions or navigation — only Oxblood commands attention.

**Accepted exception:** the browser's native text-selection highlight (`::selection`) sets white text on the Oxblood accent — a two-property browser convenience rule, not a designed surface, so it stays outside the token system rather than manufacturing a dedicated "selection-text" role for one line of CSS.

## Typography

**Display Font:** Oswald (with Arial Narrow, sans-serif fallback)
**Body Font:** Inter (with ui-sans-serif, system-ui, sans-serif fallback)
**Label/Mono Font:** Courier Prime (with Courier New, ui-monospace, monospace fallback)

**Character:** Oswald's condensed caps carry every piece of structural/UI language — mastheads, tab labels, panel headings, field captions, badges — so the interface reads like stencilled document headers. Inter stays purely a reading face for sentences and paragraphs, chosen deliberately as a workhorse rather than a display face (this is an Operate surface; legibility at small sizes across dozens of dense panels outranks typographic flourish in body copy). Courier Prime marks anything that is data rather than prose — table cells, stat values, form input text, JSON dumps — so a glance tells you which tokens on screen are typed measurements versus written language.

**Diagram-label exception:** the landing page's illustrative SVG compositions (trend radar node labels, forecast-chart axis tag, the nav wordmark's two-letter monogram) carry their own micro-scale (6-8px) outside the ten UI steps below. These are diagram annotations read at a glance inside a graphic, the same category as a chart's axis ticks — not paragraph or UI-control text, so they don't compete with the reading-size floor the rest of this scale protects.

### Hierarchy
- **Display** (600, 2.6rem desktop / 2rem mobile, 1.02 line-height, uppercase): the "Reel Oracle" masthead title only, on the Operate dashboard.
- **Hero Display** (600, fluid `clamp(2rem, 4.2vw, 3.1rem)`, 1.06 line-height): the landing page's headline only — the one place a fluid, viewport-responsive size is used instead of the dashboard's two fixed steps, because a Persuade-mode first viewport needs to hold its scale relationship across a much wider range of widths than a dashboard panel ever does.
- **Section Head** (600, fluid `clamp(1.4rem, 2.6vw, 1.9rem)`, 1.18 line-height): landing-page case-file headings (one per pillar/who/method/log file).
- **Title** (600, 1rem, uppercase, 0.03em tracking): panel headings, above a perforated rule.
- **Lead** (400, 0.94rem, 1.5 line-height): the hero subhead — the only paragraph-scale copy on screen.
- **Meta** (600, 0.72rem, uppercase, 0.06em tracking): case-file metadata and secondary controls — the hero's file/case tag, the theme toggle, the raw JSON dump.
- **Data** (400, 0.85rem, tabular numerics): form input text, the quota value.
- **Control** (600, 0.76rem, uppercase, 0.05em tracking): buttons, folder tabs, muted asides, export links.
- **Small** (400, 0.8rem): notes, checkbox labels, inline errors, quote body text.
- **Data Small** (400, 0.82rem, tabular numerics): table cells, list/aspect-row text.
- **Label** (600, 0.68rem, uppercase, 0.06em tracking): stamps and badges.
- **Micro** (600, 0.64rem, uppercase, 0.06em–0.08em tracking): field captions, stat labels, quota labels, quote attributions, table headers.

One narrow, deliberate exception: the decorative opening-quote glyph on `.yt-quote` borrows Georgia at 1.6rem for a proper serif quotation-mark shape — a single typographic character, not a UI role, so it sits outside this scale rather than forcing Oswald/Courier Prime to fake a glyph they don't draw well.

### Named Rules
**The Structure-vs-Prose Rule.** Oswald is never used for a sentence longer than a few words, and Inter is never used for a UI label. If it names or structures something, it's Oswald; if it explains something, it's Inter; if it's a measured value, it's Courier Prime.
**The Ten-Step Rule.** All Operate-dashboard type sizes resolve to one of ten documented steps (0.64 / 0.68 / 0.72 / 0.76 / 0.8 / 0.82 / 0.85 / 0.94 / 1 / 2–2.6rem). A new size needs a named role in this table, not a one-off value tucked into a component. The landing page's two fluid `clamp()` roles (Hero Display, Section Head) are the sanctioned exception — Persuade surfaces are allowed viewport-responsive sizing the fixed-scale Operate dashboard doesn't need.

### Typography tokens (formal scale)

The sizes above are the *documented steps*; `frontend/src/index.css` now names them as reusable CSS custom properties so no component hand-writes a `rem` value. A `--text-*` scale (3xs/2xs/xs/sm/base/md/lg/xl/2xl/display/data-display) holds the raw sizes; a `--type-*` role layer aliases each to the job it does (`--type-caption`, `--type-label`, `--type-meta`, `--type-control`, `--type-body`, `--type-lead`, `--type-title`, `--type-module`, `--type-section`, `--type-display`, `--type-data`). Components reference the role (`font-size: var(--type-label)`), never the raw scale step directly, so renaming what a role means never requires touching every component that uses it. The landing page's `Landing.css` was fully migrated onto this scale in this pass; the dashboard's older named-role CSS variables (`--yt-hero-display-size` etc.) now resolve through it as legacy aliases rather than duplicating the values.

## Layout

Single-column max-width container (1500px), with a two-column responsive grid (`repeat(2, minmax(0,1fr))`) for panel groups that collapses to one column below 1000px. The hero masthead switches from a row (title block + quota/toggle side by side) to a stacked column below 640px. Spacing runs on an approximate 6/10/16/22/30px rhythm — tighter within a form row, generous between panels and around the hero. Panels stagger their entrance animation by 60ms per grid position so a tab's content cascades in rather than popping at once.

## Elevation & Depth

Flat-by-default with soft ambient shadows, not hard offset drop-shadows: `--yt-shadow-sm` (`0 1px 2px rgba(0,0,0,.35)`) for resting cards, `--yt-shadow-md` (`0 10px 26px rgba(0,0,0,.4)`) on hover lift, `--yt-shadow-inset` (`inset 0 1px 2px rgba(0,0,0,.4)`) for recessed tracks (the quota meter's groove), and a signature `--yt-shadow-glow` (oxblood-tinted ring + soft blur) reserved for primary-button hover, echoing the accent rather than a generic elevation increase.

### Named Rules
**The Ink-Not-Elevation Rule.** Depth on hover comes from a small `translateY(-2px)`/`-3px` lift plus a softened shadow, never from a change in surface color or border weight — the corner-cut and border language stay constant across resting and hover states.

## Shapes

Every panel, card, and the hero itself shares one signature cut: a top-right corner sliced off via `clip-path` (a "dog-eared folder" silhouette), scaled to the element — 30px on the hero, 20px on panels, 12px on cards. Folder-tab navigation buttons use an asymmetric trapezoid clip (`polygon(10px 0, 100% 0, calc(100% - 10px) 100%, 0 100%)`) so they read as overlapping paper tabs rather than pill buttons. Corner radius elsewhere is minimal (2–3px) — just enough to soften a machined edge, never a rounded "app card" radius. Badges/stamps carry a small counter-rotation (±1.5–3deg) instead of sitting perfectly level, reinforcing the hand-stamped reading.

## Components

### Buttons
- **Shape:** 3px radius, no corner cut (buttons are tools, not documents).
- **Primary:** Oxblood background (`#a3341f`), cream text (`#fbf3e6`), Oswald label type, uppercase, 0.05em tracking.
- **Hover:** lifts 2px, background shifts to `#c94427`, gains the oxblood glow shadow.
- **Disabled:** 40% opacity, no pointer cursor.

### Badges (stamps)
- **Style:** 1px solid border in the current color, background at ~20% accent opacity, Oswald label type, uppercase, slight rotation.
- **Variants:** default (oxblood), alert (brighter red-orange, opposite rotation), muted (dashed border, no fill — an unstamped/pending reading).
- **Motion:** a single authored `yt-stamp` keyframe (scale + rotate settle with a spring ease) plays once on mount — the one place bounce easing is intentional in this system.

### Cards / Containers
- **Corner Style:** top-right cut (12px on cards, 20px on panels, 30px on the hero).
- **Background:** one step lighter than the page (Folder Shadow/Manila for panels and hero, Case Surface for cards nested inside panels).
- **Shadow Strategy:** resting `shadow-sm`, hover `shadow-md` plus a 3px lift.
- **Border:** 1px `Border Ink`, strengthening to `Border Ink Strong` on hover.
- **Internal Padding:** 16–24px depending on nesting depth.

### Inputs / Fields
- **Style:** 1px `Border Ink Strong`, 3px radius, Case-Surface background, Courier Prime text (typed-entry reading).
- **Focus:** border shifts to Oxblood plus a 3px soft accent-tinted ring.
- **Label:** Oswald label type above the field, not inline/floating.

### Navigation (folder tabs)
- Trapezoid-clipped tab buttons sharing a bottom rule; inactive tabs sit in Folder Shadow with muted label text, the active tab lifts to the panel's own background with full-contrast text. A 3px oxblood underline (glow-shadowed) slides beneath the active tab.

### Loader (redaction bars)
- Three short horizontal bars (Paper Ink fill) pulse in staggered sequence next to a mono-font label — the redaction motif made real for every async loading state in the app, replacing a generic spinner.

### Intake instrument (landing)
- Mode switching must actually recompose the field layout (the brief this was built against explicitly bans a hard jump when Compare Creators' second field appears). `.ld-instrument-field-2` animates `max-width` — a deliberate, narrow exception to the transform/opacity default, because the whole point is that real layout space opens up smoothly; a `transform`-only fake would leave dead space or fail to move the Run button.

## Do's and Don'ts

### Do:
- **Do** keep Oxblood as the only saturated color on any given screen (The One Ink Rule).
- **Do** apply the cut-corner clip-path to any new panel, card, or container-level component so it reads as part of this system.
- **Do** use Oswald for anything structural (labels, headings, nav, badges) and Inter only for prose (The Structure-vs-Prose Rule).
- **Do** reserve spring/bounce easing (`--yt-ease-spring`) exclusively for the stamp-impact motion; use `--yt-ease-out` (exponential) for every other transition.
- **Do** use Courier Prime for any genuinely measured/typed value (numbers, IDs, timestamps, JSON) — never as a generic "technical" costume.

### Don't:
- **Don't** reintroduce YouTube's own red/black palette or a generic blue-accent SaaS look — both are the explicitly rejected defaults for this product.
- **Don't** place a small label directly above a heading in the kicker/eyebrow position; if document-style metadata is needed, it belongs beside or below the title, not above it.
- **Don't** use emoji or bare Unicode glyphs as icons; draw them as inline SVG in the existing stroke-based icon style.
- **Don't** give cards, list items, or alerts a colored `border-left`/`border-right` — depth and emphasis come from the corner cut, shadow, and rotation, not a side rule.
- **Don't** animate `width`/`height`/`padding`/`margin` for new components; animate `transform`/`opacity` instead (see the quota meter's `scaleX` fill as the reference pattern).
