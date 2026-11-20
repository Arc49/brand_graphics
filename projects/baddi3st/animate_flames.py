#!/usr/bin/env python3
"""Animate the pink flames of a still logo into a seamless loop.

The chrome lettering, crown and ornaments stay pixel-for-pixel static; only the soft
magenta flames move. How it works:

1. Masks: the chrome is busy (high local edge energy) or bright and pale; the
   flames are smooth, saturated magenta. That gives a letter mask L and a flame
   mask F.
2. Background plate: the letters are inpainted out (normalised blur), so warping
   the flames never drags chrome pixels along.
3. Each frame warps the plate with a rising, vertically-tileable noise field
   (it scrolls exactly one period per loop, so the loop is seamless), flickers
   the flame brightness, and adds a few rising embers. Then the original
   letters go back on top.

  python3 animate_flames.py baddi3st_logo.jpg --out out/ [--seconds 6 --fps 30 --size 1920x1080]
"""

import argparse
import os
import subprocess

import numpy as np
from PIL import Image, ImageFilter

TAU = 2 * np.pi


def _box(a, k, axis):
    """Box filter of width 2k+1 along an axis (edge-clamped), via cumulative sums."""
    pad = [(0, 0)] * a.ndim
    pad[axis] = (k + 1, k)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    hi = np.take(c, np.arange(2 * k + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, c.shape[axis] - 2 * k - 1), axis=axis)
    return ((hi - lo) / (2 * k + 1)).astype(np.float32)


def blur(a, r):
    """Gaussian-like blur with sigma ≈ r (three box passes per axis)."""
    if r <= 0:
        return a
    k = max(1, int(round(np.sqrt(4 * r * r + 1) / 2)))  # 3 boxes of width 2k+1 ≈ gaussian sigma r
    for axis in (0, 1):
        for _ in range(3):
            a = _box(a, k, axis)
    return a


