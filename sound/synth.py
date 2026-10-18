#!/usr/bin/env python3
"""Brand SFX synthesizer.

Generates the whole sound-design library from brand/brand.json with numpy only:
UI ticks, whooshes, risers, impacts, tonal stings and a sonic logo. Tonal sounds
are tuned to the brand root note so every sting sits in the same key as the
brand music.

Each sound has a *sync point* ("hit"): the moment that should land on the visual
event (a whoosh's peak, a riser's end, an impact's onset). The renderer aligns
that point to the cue time of a motion template, so a riser automatically starts
early enough to peak exactly on the cut.

Usage:  python3 sound/synth.py [--brand brand/brand.json] [--out library/sfx]
"""

import argparse
import json
import os
import wave

import numpy as np

SR = 48000
NOTE_INDEX = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
              "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11]}


# ---------------------------------------------------------------- primitives

def secs(n):
    return np.arange(int(n * SR)) / SR


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def osc(freq, dur, shape="sine", phase=0.0):
    """Oscillator with per-sample frequency (scalar or array) via phase accumulation."""
    n = int(dur * SR)
    f = np.broadcast_to(np.asarray(freq, dtype=float), (n,)) if np.ndim(freq) == 0 else np.asarray(freq)[:n]
    ph = 2 * np.pi * np.cumsum(f) / SR + phase
    if shape == "sine":
        return np.sin(ph)
    if shape == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if shape == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    if shape == "square":
        return np.sign(np.sin(ph))
    raise ValueError(shape)


def env_exp(dur, attack=0.002, decay=0.2):
    t = secs(dur)
    a = np.clip(t / max(attack, 1e-5), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / max(decay, 1e-5))


def env_curve(dur, points):
    """Piecewise-linear envelope from [(time, level), ...]."""
    t = secs(dur)
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


def stft_shape(x, gain_fn, n_fft=2048, hop=256):
    """Time-varying spectral filter: gain_fn(t[frames,1], f[1,bins]) -> gain."""
    n = len(x)
    pad = np.concatenate([np.zeros(n_fft), x, np.zeros(n_fft)])
    win = np.hanning(n_fft)
    starts = np.arange(0, len(pad) - n_fft, hop)
    frames = np.stack([pad[s:s + n_fft] for s in starts]) * win
    X = np.fft.rfft(frames, axis=1)
    t = ((starts + n_fft / 2) - n_fft) / SR
    f = np.fft.rfftfreq(n_fft, 1 / SR)
    Y = np.fft.irfft(X * gain_fn(t[:, None], f[None, :]), n=n_fft, axis=1) * win
    out = np.zeros(len(pad))
    norm = np.zeros(len(pad))
    for i, s in enumerate(starts):
        out[s:s + n_fft] += Y[i]
        norm[s:s + n_fft] += win ** 2
    out /= np.maximum(norm, 1e-3)
    return out[n_fft:n_fft + n]


def bandpass_gain(fc, bw_oct):
    def g(t, f):
        c = np.interp(t, *fc) if isinstance(fc, tuple) else fc
        return np.exp(-0.5 * (np.log2(np.maximum(f, 1) / c) / bw_oct) ** 2)
    return g


def lowpass(x, cutoff, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / cutoff) ** (2 * order)), n=len(x))


def highpass(x, cutoff, order=2):
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(len(x), 1 / SR), 1e-3)
    return np.fft.irfft(X / np.sqrt(1 + (cutoff / f) ** (2 * order)), n=len(x))


def fft_convolve(a, b):
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(a, size) * np.fft.rfft(b, size), size)[:n]


def reverb(st, rng, decay=1.2, mix=0.25, predelay=0.012, damp=4000):
    """Stereo algorithmic-ish reverb: convolution with decorrelated, darkening noise tails."""
    ir_len = decay * 1.2
    t = secs(ir_len)
    out = []
    for ch in range(2):
        ir = rng.standard_normal(len(t)) * np.exp(-6.9 * t / decay)
        ir = stft_shape(ir, lambda tt, f: 1 / np.sqrt(1 + (f / (damp * np.exp(-tt / decay) + 300)) ** 4))
        ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out.append(fft_convolve(st[:, ch], ir))
    wet = np.stack(out, axis=1)
    dry = np.vstack([st, np.zeros((len(wet) - len(st), 2))])
    return dry * (1 - mix) + wet * mix * 0.6


