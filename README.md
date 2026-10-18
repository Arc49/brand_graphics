# Brand motion and sound kit

A code-driven system of **motion graphics and sound design** for long-form (16:9)
and short-form (9:16) video. Everything is generated from one brand file, so the
whole look and sound changes together.

- **10 motion templates**: logo sting, lower third, chapter card, callout, punch text
  (hook), stat counter, list reveal, transitions (3 styles), subscribe/follow CTA, end card
- **2 themes**: `light` (**default**, clean white story: black type, red highlight, green
  action) and `dark` (app UI: black and emerald)
- **200 sound effects** in `library/sfx/`, all loudness-normalised per category:
  - 31 core brand sounds tuned to the brand key: whooshes, risers, impacts, clicks/pops/ticks,
    chimes and a **sonic logo**
  - 18 original **desktop-OS style** (`desktop/`) and **handheld-console style** (`console/`) UI sounds
  - 151 recorded CC0 UI sounds from Kenney (`kenney_interface/`, `kenney_ui/`); see `library/sfx/THIRD_PARTY.md`
- Every overlay ships with its **SFX already synced** to the motion (sample-accurate)
- Exports for any editor: **ProRes 4444 + alpha** (`.mov`), **VP9 + alpha** (`.webm`),
  a standalone `_sfx.wav`, a review `_preview.mp4` and a poster `.png`
- A `manifest.json` with placement **anchors** and usage rules, so an editing agent (Rush or
  any other) can place graphics from a transcript (see [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md))

## Quick start

```bash
npm run sfx                      # regenerate the synthesised SFX → library/sfx/ (keeps imported packs)
npm run library                  # render WebM/WAV/preview kit   → library/overlays/
npm run render                   # full render incl. ProRes .mov → out/
npm run preview                  # gallery at /preview/, live player at /motion/stage.html
```

Requirements: Node 18+, Python 3 + numpy, ffmpeg, and Playwright Chromium.

### Render your own text

```bash
node render/render.mjs --template lower_third --name lt_sam \
  --props '{"name":"Sam Lee","title":"Coach"}' --formats landscape,vertical --theme light
```

Quick visual check without encoding:

```bash
node render/snap.mjs punch_text vertical --theme light --props '{"background":true}'
```

### Live player

`motion/stage.html` (served by `npm run preview`) plays any template in real time
**with its sound**. You can switch format, theme and background, scrub the
timeline, and edit the props JSON live.

## Layout

```
brand/brand.json      ← single source of truth: themes, fonts, motion tokens, sound key, loudness
brand/logo.svg        ← mark (currentColor = theme accent)
brand/fonts/          ← Poppins 600/700/800 (OFL)
motion/lib/           ← seekable animation core + stage runtime
motion/templates/     ← one file per template
sound/synth.py        ← SFX synthesiser (numpy)
render/render.mjs     ← frame-accurate renderer → mov / webm / wav / mp4 / manifest
render/snap.mjs       ← contact-sheet snapshots for quick review
jobs/showcase.json    ← which variants to render
library/              ← committed kit: sfx + rendered overlays + manifests
docs/SYSTEM.md        ← the design rules (timing, easing, loudness, density, blueprints)
docs/AGENT_GUIDE.md   ← contract for editing agents
```

## Brand status

`brand/brand.json` is a **draft built from the style references**: the
Visual Cranio app UI and the clean white "glow-up myths" story. The name, handle
and logo are placeholders. When the final guidelines arrive, edit that file (and
`logo.svg`) and run `npm run build`. Every graphic and sound regenerates.
