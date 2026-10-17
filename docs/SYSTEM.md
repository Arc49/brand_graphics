# Motion and sound design system

These are the rules that make the videos feel like one brand. The tokens live in
[`brand/brand.json`](../brand/brand.json). This document explains how to use them.

> **Status:** draft based on two style references: the Visual Cranio app UI (dark)
> and a clean white "glow-up myths" story (light). Name, handle and logo are
> placeholders. The *rules* below still apply when the final guidelines replace them.

## 0. Visual identity (draft)

| | `dark` theme (app UI) | `light` theme (story) |
|---|---|---|
| Background | `#0A0A0A` | `#FFFFFF` |
| Surface | `#161616` | `#F1F1F1` |
| Text / muted | `#FFFFFF` / `#8C8C8C` | `#111111` / `#5C5C5C` |
| Accent (brand mark, rings, lines) | emerald `#14B886` | red `#E0473A` |
| Highlight (the *one* key word) | emerald `#14B886` | red `#E0473A` |
| Action (buttons, "Tap through →", checks) | emerald `#14B886` | green `#3DA35D` |

**Type:** Poppins ExtraBold (800) for headlines, tight tracking (−0.025em) and
leading (1.02). Poppins SemiBold for sub-lines. Inter for small UI text. Labels and
the wordmark use Poppins Bold, UPPERCASE, +0.14em tracking, with the first word in
the accent colour (**VISUAL** CRANIO).

**Highlighting:** colour the key word. Don't box it. One highlight per statement.
A sub-line can end in an *action* phrase in the action colour plus an arrow that
nudges.

**When to use which theme:** `dark` for long-form, app and product content, and
over footage. `light` for story and carousel-style Shorts frames (`punch_text`
with `background: true`) and educational list content.

---

## 1. Principles

1. **One system, no one-offs.** Every graphic comes from a template, and every
   template reads the same tokens. If something can't be built from a template,
   add a template. Don't hand-animate a special case.
2. **Motion means something.** Elements enter fast and settle softly
   (confident). They leave faster than they arrived (out of the way). Nothing
   moves just to fill time.
3. **Every motion has a sound, every sound has a motion.** Sound sits *under* the
   voice and never competes with it. If you'd notice the SFX with your eyes
   closed, it's too loud.
4. **Restraint is the professional look.** Amateur edits overuse transitions,
   whooshes and zooms. Use the density limits in §5.

---

## 2. Motion tokens

| Token | Value | Use |
|---|---|---|
| `duration.micro` | 0.18 s | colour/state flips, button press |
| `duration.short` | 0.35 s | exits, small elements, wipes |
| `duration.medium` | 0.60 s | standard entrance (text, panels) |
| `duration.long` | 0.90 s | full-frame moves, underline draws |
| `stagger` | 0.06 s | delay between words / list items |
| `ease.enter` | `cubic-bezier(.16,1,.3,1)` (expo-out) | anything appearing |
| `ease.exit` | `cubic-bezier(.7,0,.84,0)` (expo-in) | anything leaving |
| `ease.move` | `cubic-bezier(.65,0,.35,1)` | things travelling across frame (wipes) |
| `spring` | k=170, c=20 | pops: callouts, logo mark, checkmarks |

Rules:

- **Exit ≈ 60% of enter.** Viewers have already read it, so get it out of the way.
- **Linear only for data:** counters, progress bars, timers.
- **Masks over fades.** Text rises out of a mask or wipes on. Plain opacity
  fades look like defaults.
- **Max two things animating at once** (excluding the background).
- **Hold times** (`motion.hold`) give the reading time. Allow ≈ 0.3 s per word plus
  1 s, and never less than 2 s.

### Safe areas

| Format | Keep text inside | Avoid |
|---|---|---|
| 16:9 | 6% margin all round | bottom 12% if burnt-in captions are used |
| 9:16 | 6% sides, 10% top | **bottom 20%** (caption + platform UI), **right 15%** (like/comment rail) |

The templates already respect these margins. When you pass custom `x`/`y`
positions to `callout`, keep them inside the safe areas.

---

## 3. Sound tokens

All tonal sounds (chimes, blips, risers, the sonic logo) are tuned to
**`sound.rootNote` + `sound.scale`** (draft: E minor, which reads sleek, serious and
clinical rather than cute). Pick music beds in E minor or its relative major
(G major) so stings never clash with the music.

### Loudness ladder (what the timeline should measure)

| Layer | Target | Notes |
|---|---|---|
| Dialogue | **−14 LUFS integrated**, −1 dBTP | YouTube, Shorts, Reels and TikTok all normalise near −14 |
| Music bed under voice | −28 to −32 LUFS | duck 8–12 dB under speech, 150 ms attack, 400 ms release |
| Music with no voice (intro, b-roll) | −18 to −16 LUFS | |
| Sonic logo | −16 LUFS-M | the only SFX allowed near dialogue level |
| Impacts | −18 LUFS-M | |
| Transitions / risers | −22 LUFS-M | |
| UI (clicks, pops, ticks) | −26 LUFS-M | felt more than heard |