def stereo(x, pan=0.0):
    """Constant-power pan. pan may be an array (-1 left .. 1 right)."""
    p = (np.asarray(pan) + 1) * np.pi / 4
    return np.stack([x * np.cos(p), x * np.sin(p)], axis=1)


def widen(rng, x, amount=0.6):
    """Stereo from mono by mixing in a decorrelated (all-pass-ish) copy."""
    X = np.fft.rfft(x)
    side = np.fft.irfft(X * np.exp(1j * rng.uniform(0, 2 * np.pi, len(X))), n=len(x))
    return np.stack([x + amount * side, x - amount * side], axis=1) / (1 + amount * 0.5)


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros((n, 2))
    for p in parts:
        p = p if p.ndim == 2 else stereo(p)
        out[:len(p)] += p
    return out


def at(x, offset):
    """Delay a stereo/mono signal by `offset` seconds."""
    pad = np.zeros((int(offset * SR),) + x.shape[1:])
    return np.concatenate([pad, x])


def saturate(x, drive):
    if drive <= 0:
        return x
    return np.tanh(x * (1 + drive * 4)) / np.tanh(1 + drive * 4)


def fade_out(st, dur=0.01):
    n = min(int(dur * SR), len(st))
    st[-n:] *= np.linspace(1, 0, n)[:, None]
    return st


# ---------------------------------------------------------------- loudness (ITU-R BS.1770, freq-domain K-weighting)

def _biquad_mag(f, b, a):
    w = 2 * np.pi * f / SR
    z = np.exp(-1j * w)
    return np.abs((b[0] + b[1] * z + b[2] * z ** 2) / (a[0] + a[1] * z + a[2] * z ** 2))


K_SHELF = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
K_HP = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def k_weight(x):
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = _biquad_mag(f, *K_SHELF) * _biquad_mag(f, *K_HP)
    return np.fft.irfft(X * g[:, None], n=len(x), axis=0)


def max_momentary_lufs(st):
    win, hop = int(0.4 * SR), int(0.1 * SR)
    y = k_weight(np.vstack([st, np.zeros((win, 2))]))
    best = 1e-12
    for s in range(0, max(len(y) - win, 1), hop):
        best = max(best, np.sum(np.mean(y[s:s + win] ** 2, axis=0)))
    return -0.691 + 10 * np.log10(best)


def true_peak_db(st):
    up = np.fft.irfft(np.fft.rfft(st, axis=0), n=len(st) * 4, axis=0) * 4
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def normalize(st, target_lufs, ceiling_db):
    st = st * 10 ** ((target_lufs - max_momentary_lufs(st)) / 20)
    tp = true_peak_db(st)
    if tp > ceiling_db:  # transient-heavy: soft-clip the peaks rather than lose loudness
        lim = 10 ** (ceiling_db / 20) * 0.98
        st = lim * np.tanh(st / lim)
    return st


def trim_tail(st, floor_db=-60, fade=0.05):
    """Cut the inaudible end of reverb tails, with a short fade."""
    env = np.max(np.abs(st), axis=1)
    loud = np.nonzero(env > 10 ** (floor_db / 20))[0]
    end = min(len(st), (loud[-1] if len(loud) else 0) + int(0.01 * SR))
    return fade_out(st[:end].copy(), fade)