def maxf(a, size):
    img = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(img.filter(ImageFilter.MaxFilter(size)), dtype=np.float32) / 255


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def masks(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    lum = 0.2126 * R + 0.7152 * G + 0.0722 * B
    mx, mn = im.max(-1), im.min(-1)
    sat = (mx - mn) / (mx + 1e-4)
    l1 = blur(lum, 1.0)
    gy, gx = np.gradient(l1)
    energy = blur(np.hypot(gx, gy), 3.0)
    chrome = np.maximum(smooth(0.012, 0.03, energy), smooth(0.5, 0.75, lum) * smooth(0.75, 0.5, sat))
    # dark outlines inside the letters: keep anything enclosed by chrome
    L = blur(maxf(chrome, 7), 1.5)
    L = np.clip(L * 1.4, 0, 1)
    L_tight = np.clip(blur(maxf(chrome, 3), 1.0) * 1.3, 0, 1)  # opaque chrome for the alpha matte
    glow = smooth(0.02, 0.22, R) * smooth(0.45, 0.75, sat)
    F = glow * (1 - L)
    M = np.clip(blur(maxf(F, 61), 18) * 1.6, 0, 1) * (1 - L)  # region the flames may move in
    return L, F, M, L_tight


def inpaint(im, L):
    """Fill the letters with their surroundings (multi-scale normalised blur)."""
    w = (1 - L) ** 4
    out = im.copy()
    for r in (48, 24, 12, 6, 3):
        num = np.stack([blur(im[..., c] * w, r) for c in range(3)], -1)
        den = blur(w, r)[..., None] + 1e-5
        fill = num / den
        a = np.clip(L[..., None] * 1.2, 0, 1)
        out = out * (1 - a) + fill * a
        w = np.maximum(w, (1 - L) ** 2 * 0.5)
    return out


def tile_noise(h, w, scale, rng):
    """Smooth noise that tiles in both directions (FFT-filtered white noise), range ~[-1, 1]."""
    n = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    k = np.exp(-((fx * w / scale) ** 2 + (fy * h / scale) ** 2) / 2 * (scale / 8) ** 2)
    n = np.real(np.fft.ifft2(np.fft.fft2(n) * k))
    return (n / (np.abs(n).max() + 1e-6)).astype(np.float32)


def sample(img, x, y):
    """Bilinear sample img (H,W,C) at float coords."""
    h, w = img.shape[:2]
    x = np.clip(x, 0, w - 1.001)
    y = np.clip(y, 0, h - 1.001)
    x0 = x.astype(np.int32)
    y0 = y.astype(np.int32)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    a = img[y0, x0]
    b = img[y0, x0 + 1]
    c = img[y0 + 1, x0]
    d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="out")
    ap.add_argument("--seconds", type=float, default=6.0)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080", help="output size, or 'native'")
    ap.add_argument("--strength", type=float, default=1.0, help="flame motion amount")
    ap.add_argument("--embers", type=int, default=70)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--debug", action="store_true", help="also write mask images")
    ap.add_argument("--keep-black", action="store_true", help="keep the black background (no alpha)")
    ap.add_argument("--audio", default=None, help="WAV to mux into the outputs (same loop length)")
    ap.add_argument("--frames", default=None, help="only render these frame indices (comma list) as PNGs")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    src = Image.open(args.src).convert("RGB")
    if args.size != "native":
        W, H = map(int, args.size.split("x"))
        src = src.resize((W, H), Image.LANCZOS)
    im = np.asarray(src).astype(np.float32) / 255
    H, W = im.shape[:2]
    s = W / 1600  # tuned at 1600px wide

    L, F, M, L_tight = masks(im)
    plate = inpaint(im, L)
    if args.debug:
        for name, a in (("mask_letters", L), ("mask_flames", F), ("mask_motion", M)):
            Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(os.path.join(args.out, name + ".png"))
        Image.fromarray((np.clip(plate, 0, 1) * 255).astype(np.uint8)).save(os.path.join(args.out, "plate.png"))

    n_frames = int(round(args.seconds * args.fps))
    # noise layers, tileable vertically with period P; each scrolls k*P per loop => seamless
    P = H
    layers = [  # (scale px, amplitude px, scroll periods per loop, horizontal weight)
        (90 * s, 16 * s, 2, 1.0),
        (38 * s, 7 * s, 3, 0.8),
        (16 * s, 2.5 * s, 5, 0.6),
    ]
    noise = [(tile_noise(P, W, sc, rng), tile_noise(P, W, sc, rng), sc, amp, k, hw) for sc, amp, k, hw in layers]
    flick = tile_noise(P, W, 120 * s, rng)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

    # embers: spawn inside the flames, rise and fade, wrap around the loop period
    fy, fx = np.nonzero(F > 0.5)
    pick = rng.choice(len(fx), size=min(args.embers, len(fx)), replace=False) if len(fx) else []
    embers = [dict(x=float(fx[i]), y=float(fy[i]), phase=rng.uniform(0, 1), rise=rng.uniform(120, 260) * s,
                   r=rng.uniform(1.0, 2.6) * s, sway=rng.uniform(4, 14) * s, cycles=int(rng.integers(1, 3)))
              for i in pick]
    ember_col = np.array([1.0, 0.45, 0.85], np.float32)

    only = set(int(v) for v in args.frames.split(",")) if args.frames else None
    frame_dir = os.path.join(args.out, "frames")
    os.makedirs(frame_dir, exist_ok=True)
    for f in range(n_frames):
        if only is not None and f not in only:
            continue
        t = f / n_frames  # 0..1 over the loop
        dx = np.zeros((H, W), np.float32)
        dy = np.zeros((H, W), np.float32)
        for nx, ny, sc, amp, k, hw in noise:
            off = int(round(t * k * P))  # rising: pattern moves up => sample rows below
            rows = (np.arange(H) + off) % P
            dx += nx[rows] * amp * hw
            dy += ny[rows] * amp
        # flames lick upward: bias sampling downward a little, more where motion is strong
        dy += 6 * s
        m = M * args.strength
        warped = sample(plate, xx + dx * m, yy + dy * m)
        off = int(round(t * 1 * P))
        fl = flick[(np.arange(H) + off) % P]
        gain = 1 + 0.28 * fl * M + 0.06 * np.sin(TAU * t * 4) * M
        warped = warped * gain[..., None]

        # embers
        glow = np.zeros((H, W), np.float32)
        for e in embers:
            p = (t * e["cycles"] + e["phase"]) % 1.0
            ex = e["x"] + np.sin(TAU * (p * 2 + e["phase"])) * e["sway"]
            ey = e["y"] - p * e["rise"]
            a = np.sin(np.pi * p) ** 1.5
            r = e["r"]
            x0, x1 = int(max(ex - 4 * r, 0)), int(min(ex + 4 * r + 1, W))
            y0, y1 = int(max(ey - 4 * r, 0)), int(min(ey + 4 * r + 1, H))
            if x0 >= x1 or y0 >= y1:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
            glow[y0:y1, x0:x1] += a * np.exp(-((gx - ex) ** 2 + (gy - ey) ** 2) / (2 * r * r))
        glow *= (1 - L)

        bg = im * (1 - M[..., None]) + warped * M[..., None]
        bg = bg + glow[..., None] * ember_col  # additive glow
        out = np.clip(bg * (1 - L[..., None]) + im * L[..., None], 0, 1)  # letters back on top, untouched
        if args.keep_black:
            rgba = out
        else:
            # remove the black background: glow becomes see-through in proportion to its brightness
            # (luminance key + un-premultiply), chrome stays opaque
            a = np.clip((out.max(-1) - 0.02) / 0.98, 0, 1)
            a = np.maximum(a, L_tight)
            rgb = np.clip(out / np.maximum(a, 1e-3)[..., None], 0, 1)
            rgba = np.concatenate([rgb, a[..., None]], -1)
        Image.fromarray((rgba * 255 + 0.5).astype(np.uint8)).save(os.path.join(frame_dir, f"f{f:04d}.png"))
        if f % 30 == 0:
            print(f"  frame {f}/{n_frames}", flush=True)

    if only is None:
        base = os.path.splitext(os.path.basename(args.src))[0] + "_flames_loop"
        frames = ["-framerate", str(args.fps), "-i", os.path.join(frame_dir, "f%04d.png")]
        aud = ["-i", args.audio] if args.audio else []
        amap = ["-map", "0:v", "-map", "1:a"] if args.audio else []

        def enc(name, vcodec, acodec):
            subprocess.run(["ffmpeg", "-v", "error", "-y", *frames, *aud, *amap, *vcodec,
                            *(acodec if args.audio else []), "-shortest", os.path.join(args.out, name)], check=True)

        # editor master: ProRes 4444 with alpha (Premiere / Resolve / FCP / CapCut desktop)
        enc(base + ".mov", ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"],
            ["-c:a", "pcm_s24le"])
        # web / browser / OBS: VP9 with alpha
        enc(base + ".webm", ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-row-mt", "1",
                             "-auto-alt-ref", "0"], ["-c:a", "libopus", "-b:a", "192k"])
        # previews (no alpha): on black and on a grey checkerboard to show the transparency
        for name, bg in (("_preview_black.mp4", "color=c=black"), ("_preview_checker.mp4", "color=c=0x6a6a6a")):
            W_, H_ = Image.open(os.path.join(frame_dir, "f0000.png")).size
            bgsrc = f"{bg}:s={W_}x{H_}:r={args.fps}"
            graph = "[1:v]format=rgba[fg];[0:v]"
            if "checker" in name:
                graph += f"geq=lum='if(eq(mod(floor(X/40)+floor(Y/40),2),0),110,80)':cb=128:cr=128,"
            graph += "format=rgba[bg];[bg][fg]overlay=shortest=1,format=yuv420p[v]"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", bgsrc, *frames, *aud, "-filter_complex", graph,
                            "-map", "[v]", *(["-map", "2:a", "-c:a", "aac", "-b:a", "256k"] if args.audio else []),
                            "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-movflags", "+faststart", "-shortest",
                            os.path.join(args.out, base + name)], check=True)
        print("wrote", base + ".mov/.webm + previews in", args.out)

if __name__ == "__main__":
    main()