The library files are **already normalised** to these levels. Drop them on the
timeline at 0 dB and they sit correctly under −14 LUFS dialogue. Turn a sound
down if needed, but don't push one above its tier.

### Sync

- Every SFX has a **sync point** (`sync` in `library/sfx/sfx.json`): the frame
  that has to land on the visual event. For a whoosh that's its peak, for a riser
  its end, for an impact its onset. The renderer lines this up for you.
- Keep sync to **±1 frame**. Audio that arrives early is more noticeable than
  audio that arrives late.
- **Round-robin:** sounds with `_01/_02/_03` variants should be rotated so repeats
  don't sound mechanical.

### Library

| Category | Sounds | Typical use |
|---|---|---|
| `brand` | `sonic_logo` | logo sting, end card |
| `transition` | `whoosh_short_01-03`, `whoosh_long_01-02`, `swish_01`, `glitch_01-02`, `reverse_swell` | wipes, text in/out, scene changes |
| `riser` | `riser_1s`, `riser_2s`, `downlifter_01` | build into reveals, release after peaks |
| `impact` | `impact_soft`, `impact_hard`, `sub_drop` | titles landing, big statements |
| `ui` | `click_01-03`, `pop_01-03`, `tick_01-03`, `blip_up/down`, `typing_01` | callouts, counters, lists, CTA |
| `tonal` | `chime`, `success`, `shimmer` | tips, results, sweeteners |

---

## 4. Template catalogue

| Template | Formats | Anchor (what to line up) | Default sound |
|---|---|---|---|
| `logo_sting` | 16:9, 9:16 | 0.47 s → the hard cut after the cold-open hook | sonic_logo |
| `lower_third` | 16:9, 9:16 | 0 s → the speaker's first line | swish + click |
| `title_card` | 16:9, 9:16 | 0.35 s → the cut into the new section | whoosh + soft impact |
| `callout` | 16:9, 9:16 | 0.02 s → the emphasised word | pop |
| `punch_text` | 16:9, 9:16 | 0.1 s → first word spoken | clicks + impact on *highlighted* word |
| `stat_counter` | 16:9, 9:16 | 0.4 + countDur → the number is spoken | ticks + success |
| `list_reveal` | 16:9, 9:16 | first item time → first item spoken | pop + tick per item |
| `transition` (`bands` / `iris` / `slide`) | 16:9, 9:16 | midpoint → the cut | whoosh_long / reverse_swell |
| `cta_subscribe` | 16:9, 9:16 | 1.25 s → "subscribe"/"follow" is said | whoosh, click, blip, shimmer |
| `end_card` | 16:9, 9:16 | 0 s → last line ends | whoosh_long + chime |

---

## 5. Video blueprints

### Long-form (YouTube 16:9)

```
0:00  Cold open / hook ....................... optional punch_text on the key line
0:05–0:20  logo_sting (+ sonic_logo) ......... hard cut on the anchor
first speaker line  lower_third
each topic change   title_card (every ~2–4 min)
on numbers          stat_counter
on enumerations     list_reveal
on key words        callout (max 1 per ~8 s)
after first payoff (~0:30–1:30) cta_subscribe (once)
scene/location changes  transition (max 1 per ~45 s; never on jump cuts)
last 10–20 s        end_card (YouTube end-screen slots are pre-laid out)
```

### Short-form (Shorts / Reels / TikTok 9:16)

```
0.0–1.5 s  punch_text hook (the first frame must already show text)
every 3–5 s  something changes: callout, stat, zoom-cut, B-roll
scene changes  transition style "slide" (0.8 s) at most every ~10 s
end  cta_subscribe with label "Follow" OR loop back cleanly (no end_card)
```

### Density limits (the "too much" alarm)

| | Long-form | Short-form |
|---|---|---|
| Transitions | ≤ 1 / 45 s | ≤ 1 / 10 s |
| Callouts / pops | ≤ 1 / 8 s | ≤ 1 / 3 s |
| Simultaneous overlays | 1 (transition may overlap one) | 1 |
| Impacts | ≤ 1 / 60 s | ≤ 2 per video |

---

## 6. Changing the brand

1. Edit `brand/brand.json` (colours, fonts, motion feel, sound key and character)
   and replace `brand/logo.svg` (use `fill="currentColor"` for the recolourable parts).
2. To use custom fonts, put the files in `brand/fonts/` and set `font.*.file`, e.g.
   `"file": "brand/fonts/Satoshi-Black.woff2"`.
3. Run `npm run build`. It regenerates the SFX (now in the new key), then
   re-renders every template.

Sound personality knobs: `sound.character` (`clean` | `warm` | `gritty`),
`sound.brightness` (0–1), `sound.rootNote`, `sound.scale`, and `sound.seed`
(changes the noise "take" without changing the design).