def write_wav(path, st, bits=24):
    st = np.clip(st, -1, 1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(bits // 8)
        w.setframerate(SR)
        if bits == 24:
            ints = (st * (2 ** 23 - 1)).astype("<i4")
            raw = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
        else:
            raw = (st * 32767).astype("<i2").tobytes()
        w.writeframes(raw)


# ---------------------------------------------------------------- the library

class Palette:
    def __init__(self, brand):
        s = brand["sound"]
        self.root = NOTE_INDEX[s["rootNote"]]
        self.scale = SCALES[s.get("scale", "major")]
        self.bright = float(s.get("brightness", 0.6))
        self.drive = {"clean": 0.0, "warm": 0.25, "gritty": 0.6}.get(s.get("character", "clean"), 0.0)
        self.seed = int(s.get("seed", 1))

    def note(self, degree, octave=5):
        """Scale degree (0-based, can exceed 7) in the brand key -> Hz."""
        o, d = divmod(degree, len(self.scale))
        return mtof(12 * (octave + 1 + o) + self.root + self.scale[d])

    def hz(self, f):
        """Scale a filter frequency by the brand brightness (0.5 = neutral)."""
        return f * 2 ** ((self.bright - 0.5) * 2)


def bell(freq, dur, rng, index=2.0, ratio=3.5):
    """FM bell: modulator decays faster than carrier for a bright attack and pure tail."""
    t = secs(dur)
    mod_env = np.exp(-t / (dur * 0.15))
    mod = np.sin(2 * np.pi * freq * ratio * t + rng.uniform(0, 6)) * index * mod_env
    return np.sin(2 * np.pi * freq * t + mod) * env_exp(dur, 0.002, dur * 0.35)


def whoosh(P, rng, dur=0.5, peak=0.5, lo=300, hi=3500, pan=(-0.7, 0.7), tone=True):
    n = int(dur * SR)
    t = secs(dur)
    pk = peak * dur
    fc = (np.array([0, pk, dur]), np.array([P.hz(lo), P.hz(hi), P.hz(lo * 1.3)]))
    noise = stft_shape(rng.standard_normal(n), bandpass_gain(fc, 0.9))
    amp = np.where(t < pk, (t / pk) ** 2.2, np.exp(-(t - pk) / (dur * 0.18)))
    body = noise * amp
    if tone:  # faint doppler tone gives the whoosh "air pressure"
        f = np.where(t < pk, 90 + 60 * t / pk, 150 - 70 * (t - pk) / (dur - pk + 1e-9))
        body += 0.25 * osc(f, dur) * amp
    return fade_out(stereo(body, np.interp(t, [0, dur], pan)) * 1.0, 0.02), pk


def riser(P, rng, dur=2.0):
    t = secs(dur)
    n = len(t)
    fc = (np.array([0, dur]), np.array([P.hz(250), P.hz(7000)]))
    noise = stft_shape(rng.standard_normal(n), bandpass_gain(fc, 0.7))
    pitch = P.note(0, 3) * 2 ** (2 * (t / dur) ** 1.6)  # rises two octaves, accelerating
    synth = sum(osc(pitch * (1 + d), dur, "saw") for d in (-0.006, 0, 0.007)) / 3
    synth = stft_shape(synth, lambda tt, f: 1 / np.sqrt(1 + (f / (P.hz(400) + P.hz(5000) * tt / dur)) ** 4))
    trem_rate = 4 + 18 * (t / dur) ** 2
    trem = 0.65 + 0.35 * np.sin(2 * np.pi * np.cumsum(trem_rate) / SR)
    amp = (t / dur) ** 2.5
    body = (noise * 0.8 + synth * 0.5) * amp * trem
    st = widen(rng, body, 0.5 + 0.4 * (t[-1] / dur))
    return fade_out(st, 0.004), dur


def downlifter(P, rng, dur=1.5):
    st, _ = riser(P, rng, dur)
    return fade_out(st[::-1].copy(), 0.05), 0.0


def impact(P, rng, dur=1.4, hard=False):
    t = secs(dur)
    sub = osc(np.maximum(110 * np.exp(-t / 0.05), 0) + P.note(0, 1), dur) * env_exp(dur, 0.001, 0.35)
    thump = lowpass(rng.standard_normal(len(t)), P.hz(900)) * env_exp(dur, 0.0005, 0.04) * 1.5
    parts = [stereo(saturate(sub, P.drive + (0.4 if hard else 0.1))), widen(rng, thump, 0.3)]
    if hard:
        crack = highpass(rng.standard_normal(len(t)), P.hz(1800)) * env_exp(dur, 0.0003, 0.02)
        parts.append(widen(rng, crack, 0.8) * 0.8)
    st = mix(*parts)
    st = reverb(st, rng, decay=1.6 if hard else 0.9, mix=0.3 if hard else 0.15, damp=P.hz(3000))
    return fade_out(st, 0.05), 0.0


def sub_drop(P, rng, dur=1.8):
    t = secs(dur)
    f = P.note(0, 2) * 2 ** (-1.5 * t / dur)
    x = osc(f, dur) * env_curve(dur, [(0, 0), (0.005, 1), (dur * 0.6, 0.7), (dur, 0)])
    return stereo(saturate(x, 0.3 + P.drive)), 0.0


def click(P, rng, variant=0):
    dur = 0.06
    t = secs(dur)
    tick = osc(P.hz(2400) * (1 + 0.08 * variant), dur) * env_exp(dur, 0.0002, 0.006)
    snap = highpass(rng.standard_normal(len(t)), P.hz(3000)) * env_exp(dur, 0.0001, 0.003)
    return fade_out(stereo(tick * 0.6 + snap * 0.5), 0.005), 0.0


def tick(P, rng, variant=0):
    dur = 0.05
    x = osc(P.note(4 + variant, 6), dur, "tri") * env_exp(dur, 0.0005, 0.012)
    return fade_out(stereo(x), 0.005), 0.0


def pop(P, rng, variant=0):
    dur = 0.18
    t = secs(dur)
    f = P.note(variant * 2, 5) * 1.6 * np.exp(-t / 0.03) + P.note(variant * 2, 4)
    body = osc(f, dur) * env_exp(dur, 0.0005, 0.045)
    air = highpass(rng.standard_normal(len(t)), 4000) * env_exp(dur, 0.0002, 0.004) * 0.3
    return fade_out(stereo(body + air), 0.01), 0.0


def blip(P, rng, up=True):
    dur = 0.22
    degs = (0, 4) if up else (4, 0)
    a = osc(P.note(degs[0], 6), 0.07, "tri") * env_exp(0.07, 0.001, 0.03)
    b = osc(P.note(degs[1], 6), 0.15, "tri") * env_exp(0.15, 0.001, 0.05)
    st = mix(stereo(a, -0.15), at(stereo(b, 0.15), 0.06))
    return fade_out(reverb(st, rng, 0.5, 0.12)[:int(dur * 1.8 * SR)], 0.02), 0.0


def typing(P, rng, keys=10, rate=0.075):
    out = []
    for k in range(keys):
        c, _ = click(P, rng, k % 3)
        jitter = rng.uniform(-0.015, 0.015)
        out.append(at(c * rng.uniform(0.6, 1.0), max(k * rate + jitter, 0)))
    return mix(*out), 0.0


def glitch(P, rng, dur=0.45):
    n = int(dur * SR)
    x = np.zeros(n)
    pos = 0
    while pos < n:
        seg = int(rng.uniform(0.012, 0.05) * SR)
        kind = rng.integers(0, 3)
        if kind == 0:
            s = rng.standard_normal(seg)
            s = np.round(s * 4) / 4  # bitcrush
        elif kind == 1:
            s = osc(rng.choice([P.note(0, 4), P.note(4, 5), P.note(2, 6)]), seg / SR, "square")
        else:
            s = np.zeros(seg)
        s = np.resize(s, seg)
        hold = int(rng.integers(1, 6))
        s = np.repeat(s[::hold], hold)[:seg]  # sample-rate reduction
        end = min(pos + seg, n)
        x[pos:end] = s[:end - pos] * rng.uniform(0.3, 1)
        pos += seg
    x = lowpass(x, P.hz(9000))
    return fade_out(stereo(x * 0.6, rng.uniform(-0.4, 0.4, 1)[0]), 0.01), 0.0


def chime(P, rng, dur=2.2):
    parts = [stereo(bell(P.note(d, 5), dur, rng), pan) * g
             for d, pan, g in ((0, -0.2, 1.0), (4, 0.2, 0.7), (7, 0, 0.5))]
    return fade_out(reverb(mix(*parts), rng, 2.0, 0.3, damp=P.hz(6000)), 0.1), 0.0


def success(P, rng):
    notes = [0, 2, 4, 7]
    parts = [at(stereo(bell(P.note(d, 5), 0.9, rng, index=1.2), -0.3 + 0.2 * i), i * 0.07)
             for i, d in enumerate(notes)]
    return fade_out(reverb(mix(*parts), rng, 1.4, 0.25, damp=P.hz(7000)), 0.1), 0.21


def shimmer(P, rng, dur=1.6):
    parts = []
    for i in range(14):
        d = int(rng.choice([0, 2, 4, 7, 9, 11]))
        parts.append(at(stereo(bell(P.note(d, 6 + i % 2), 0.5, rng, 0.8, 2.0) * rng.uniform(0.2, 0.5),
                               rng.uniform(-0.8, 0.8)), i * dur / 20))
    return fade_out(reverb(mix(*parts), rng, 2.2, 0.45, damp=P.hz(9000)), 0.1), 0.0


def reverse_swell(P, rng, dur=1.2):
    """Reversed chord tail that sucks into the cut: the classic 'reverse reverb' transition."""
    st, _ = chime(P, rng, 1.8)
    w, _ = whoosh(P, rng, 1.2, 0.5, 200, 2500, (0.5, -0.5), tone=False)
    rev = st[::-1].copy()[-int(dur * SR):]
    rev = mix(rev, w[::-1].copy()[-int(dur * SR):] * 0.5)
    return fade_out(rev, 0.004), dur


def sonic_logo(P, rng):
    """Brand signature (~2.4s): air-in, low hit, then a 4-note motif in the brand key."""
    w, wpk = whoosh(P, rng, 0.5, 0.95, 250, 3000, (-0.4, 0.2))
    hit, _ = impact(P, rng, 1.6)
    motif = [(0, 0.00, 5), (4, 0.16, 5), (7, 0.32, 5), (0, 0.52, 6)]
    bells = [at(stereo(bell(P.note(d, o), 1.6, rng, 1.6, 3.0) * (1.0 if i == 3 else 0.8),
                       (-0.3, 0.1, 0.3, 0)[i]), t0) for i, (d, t0, o) in enumerate(motif)]
    pad = stereo(sum(osc(P.note(d, 4) * (1 + det), 1.8, "tri") for d in (0, 4, 7) for det in (-0.003, 0.003))
                 * env_curve(1.8, [(0, 0), (0.3, 0.12), (1.1, 0.1), (1.8, 0)]))
    hit_t = wpk
    st = mix(w * 0.8, at(hit * 0.7, hit_t), at(mix(*bells), hit_t), at(pad, hit_t))
    return fade_out(reverb(st, rng, 2.2, 0.22, damp=P.hz(6000)), 0.3), hit_t


# ---------------------------------------------------------------- desktop + console UI packs
# Original sounds in the *style* of desktop-OS alerts and handheld-console menus.
# They are synthesised here rather than copied from Apple or Nintendo, whose
# system sounds are copyrighted and would draw Content ID claims on published videos.

def struck(freqs, amps, decays, dur, rng):
    """Inharmonic struck-object model: sum of exponentially decaying partials."""
    t = secs(max(dur, 7 * max(decays)))  # run until the partials are ~-60 dB, so nothing gets cut off
    x = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / d) for f, a, d in zip(freqs, amps, decays))
    return x * np.clip(t / 0.0015, 0, 1)


