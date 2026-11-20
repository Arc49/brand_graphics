#!/usr/bin/env python3
"""Sound design for the BADDI3ST C/S flame loop (uses the brand synth toolkit).

Writes two files:
  baddi3st_fire_loop.wav  seamless loop, same length as the video loop: low roar,
                          crackles, flare swells synced to the flicker, ember sparkles
  baddi3st_ignite.wav     one-shot reveal: reverse suck-in -> ignition whoosh -> hit + shimmer
                          (put it under the first second when the logo appears)

  python3 flame_sound.py --seconds 6 --out out/
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sound"))
import synth as S  # noqa: E402

SR = S.SR


def secs(d):
    return np.arange(int(d * SR)) / SR


def roar(rng, dur):
    """Fire body: low-passed brown-ish noise with slow, irregular breathing."""
    n = len(secs(dur))
    x = np.cumsum(rng.standard_normal(n)) * 0.02
    x = S.highpass(x - S.lowpass(x, 3), 40)
    x = S.lowpass(x, 900)
    breath = S.lowpass(rng.standard_normal(n), 1.5)
    breath = 0.7 + 0.3 * breath / (np.abs(breath).max() + 1e-9)
    st = S.widen(rng, x * breath, 0.7)
    return st / (np.abs(st).max() + 1e-9)


def hiss(rng, dur):
    """Airy top of the flames (gas hiss), gently modulated."""
    n = len(secs(dur))
    x = S.highpass(rng.standard_normal(n), 2500)
    x = S.lowpass(x, 9000)
    mod = S.lowpass(rng.standard_normal(n), 4)
    mod = 0.5 + 0.5 * mod / (np.abs(mod).max() + 1e-9)
    return S.widen(rng, x * mod, 0.9) * 0.25


def crackles(rng, dur, rate=14):
    """Wood-free 'electric' crackle: short resonant noise pops, random pan, Poisson timing."""
    out = np.zeros((len(secs(dur)), 2))
    t = 0.0
    while True:
        t += rng.exponential(1 / rate)
        if t >= dur:
            break
        d = rng.uniform(0.004, 0.02)
        tt = secs(d)
        burst = rng.standard_normal(len(tt)) * np.exp(-tt / (d * 0.25))
        f = rng.uniform(1500, 5500)
        burst = S.stft_shape(np.concatenate([burst, np.zeros(2048)]), S.bandpass_gain(f, 0.9))[: len(tt) + 400]
        g = rng.uniform(0.15, 1.0) ** 2
        st = S.stereo(burst * g, rng.uniform(-0.8, 0.8))
        i = int(t * SR)
        out[i:i + len(st)] += st[: len(out) - i]
    return out


def flares(rng, dur, times):
    """Soft whoosh swells where the flames surge."""
    out = np.zeros((len(secs(dur)), 2))
    P = S.Palette({"sound": {"rootNote": "C#", "scale": "minor", "brightness": 0.55, "character": "warm"}})
    for t0 in times:
        w, pk = S.whoosh(P, rng, 1.1, 0.55, 180, 1800, tuple(rng.uniform(-0.5, 0.5, 2)), tone=True)
        i = int((t0 - pk) * SR)
        a, b = max(i, 0), min(i + len(w), len(out))
        out[a:b] += w[a - i:b - i]
    return out


def sparkles(rng, dur, count=10):
    """Glassy high tinks for the rising embers (glam / crown vibe), tuned to C# minor."""
    out = np.zeros((len(secs(dur)), 2))
    notes = [73, 76, 80, 83, 85, 88]  # C#5 E5 G#5 B5 C#6 E6 (midi)
    for _ in range(count):
        f = S.mtof(int(rng.choice(notes)) + 12)
        d = 0.9
        tt = secs(d)
        x = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / dd) for r, a, dd in ((1, 1, 0.25), (2.76, 0.35, 0.08), (5.4, 0.12, 0.04)))
        st = S.stereo(x * rng.uniform(0.2, 0.6), rng.uniform(-0.9, 0.9))
        i = int(rng.uniform(0, dur - 0.1) * SR)
        out[i:i + len(st)] += st[: len(out) - i]
    return out


def make_loop(rng, dur):
    """Build dur + 1.5 s, then fold the overhang onto the start with an equal-power crossfade => seamless."""
    tail = 1.5
    total = dur + tail
    bed = roar(rng, total) * 0.9 + hiss(rng, total)
    sub = S.stereo(S.lowpass(rng.standard_normal(len(secs(total))), 70)) * 0.9
    mix = bed + sub + crackles(rng, total) * 0.55 + flares(rng, total, [0.75, 3.75, dur + 0.75]) * 0.6 \
        + sparkles(rng, total) * 0.35
    mix = S.reverb(mix, rng, 1.2, 0.15, damp=5000)[: len(secs(total))]
    n, k = len(secs(dur)), len(secs(tail))
    fade = np.linspace(0, np.pi / 2, k)[:, None]
    loop = mix[:n].copy()
    loop[:k] = mix[:k] * np.sin(fade) + mix[n:n + k] * np.cos(fade)
    return loop


def ignite(rng):
    P = S.Palette({"sound": {"rootNote": "C#", "scale": "minor", "brightness": 0.6, "character": "warm"}})
    suck, _ = S.reverse_swell(P, rng, 1.0)
    w, wpk = S.whoosh(P, rng, 0.9, 0.3, 150, 4000, (-0.2, 0.2), tone=True)
    hit, _ = S.impact(P, rng, 1.8, hard=True)
    shim, _ = S.shimmer(P, rng, 1.4)
    fire = roar(rng, 2.5) * S.env_curve(2.5, [(0, 0), (0.15, 1), (1.5, 0.6), (2.5, 0)])[:, None]
    t_hit = 1.0
    return S.mix(suck * 0.7, S.at(w, t_hit - wpk), S.at(hit * 0.8, t_hit), S.at(shim * 0.5, t_hit + 0.05),
                 S.at(fire * 0.5, t_hit - 0.1)), t_hit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--out", default="out")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    loop = S.normalize(make_loop(rng, args.seconds), -20, -1.0)
    S.write_wav(os.path.join(args.out, "baddi3st_fire_loop.wav"), loop)
    ig, t_hit = ignite(rng)
    ig = S.trim_tail(S.normalize(ig, -16, -1.0))
    S.write_wav(os.path.join(args.out, "baddi3st_ignite.wav"), ig)
    print(f"fire loop {len(loop)/SR:.2f}s  {S.max_momentary_lufs(loop):.1f} LUFS-M | "
          f"ignite {len(ig)/SR:.2f}s, hit at {t_hit:.2f}s  {S.max_momentary_lufs(ig):.1f} LUFS-M")


if __name__ == "__main__":
    main()
