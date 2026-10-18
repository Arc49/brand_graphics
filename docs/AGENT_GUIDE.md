# Guide for editing agents (Rush or any agentic editor)

This repo is a **graphics and sound kit**. An editing agent should be able to take a
raw cut plus its transcript and place branded motion graphics and SFX
consistently, without a human choosing each asset. This file is the contract.

## What you get

| Path | What |
|---|---|
| `library/overlays/manifest.json` | Every pre-rendered overlay: files, size, fps, duration, **anchor**, SFX cues, usage rule |
| `library/overlays/<asset>/` | `.webm` (VP9 alpha and SFX), `_sfx.wav` (SFX alone), `_preview.mp4`, `.png` poster |
| `out/` (after `npm run render`) | Same, plus `.mov` ProRes 4444 with alpha and PCM audio, for Premiere / Resolve / FCP |
| `library/sfx/sfx.json` | Every sound effect: file, category, duration, **sync** point, loudness |
| `docs/SYSTEM.md` | Design rules: density limits, loudness ladder, blueprints |

## Placement math

Each overlay has an `anchor` `{ t, event }`: the time *inside the clip* that has to
coincide with a story event (e.g. "the number is spoken").

```
clip_start_on_timeline = event_time_in_video − anchor.t
```

`anchor.t` already includes any lead-in (`leadIn`). The audio inside the overlay
(and the matching `_sfx.wav`) starts at the clip's first frame, so put the
`_sfx.wav` at the same `clip_start` if you use it instead of the embedded track.

Standalone SFX (not tied to an overlay):

```
sfx_start = event_time − sfx.sync
```

## Procedure

1. **Read the transcript** (word-level timestamps) and tag:
   - speakers and their first line → `lower_third`
   - topic boundaries → `title_card` (long-form) or `transition` style `slide` (Shorts)
   - spoken numbers that matter → `stat_counter`
   - enumerations ("three things…", "first… second…") → `list_reveal` with `times` = when each item is spoken
   - the single most important phrase in a section → `callout` or `punch_text`
   - the hook line (first sentence) → `punch_text` in Shorts
   - the first payoff moment → `cta_subscribe`
2. **Apply density limits** from `docs/SYSTEM.md §5`. Drop the lowest-value
   candidates until the limits hold, and never stack two overlays (a transition
   may overlap one).
3. **Render custom text.** Pre-rendered assets have placeholder text. For each
   placement with custom content, render a variant (see below) and use the new
   manifest entry.
4. **Place** video on a track above the footage and audio on a dedicated SFX
   track. Don't duck SFX. Duck the *music* under dialogue (8–12 dB).
5. **Check:** dialogue −14 LUFS integrated, true peak ≤ −1 dBTP. No overlay in the
   9:16 bottom 20% or right 15%.

## Rendering a variant

```bash
node render/render.mjs --template lower_third --name lt_sam \
  --props '{"name":"Sam Lee","title":"Head of Growth"}' --formats landscape,vertical
# add --theme light|dark (default: brand.json "theme" = light); auto names are <template>_<theme>
# add --fast to skip ProRes (WebM + WAV + preview only; much faster)
# add --out library/overlays to add it to the committed library
```

Props per template (defaults are in each `motion/templates/*.js`):

| Template | Props |
|---|---|
| `lower_third` | `name`, `title`, `hold` |
| `title_card` | `label`, `title`, `background` (bool), `hold` |
| `callout` | `text`, `icon` (emoji/char or null), `x`, `y` (0–1 of frame), `style` (`accent`/`surface`), `hold` |
| `punch_text` | `text` (wrap one word in `*stars*` to highlight), `sub` (smaller line; `*stars*` = action colour; end with `→` for a nudging arrow), `anim` (`rise`/`slam`), `align` (`left`/`center`), `background` (full theme card, e.g. story frames), `scrim`, `wordGap`, `hold` |
| `stat_counter` | `value`, `prefix`, `suffix`, `decimals`, `label`, `countDur`, `hold`, `x`, `y`, `compact` |
| `list_reveal` | `heading`, `items[]`, `gap` **or** `times[]` (seconds from clip start), `hold`, `panel` |
| `transition` | `style` (`bands`/`iris`/`slide`), `dur` |
| `cta_subscribe` | `label`, `doneLabel`, `hold` |
| `logo_sting` | `name`, `tagline`, `background`, `compact` |
| `end_card` | `heading`, `sub`, `hold` (5–20 s for YouTube end screens), `placeholders` |

To match a speaker's pacing, derive props from the transcript. For example,
`stat_counter.countDur` = time from when the speaker starts the sentence to the
number. `list_reveal.times` = each item's word timestamp minus the clip start.

## Edit decision example

```json
{
  "video": "episode_12_main.mp4",
  "format": "landscape",
  "placements": [
    { "asset": "logo_sting_light_landscape", "event": "hook ends", "event_time": 11.40, "clip_start": 10.93 },
    { "asset": "lt_sam_landscape", "event": "Sam's first line", "event_time": 14.02, "clip_start": 14.02 },
    { "asset": "stat_revenue_landscape", "event": "'…three hundred thousand'", "event_time": 96.80, "clip_start": 94.80 },
    { "sfx": "whoosh_long_01", "event": "B-roll cut", "event_time": 131.00, "start": 130.40 }
  ]
}
```