def glass_ping(P, rng):
    f0 = P.note(4, 6)
    x = struck([f0 * r for r in (1, 2.76, 5.40, 8.93)], [1, 0.5, 0.25, 0.12], [0.55, 0.3, 0.15, 0.08], 1.2, rng)
    return fade_out(reverb(stereo(x), rng, 1.0, 0.18, damp=9000), 0.05), 0.0


def tink(P, rng):
    f0 = P.note(0, 7)
    x = struck([f0, f0 * 2.31, f0 * 3.9], [1, 0.4, 0.2], [0.07, 0.04, 0.02], 0.25, rng)
    return fade_out(stereo(x), 0.01), 0.0


def bubble(P, rng):
    dur = 0.16
    t = secs(dur)
    f = P.note(0, 5) * 2 ** (1.3 * (t / dur) ** 0.5)  # upward chirp = bubble
    return fade_out(stereo(osc(f, dur) * env_exp(dur, 0.002, 0.04)), 0.01), 0.0


def bottle(P, rng):
    dur = 0.6
    t = secs(dur)
    f = P.note(0, 4)
    breath = stft_shape(rng.standard_normal(len(t)), bandpass_gain(f * 1.02, 0.08)) * 3
    tone = osc(f * (1 + 0.004 * np.sin(2 * np.pi * 5 * t)), dur)
    env = env_curve(dur, [(0, 0), (0.06, 1), (0.25, 0.7), (dur, 0)])
    return fade_out(reverb(stereo((tone * 0.6 + breath * 0.5) * env), rng, 0.8, 0.15), 0.05), 0.0


def funk(P, rng):
    parts = []
    for i, (d, o) in enumerate(((0, 3), (7, 3))):
        dur = 0.16
        t = secs(dur)
        x = osc(P.note(d, o), dur, "saw")
        x = stft_shape(x, lambda tt, f: 1 / np.sqrt(1 + (f / (300 + 3500 * np.exp(-tt / 0.03))) ** 4))
        parts.append(at(stereo(saturate(x * env_exp(dur, 0.002, 0.06), 0.4)), i * 0.11))
    return fade_out(mix(*parts), 0.01), 0.0


def purr(P, rng):
    dur = 0.55
    t = secs(dur)
    am = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 28 * t))
    x = lowpass(rng.standard_normal(len(t)), P.hz(600)) * am * env_curve(dur, [(0, 0), (0.03, 1), (0.4, 0.8), (dur, 0)])
    x += osc(P.note(0, 2), dur, "tri") * 0.4 * am * env_exp(dur, 0.01, 0.25)
    return fade_out(stereo(x), 0.03), 0.0


def sonar(P, rng):
    x = struck([P.note(4, 5)], [1], [0.18], 0.5, rng)
    echoes = [at(stereo(x * g, pan), d) for d, g, pan in ((0, 1, 0), (0.28, 0.45, -0.5), (0.56, 0.22, 0.5), (0.84, 0.1, 0))]
    return fade_out(reverb(mix(*echoes), rng, 1.4, 0.25, damp=3000), 0.1), 0.0


def hero(P, rng):
    dur = 0.9
    t = secs(dur)
    rise = 2 ** (0.5 * (1 - np.exp(-t / 0.08)) - 0.5)
    chord = sum(osc(P.note(d, 4) * rise * (1 + det), dur, "saw") for d in (0, 2, 4) for det in (-0.004, 0.004)) / 6
    chord = stft_shape(chord, lambda tt, f: 1 / np.sqrt(1 + (f / (500 + 4000 * np.minimum(tt / 0.25, 1))) ** 4))
    st = widen(rng, chord * env_curve(dur, [(0, 0), (0.12, 1), (0.5, 0.8), (dur, 0)]), 0.5)
    return fade_out(reverb(st, rng, 1.2, 0.2), 0.08), 0.12


def snap_in(P, rng):
    """Console controller attaching: two sharp plastic clicks with a tiny resonant body."""
    def snap(g, f):
        dur = 0.05
        t = secs(dur)
        n = highpass(rng.standard_normal(len(t)), 2500) * env_exp(dur, 0.0001, 0.0025)
        body = osc(f, dur) * env_exp(dur, 0.0003, 0.012)
        return stereo((n + 0.5 * body) * g)
    return fade_out(mix(snap(1.0, 1900), at(snap(0.7, 2300), 0.045)), 0.005), 0.0


def menu_move(P, rng, variant=0):
    dur = 0.06
    f = P.note(4 + 2 * variant, 6)
    x = osc(f * (1 + 0.15 * np.exp(-secs(dur) / 0.004)), dur, "tri") * env_exp(dur, 0.0004, 0.014)
    return fade_out(stereo(x), 0.005), 0.0


def menu_select(P, rng):
    a = osc(P.note(4, 5), 0.05) * env_exp(0.05, 0.001, 0.02)
    b = osc(P.note(4, 6), 0.12) * env_exp(0.12, 0.001, 0.045)
    return fade_out(mix(stereo(a), at(stereo(b), 0.035)), 0.01), 0.0


def menu_back(P, rng):
    dur = 0.12
    t = secs(dur)
    f = P.note(4, 6) * 2 ** (-1 * t / dur)
    return fade_out(stereo(osc(f, dur) * env_exp(dur, 0.001, 0.04)), 0.01), 0.0


def console_launch(P, rng):
    notes = [(0, 5), (4, 5), (7, 5), (0, 6)]
    parts = [at(stereo(struck([P.note(d, o), P.note(d, o) * 4.0], [1, 0.15], [0.35, 0.05], 0.6, rng), -0.3 + 0.2 * i), i * 0.045)
             for i, (d, o) in enumerate(notes)]
    w, _ = whoosh(P, rng, 0.5, 0.35, 600, 6000, (-0.3, 0.3), False)
    return fade_out(reverb(mix(*parts, w * 0.35), rng, 1.0, 0.2, damp=8000), 0.05), 0.0


def console_home(P, rng):
    x = struck([P.note(0, 4), P.note(0, 4) * 2.0, P.note(0, 4) * 3.01], [1, 0.3, 0.1], [0.25, 0.1, 0.05], 0.6, rng)
    return fade_out(reverb(stereo(x), rng, 0.7, 0.12), 0.03), 0.0


def console_error(P, rng):
    def buzz():
        dur = 0.09
        x = lowpass(osc(P.note(1, 3), dur, "square"), 1800) * env_curve(dur, [(0, 0), (0.005, 1), (0.07, 0.8), (dur, 0)])
        return stereo(x * 0.7)
    return fade_out(mix(buzz(), at(buzz(), 0.12)), 0.01), 0.0


def toggle(P, rng, on=True):
    c, _ = snap_in(P, rng)
    tone = menu_select(P, rng)[0] if on else menu_back(P, rng)[0]
    return fade_out(mix(c[: int(0.04 * SR)] * 0.8, at(tone * 0.6, 0.02)), 0.01), 0.0


# name -> (category, loudness key, builder, description)
def catalog(P):
    c = {}

    def add(name, cat, loud, fn, desc):
        c[name] = (cat, loud, fn, desc)

    for i in range(3):
        add(f"click_{i+1:02d}", "ui", "ui", lambda r, i=i: click(P, r, i), "UI click — buttons, cursor, toggles")
        add(f"pop_{i+1:02d}", "ui", "ui", lambda r, i=i: pop(P, r, i), "Element pop-in (callouts, icons, words)")
        add(f"tick_{i+1:02d}", "ui", "ui", lambda r, i=i: tick(P, r, i), "Counter / list-item tick")
        add(f"whoosh_short_{i+1:02d}", "transition", "transition",
            lambda r: whoosh(P, r, 0.45, 0.55, 350, 4200), "Fast whoosh for text in/out, quick cuts")
    add("whoosh_long_01", "transition", "transition", lambda r: whoosh(P, r, 1.0, 0.6, 200, 3000), "Big pass-by for scene transitions")
    add("whoosh_long_02", "transition", "transition", lambda r: whoosh(P, r, 1.1, 0.5, 180, 2600, (0.7, -0.7)), "Pass-by, right to left")
    add("swish_01", "transition", "transition", lambda r: whoosh(P, r, 0.22, 0.45, 1500, 9000, (-0.3, 0.3), False), "Tiny high swish: lower thirds, small slides")
    add("blip_up", "ui", "ui", lambda r: blip(P, r, True), "Positive two-note blip (appear)")
    add("blip_down", "ui", "ui", lambda r: blip(P, r, False), "Two-note blip (dismiss)")
    add("typing_01", "ui", "ui", lambda r: typing(P, r), "Keyboard typing burst for typewriter text")
    add("glitch_01", "transition", "transition", lambda r: glitch(P, r), "Digital glitch stutter")
    add("glitch_02", "transition", "transition", lambda r: glitch(P, r, 0.3), "Short digital glitch")
    add("riser_1s", "riser", "riser", lambda r: riser(P, r, 1.0), "Short build into a reveal (sync = end)")
    add("riser_2s", "riser", "riser", lambda r: riser(P, r, 2.0), "Build into a big moment (sync = end)")
    add("downlifter_01", "riser", "riser", lambda r: downlifter(P, r, 1.5), "Release after a peak / scene end")
    add("reverse_swell", "transition", "tonal", lambda r: reverse_swell(P, r), "Reverse-reverb suck into a cut (sync = end)")
    add("impact_soft", "impact", "impact", lambda r: impact(P, r, 1.2, False), "Soft low hit for titles / reveals")
    add("impact_hard", "impact", "impact", lambda r: impact(P, r, 1.8, True), "Cinematic hit for big statements")
    add("sub_drop", "impact", "impact", lambda r: sub_drop(P, r), "Sub-bass drop under a reveal")
    add("chime", "tonal", "tonal", lambda r: chime(P, r), "Brand-key chord chime: info cards, tips")
    add("success", "tonal", "tonal", lambda r: success(P, r), "Rising arpeggio: wins, results, checkmarks")
    add("shimmer", "tonal", "tonal", lambda r: shimmer(P, r), "Sparkle sweetener on reveals")
    add("sonic_logo", "brand", "sonicLogo", lambda r: sonic_logo(P, r), "Brand audio signature for intro / outro")
    # appended after the core set so existing sounds keep their random seeds
    add("glass_ping", "desktop", "ui", lambda r: glass_ping(P, r), "Struck-glass alert ping (desktop-OS style)")
    add("tink", "desktop", "ui", lambda r: tink(P, r), "Tiny metallic tink: subtle confirm")
    add("bubble_pop", "desktop", "ui", lambda r: bubble(P, r), "Rising bubble pop: element appears")
    add("bottle", "desktop", "ui", lambda r: bottle(P, r), "Blown-bottle tone: soft notification")
    add("funk_bounce", "desktop", "ui", lambda r: funk(P, r), "Two-note funky pluck: playful alert")
    add("purr", "desktop", "ui", lambda r: purr(P, r), "Low purr: drag, haptic, buzz")
    add("sonar_ping", "desktop", "ui", lambda r: sonar(P, r), "Sonar ping with echoes: scanning / searching")
    add("hero_rise", "desktop", "tonal", lambda r: hero(P, r), "Rising chord swell: success, unlock")
    add("snap_in", "console", "ui", lambda r: snap_in(P, r), "Controller-attach double click (handheld-console style)")
    add("menu_move_01", "console", "ui", lambda r: menu_move(P, r, 0), "Cursor move tick between menu items")
    add("menu_move_02", "console", "ui", lambda r: menu_move(P, r, 1), "Cursor move tick (variant)")
    add("menu_select", "console", "ui", lambda r: menu_select(P, r), "Bright two-step select")
    add("menu_back", "console", "ui", lambda r: menu_back(P, r), "Down-gliding back / cancel")
    add("console_launch", "console", "tonal", lambda r: console_launch(P, r), "App-launch arpeggio + air")
    add("console_home", "console", "ui", lambda r: console_home(P, r), "Soft home-button bonk")
    add("console_error", "console", "ui", lambda r: console_error(P, r), "Double buzz: wrong / myth busted")
    add("toggle_on", "console", "ui", lambda r: toggle(P, r, True), "Switch on: click + up blip")
    add("toggle_off", "console", "ui", lambda r: toggle(P, r, False), "Switch off: click + down blip")
    return c


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--brand", default=os.path.join(root, "brand", "brand.json"))
    ap.add_argument("--out", default=os.path.join(root, "library", "sfx"))
    ap.add_argument("--only", nargs="*", help="generate only these sound names")
    args = ap.parse_args()

    brand = json.load(open(args.brand))
    global SR
    SR = int(brand["sound"].get("sampleRate", 48000))
    bits = int(brand["sound"].get("bitDepth", 24))
    loud = brand["sound"]["loudness"]
    P = Palette(brand)

    mpath = os.path.join(args.out, "sfx.json")
    # keep entries we don't generate (imported third-party packs, or sounds skipped by --only)
    prev = json.load(open(mpath))["sounds"] if os.path.exists(mpath) else {}
    names = set(catalog(P))
    keep = {k: v for k, v in prev.items() if "license" in v or (args.only and k in names)}
    manifest = {"sampleRate": SR, "bitDepth": bits, "rootNote": brand["sound"]["rootNote"],
                "scale": brand["sound"].get("scale", "major"), "sounds": keep}
    for i, (name, (cat, lkey, fn, desc)) in enumerate(catalog(P).items()):
        if args.only and name not in args.only:
            continue
        rng = np.random.default_rng(P.seed * 1000 + i)
        st, sync = fn(rng)
        st = trim_tail(normalize(st, loud[lkey], loud["truePeakCeiling"]))
        rel = f"{cat}/{name}.wav"
        write_wav(os.path.join(args.out, rel), st, bits)
        manifest["sounds"][name] = {
            "file": rel, "category": cat, "description": desc,
            "duration": round(len(st) / SR, 3), "sync": round(float(sync), 3),
            "lufsMomentaryMax": round(max_momentary_lufs(st), 1), "truePeakDb": round(true_peak_db(st), 1),
        }
        print(f"  {rel:34s} {len(st)/SR:5.2f}s  sync@{sync:4.2f}s  {manifest['sounds'][name]['lufsMomentaryMax']:6.1f} LUFS-M")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
