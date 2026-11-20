#!/usr/bin/env python3
"""BADDI3ST C/S logo reveal (transparent background) with sound design.

Sequence
  1. B-A-D-D-I-3-S-T (still grey/silver chrome) fly in one at a time and SLAM into the "wall": squash, flash,
     shockwave ring, sparks, camera shake, metal slam sound (pitch rises per letter).
  2. C/S slams in as one compact block: bigger hit; the shockwave reveals the
     chrome ornaments.
  3. Flames ignite FROM C/S and spread outwards (no fire before this point); the pink colour
     spreads with them across letters and ornaments, with a hot bright front.
  4. The 3D crown (crown3d/: procedural chrome model rendered with Three.js) drops in
     spinning, lands, then keeps turning on its axis (360° every 2.6 s, short hold facing front).

The still logo is cut into layers (letters, C/S, crown, ornaments, flames) by
geometry plus the chrome mask from animate_flames.py; the flames reuse its
rising-noise warp.

  python3 logo_reveal.py baddi3st_logo.jpg --out out_reveal
  python3 logo_reveal.py baddi3st_logo.jpg --out /tmp/x --snap 0.5,1.0,2.3,3.0,4.6,6.2   # quick contact sheet
"""

import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageOps

import animate_flames as A

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "sound"))
import synth as S  # noqa: E402

TAU = 2 * np.pi

# ------------------------------------------------------------------ timeline (seconds)
T_LETTERS = [0.35 + i * 0.2 for i in range(8)]  # impact times B A D D I 3 S T
FLY = 0.16  # flight time before each letter impact
T_CS = 2.25  # C/S impact
FLY_CS = 0.24
T_ORN = T_CS  # ornaments revealed by the C/S shockwave
T_FIRE = 2.45  # flames ignite from C/S
FIRE_SPREAD = 1.2
T_CROWN_DROP, T_CROWN_LAND = 3.55, 4.45
SPIN_START, SPIN_PERIOD, SPIN_TURN = 5.4, 2.6, 1.6  # each period: 1.6 s full turn + hold
DURATION = 10.0

# ------------------------------------------------------------------ geometry (native 1600x900 coords)
# slanted cut lines between letters: (x at y=255, x at y=568); the last one is a polyline
CUTS = [
    [(175, 255), (105, 568)],          # left of B
    [(445, 255), (352, 568)],          # B | A
    [(560, 255), (545, 568)],          # A | D
    [(722, 255), (700, 568)],          # D | D
    [(910, 255), (893, 568)],          # D | I
    [(1000, 255), (968, 568)],         # I | 3
    [(1185, 255), (1160, 568)],        # 3 | S
    [(1300, 255), (1335, 568)],        # S | T
    [(1600, 255), (1600, 380), (1455, 425), (1480, 568)],  # right of T
]
CS_CENTER = (800, 625)
CROWN_POLY = [(540, 0), (1060, 0), (1060, 125), (1012, 205), (1012, 298), (588, 298), (588, 205), (540, 125)]


def cut_x(cut, yn):
    xs = [p[0] for p in cut]
    ys = [p[1] for p in cut]
    return np.interp(yn, ys, xs)


def smoothstep(e0, e1, x):
    return A.smooth(e0, e1, x)


def ease_in(x):
    return np.clip(x, 0, 1) ** 3


def ease_out(x):
    x = np.clip(x, 0, 1)
    return 1 - (1 - x) ** 3


def ease_inout(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


class Crown3D:
    """Pre-rendered 3D turntable (crown3d/render.mjs) placed where the logo's crown sits."""

    def __init__(self, frames_dir, s, step=2, band_w=415, front_bottom=(800, 305), top_limit=8):
        import json
        anchors = json.load(open(os.path.join(os.path.dirname(frames_dir), "anchors.json")))
        self.dir, self.step = frames_dir, step
        # scale: as wide as the logo's crown band, but never taller than the space above the letters
        top = min(np.nonzero(np.asarray(Image.open(os.path.join(frames_dir, f"a{a:03d}.png")))[..., 3].max(1) > 10)[0].min()
                  for a in range(0, 360, 10))
        k_w = band_w * s / (anchors["right"][0] - anchors["left"][0])
        k_h = (front_bottom[1] - top_limit) * s / (anchors["frontBottom"][1] - top)
        self.k = min(k_w, k_h)
        self.anchor = np.array(anchors["frontBottom"], float) * self.k
        self.target = np.array(front_bottom, float) * s
        self.center = self.target + np.array([0, -150 * s])
        self.cache = {}
        self.s = s

    def _img(self, idx):
        if idx not in self.cache:
            im = Image.open(os.path.join(self.dir, f"a{idx * self.step:03d}.png")).convert("RGBA")
            im = im.resize((int(im.width * self.k), int(im.height * self.k)), Image.LANCZOS)
            a = np.asarray(im).astype(np.float32) / 255
            rgb, al = a[..., :3], a[..., 3]
            # pink bloom behind the chrome, like the glow in the logo
            g = np.clip(A.blur(al * rgb.max(-1), 9 * self.s) * 1.3, 0, 0.75)
            pink = np.array([1.0, 0.25, 0.75], np.float32)
            oa = al + g * (1 - al)
            orgb = (rgb * al[..., None] + pink * (g * (1 - al))[..., None]) / np.maximum(oa, 1e-4)[..., None]
            self.cache[idx] = np.dstack([orgb, oa])
        return self.cache[idx]

    def render(self, theta, offset=(0, 0), flash=0.0, opacity=1.0):
        n = 360 // self.step
        idx = int(round(np.degrees(theta) % 360 / self.step)) % n
        a = self._img(idx)
        if flash > 0.001 or opacity < 0.999:
            a = a.copy()
            a[..., :3] = a[..., :3] + (1 - a[..., :3]) * flash
            a[..., 3] *= opacity
        im = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        return im, self.target - self.anchor + np.array(offset, float)


class Layer:
    """A static RGBA crop of one element, with its centre in full-frame coords."""

    def __init__(self, rgba, name, grey=None):
        a = rgba[..., 3]
        ys, xs = np.nonzero(a > 0.02)
        self.name = name
        if len(xs) == 0:
            self.empty = True
            return
        self.empty = False
        pad = 4
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgba.shape[0])
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgba.shape[1])
        crop = rgba[y0:y1, x0:x1]
        self.arr = crop  # float, straight alpha
        self.arr_grey = (grey if grey is not None else to_grey(rgba))[y0:y1, x0:x1]
        self.img = Image.fromarray((np.clip(crop, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        self.img_grey = Image.fromarray((np.clip(self.arr_grey, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        self.box = (y0, y1, x0, x1)
        self.origin = np.array([x0, y0], float)
        w = crop[..., 3]
        gy, gx = np.mgrid[0:crop.shape[0], 0:crop.shape[1]]
        self.center = np.array([(gx * w).sum() / w.sum() + x0, (gy * w).sum() / w.sum() + y0])

    def render(self, sx=1.0, sy=1.0, offset=(0, 0), flash=0.0, opacity=1.0, mirror=False, shade=1.0, pink=None):
        """Return (PIL image, top-left position) after scaling about the centre.

        pink: None/1 = original pink chrome, 0 = grey chrome, or (mask, front) full-frame arrays
        for the pink colour spreading across the element."""
        if pink is None or (np.isscalar(pink) and pink >= 1):
            src = self.img
        elif np.isscalar(pink):
            src = self.img_grey
        else:
            y0, y1, x0, x1 = self.box
            m = pink[0][y0:y1, x0:x1, None]
            fr = pink[1][y0:y1, x0:x1, None]
            a = self.arr_grey * (1 - m) + self.arr * m
            a[..., :3] = a[..., :3] + (1 - a[..., :3]) * fr * 0.8
            src = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        w, h = src.size
        nw, nh = max(1, int(round(w * sx))), max(1, int(round(h * sy)))
        im = src if (nw, nh) == (w, h) else src.resize((nw, nh), Image.BICUBIC)
        if mirror:
            im = ImageOps.mirror(im)
        if flash > 0.001 or opacity < 0.999 or shade < 0.999:
            a = np.asarray(im).astype(np.float32) / 255
            rgb = a[..., :3] * shade
            rgb = rgb + (1 - rgb) * flash
            al = a[..., 3] * opacity
            im = Image.fromarray((np.clip(np.dstack([rgb, al]), 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
        pos = self.center + (self.origin - self.center) * np.array([sx, sy]) + np.array(offset, float)
        return im, pos


def to_grey(rgba, solid=None):
    """Pink chrome -> neutral silver chrome (a touch more contrast, cool tint).

    solid: optional 0..1 map; the soft pink glow (not solid metal) is hidden in the grey phase."""
    rgb = rgba[..., :3]
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    lum = np.maximum(lum, rgb.max(-1) * 0.55)  # pink highlights would read too dark otherwise
    g = np.clip((lum - 0.5) * 1.15 + 0.5, 0, 1)
    out = rgba.copy()
    out[..., :3] = g[..., None] * np.array([0.93, 0.95, 1.0], np.float32)
    if solid is not None:
        out[..., 3] *= solid
    return out


def paste(canvas, im, pos):
    """alpha_composite with clipping (PIL needs the source inside the canvas)."""
    x, y = int(round(pos[0])), int(round(pos[1]))
    W, H = canvas.size
    w, h = im.size
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(w, W - x), min(h, H - y)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    canvas.alpha_composite(im.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def key_rgba(rgb, extra_alpha=None):
    """Remove black: luminance key + un-premultiply."""
    a = np.clip((rgb.max(-1) - 0.02) / 0.98, 0, 1)
    if extra_alpha is not None:
        a = np.maximum(a, extra_alpha)
    out = np.clip(rgb / np.maximum(a, 1e-3)[..., None], 0, 1)
    return np.concatenate([out, a[..., None]], -1)


def slam_curve(t, t_hit, fly, start_scale, squash=0.16):
    """Scale/squash/opacity/flash for an element that flies at the camera-wall and splats."""
    if t < t_hit - fly:
        return None
    if t < t_hit:  # flying in (towards the wall = shrinking from huge), accelerating
        p = ease_in((t - (t_hit - fly)) / fly)
        sc = start_scale + (1 - start_scale) * p
        return dict(sx=sc, sy=sc, opacity=min(1, p * 2.5), flash=0.0)
    dt = t - t_hit
    d = np.exp(-dt / 0.09) * np.cos(TAU * dt * 6.5)  # damped wobble of the splat
    sink = 0.05 * np.exp(-dt / 0.06)  # pushed into the wall for a moment
    return dict(sx=(1 + squash * d) * (1 - sink), sy=(1 - squash * 0.85 * d) * (1 - sink), opacity=1.0,
                flash=0.85 * np.exp(-dt / 0.07))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="out_reveal")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--snap", default=None, help="comma list of times: write a contact sheet only")
    ap.add_argument("--no-video", action="store_true", help="only build the audio")
    ap.add_argument("--encode-only", action="store_true", help="rebuild audio and re-encode existing frames")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    src = Image.open(args.src).convert("RGB")
    W, H = map(int, args.size.split("x"))
    src = src.resize((W, H), Image.LANCZOS)
    im = np.asarray(src).astype(np.float32) / 255
    s = W / 1600

    audio_path = os.path.join(args.out, "baddi3st_reveal_sfx.wav")
    build_audio(audio_path, rng, s)
    if args.no_video:
        return
    if args.encode_only:
        encode(args.out, os.path.join(args.out, "frames"), args.fps, audio_path, W, H)
        return

    print("cutting layers…", flush=True)
    L, F, M, Lt = A.masks(im)
    plate = A.inpaint(im, L)
    chrome = key_rgba(im, Lt)
    chrome[..., 3] *= L  # glow outside the chrome belongs to the flame layer

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xn, yn = xx / s, yy / s
    # crown silhouette (keeps the side wing-blades with the ornaments)
    poly = Image.new("L", (W, H), 0)
    from PIL import ImageDraw
    ImageDraw.Draw(poly).polygon([(x * s, y * s) for x, y in CROWN_POLY], fill=255)
    crown_m = np.asarray(poly) > 127
    cs_m = ((xn >= 570) & (xn <= 1040) & (yn >= 540) & (yn <= 693)) | \
           ((yn >= 586) & (yn <= 616) & (((xn >= 285) & (xn < 553)) | ((xn > 1052) & (xn <= 1310))))
    band = (yn >= 255) & (yn <= 568) & ~crown_m & ~cs_m
    letter_ms = []
    for i in range(8):
        left, right = cut_x(CUTS[i], yn), cut_x(CUTS[i + 1], yn)
        letter_ms.append(band & (xn >= left) & (xn < right))
    used = crown_m | cs_m | np.any(letter_ms, axis=0)
    orn_m = ~used

    # "solid" metal vs soft magenta glow: glow pixels are hidden until the pink arrives
    # metal has crisp edges everywhere; flame wisps (even their pale hot cores) are soft
    lum = A.blur(0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2], 1.0)
    gy_, gx_ = np.gradient(lum)
    crisp = smoothstep(0.055, 0.09, A.blur(np.hypot(gx_, gy_), 2.0))
    solid = np.clip(A.blur(A.maxf(crisp, 17), 2.0) * 1.3, 0, 1)
    chrome_grey = to_grey(chrome, solid)

    def layer(mask, name):
        m = A.blur(mask.astype(np.float32), 0.8)
        rgba = chrome.copy()
        rgba[..., 3] *= m
        grey = chrome_grey.copy()
        grey[..., 3] *= m
        return Layer(rgba, name, grey)

    letters = [layer(m, n) for m, n in zip(letter_ms, "BADDI3ST")]
    cs = layer(cs_m, "C/S")
    crown_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crown3d", "frames")
    if not os.path.isdir(crown_dir):
        sys.exit("3D crown frames missing: run `node crown3d/render.mjs` first")
    crown = Crown3D(crown_dir, s)
    orn_rgba = chrome.copy()
    orn_rgba[..., 3] *= A.blur(orn_m.astype(np.float32), 0.8)
    orn_grey = to_grey(orn_rgba, solid)

    csx, csy = CS_CENTER[0] * s, CS_CENTER[1] * s
    dist = np.hypot(xx - csx, yy - csy)
    edge_noise = A.tile_noise(H, W, 70 * s, rng) * 90 * s

    # flame animation state (same model as animate_flames.py)
    P = H
    noise = [(A.tile_noise(P, W, sc * s, rng), A.tile_noise(P, W, sc * s, rng), amp * s, k, hw)
             for sc, amp, k, hw in ((90, 16, 2, 1.0), (38, 7, 3, 0.8), (16, 2.5, 5, 0.6))]
    flick = A.tile_noise(P, W, 120 * s, rng)
    loop_T = 6.0
    fy, fx = np.nonzero(F > 0.5)
    pick = rng.choice(len(fx), size=min(80, len(fx)), replace=False)
    embers = [dict(x=float(fx[i]), y=float(fy[i]), phase=rng.uniform(0, 1), rise=rng.uniform(120, 260) * s,
                   r=rng.uniform(1.0, 2.6) * s, sway=rng.uniform(4, 14) * s, cycles=int(rng.integers(1, 3)))
              for i in pick]
    pink = np.array([1.0, 0.45, 0.85], np.float32)

    # impacts: (time, centre, shake px, ring scale, sparks)
    impacts = [(t, l.center, 9 * s, 1.0, 14) for t, l in zip(T_LETTERS, letters)]
    impacts.append((T_CS, cs.center, 24 * s, 2.6, 40))
    impacts.append((T_CROWN_LAND, crown.center + np.array([0, 60 * s]), 7 * s, 1.4, 18))
    sparks = []
    for t0, c, _, sc, n in impacts:
        for _ in range(n):
            ang = rng.uniform(0, TAU)
            sp = rng.uniform(250, 900) * s * (0.7 + 0.3 * sc)
            sparks.append(dict(t0=t0, x=c[0], y=c[1], vx=np.cos(ang) * sp, vy=np.sin(ang) * sp - 150 * s,
                               life=rng.uniform(0.25, 0.6), r=rng.uniform(1.2, 2.8) * s))
    shake_phase = rng.uniform(0, TAU, (len(impacts), 2))

    def crown_angle(t):
        if t < T_CROWN_LAND:
            p = ease_out((t - T_CROWN_DROP) / (T_CROWN_LAND - T_CROWN_DROP))
            return (1 - p) * 3 * TAU  # three turns, slowing down onto the front face
        if t < SPIN_START:
            return 0.0
        k, ph = divmod(t - SPIN_START, SPIN_PERIOD)
        return ease_inout(ph / SPIN_TURN) * TAU

    def overlay_fx(t):
        """Shockwave rings + sparks + embers as an RGBA float overlay (additive look)."""
        glow = np.zeros((H, W), np.float32)
        ring = np.zeros((H, W), np.float32)
        for t0, c, _, sc, _ in impacts:
            dt = t - t0
            if 0 <= dt < 0.45:
                R = (40 + 900 * ease_out(dt / 0.45) * 0.55 * sc) * s
                w = (6 + 10 * sc) * s
                ring += (1 - dt / 0.45) ** 2 * np.exp(-((np.hypot(xx - c[0], yy - c[1]) - R) / w) ** 2) * 0.9
        for p in sparks:
            dt = t - p["t0"]
            if 0 <= dt < p["life"]:
                x = p["x"] + p["vx"] * dt
                y = p["y"] + p["vy"] * dt + 0.5 * 900 * s * dt * dt
                a = (1 - dt / p["life"]) ** 1.5
                _dot(glow, x, y, p["r"], a * 1.4)
        if t >= T_FIRE:
            reveal = ease_out((t - T_FIRE) / FIRE_SPREAD)
            for e in embers:
                tl = (t - T_FIRE) / loop_T
                p = (tl * e["cycles"] + e["phase"]) % 1.0
                ex = e["x"] + np.sin(TAU * (p * 2 + e["phase"])) * e["sway"]
                ey = e["y"] - p * e["rise"]
                if np.hypot(ex - csx, ey - csy) > reveal * 1300 * s:
                    continue
                _dot(glow, ex, ey, e["r"], np.sin(np.pi * p) ** 1.5)
        return glow, ring

    def pink_field(t):
        """Where the pink (and the fire) has reached: (mask 0..1, hot front) full-frame, or scalars."""
        if t < T_FIRE:
            return 0
        if t > T_FIRE + FIRE_SPREAD + 0.35:
            return 1
        R = ease_out((t - T_FIRE) / FIRE_SPREAD) * 1350 * s
        d = dist + edge_noise
        return (np.clip((R - d) / (140 * s), 0, 1), np.exp(-((d - R) / (70 * s)) ** 2))

    def flames(t):
        tl = ((t - T_FIRE) % loop_T) / loop_T
        dx = np.zeros((H, W), np.float32)
        dy = np.zeros((H, W), np.float32)
        for nx, ny, amp, k, hw in noise:
            rows = (np.arange(H) + int(round(tl * k * P))) % P
            dx += nx[rows] * amp * hw
            dy += ny[rows] * amp
        dy += 6 * s
        warped = A.sample(plate, xx + dx * M, yy + dy * M)
        fl = flick[(np.arange(H) + int(round(tl * P))) % P]
        warped *= (1 + 0.28 * fl * M + 0.06 * np.sin(TAU * tl * 4) * M)[..., None]
        bg = im * (1 - M[..., None]) + warped * M[..., None]
        # ignition: spread out from C/S with a ragged, hot front
        R = ease_out((t - T_FIRE) / FIRE_SPREAD) * 1350 * s
        d = dist + edge_noise
        rev = np.clip((R - d) / (140 * s), 0, 1)
        front = np.exp(-((d - R) / (70 * s)) ** 2) * (t - T_FIRE < FIRE_SPREAD + 0.3)
        rgba = key_rgba(bg * (1 + 0.9 * front)[..., None])
        rgba[..., 3] *= (1 - L) * rev
        return rgba

    def frame(t):
        m = int(40 * s)
        canvas = Image.new("RGBA", (W + 2 * m, H + 2 * m), (0, 0, 0, 0))
        off = np.array([m, m], float)
        if t >= T_FIRE:
            fl = flames(t)
            paste(canvas, Image.fromarray((fl * 255 + 0.5).astype(np.uint8), "RGBA"), off)
        if t >= T_ORN:
            R = ease_out((t - T_ORN) / 0.4) * 1400 * s
            pf = pink_field(t)
            if np.isscalar(pf):
                o = (orn_rgba if pf else orn_grey).copy()
            else:
                o = orn_grey * (1 - pf[0][..., None]) + orn_rgba * pf[0][..., None]
                o[..., :3] = o[..., :3] + (1 - o[..., :3]) * pf[1][..., None] * 0.8
            rv = np.clip((R - dist) / (60 * s), 0, 1)
            edge = np.exp(-((dist - R) / (40 * s)) ** 2) * (t - T_ORN < 0.6)
            o[..., :3] = o[..., :3] + (1 - o[..., :3]) * edge[..., None] * 0.9
            o[..., 3] *= rv
            paste(canvas, Image.fromarray((np.clip(o, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA"), off)
        # crown
        if t >= T_CROWN_DROP:
            th = crown_angle(t)
            drop = 1 - ease_out((t - T_CROWN_DROP) / (T_CROWN_LAND - T_CROWN_DROP))
            dt = t - T_CROWN_LAND
            bounce = -14 * s * np.exp(-dt / 0.12) * np.sin(TAU * dt * 4) if dt > 0 else 0
            im_c, pos = crown.render(th, offset=(0, -drop * 560 * s + bounce),
                                     flash=0.6 * np.exp(-dt / 0.1) if dt > 0 else 0.0,
                                     opacity=min(1, (t - T_CROWN_DROP) / 0.15))
            paste(canvas, im_c, pos + off)
        for lay, t_hit in zip(letters, T_LETTERS):
            st = slam_curve(t, t_hit, FLY, 3.4)
            if st:
                img, pos = lay.render(**st, pink=pink_field(t))
                paste(canvas, img, pos + off)
        st = slam_curve(t, T_CS, FLY_CS, 5.0, squash=0.22)
        if st:
            img, pos = cs.render(**st, pink=pink_field(t))
            paste(canvas, img, pos + off)
        # fx overlay
        glow, ring = overlay_fx(t)
        if glow.any() or ring.any():
            col = np.clip(glow[..., None] * pink + ring[..., None] * np.array([1.0, 0.75, 0.95]), 0, 1)
            a = np.clip(np.maximum(glow, ring), 0, 1)
            fx = np.dstack([np.clip(col / np.maximum(a, 1e-3)[..., None], 0, 1), a])
            paste(canvas, Image.fromarray((fx * 255 + 0.5).astype(np.uint8), "RGBA"), off)
        # camera shake
        dx = dy = 0.0
        for (t0, _, amp, _, _), ph in zip(impacts, shake_phase):
            d = t - t0
            if 0 <= d < 0.5:
                e = amp * np.exp(-d / 0.09)
                dx += e * np.sin(TAU * 31 * d + ph[0])
                dy += e * np.sin(TAU * 27 * d + ph[1])
        return canvas.crop((int(m + dx), int(m + dy), int(m + dx) + W, int(m + dy) + H))

    if args.snap:
        times = [float(v) for v in args.snap.split(",")]
        tiles = []
        for t in times:
            fr = frame(t)
            bgc = Image.new("RGBA", fr.size, (60, 70, 90, 255))
            bgc.alpha_composite(fr)
            tiles.append(bgc.convert("RGB").resize((W // 3, H // 3)))
        cols = 3
        rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W // 3), rows * (H // 3)))
        for i, tile in enumerate(tiles):
            sheet.paste(tile, ((i % cols) * (W // 3), (i // cols) * (H // 3)))
        sheet.save(os.path.join(args.out, "snap.png"))
        print("wrote", os.path.join(args.out, "snap.png"))
        return

    fdir = os.path.join(args.out, "frames")
    os.makedirs(fdir, exist_ok=True)
    n = int(round(DURATION * args.fps))
    for i in range(n):
        frame(i / args.fps).save(os.path.join(fdir, f"f{i:04d}.png"))
        if i % 30 == 0:
            print(f"  frame {i}/{n}", flush=True)
    encode(args.out, fdir, args.fps, audio_path, W, H)


def _dot(buf, x, y, r, a):
    H, W = buf.shape
    x0, x1 = int(max(x - 4 * r, 0)), int(min(x + 4 * r + 1, W))
    y0, y1 = int(max(y - 4 * r, 0)), int(min(y + 4 * r + 1, H))
    if x0 >= x1 or y0 >= y1:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
    buf[y0:y1, x0:x1] += a * np.exp(-((gx - x) ** 2 + (gy - y) ** 2) / (2 * r * r))


# ------------------------------------------------------------------ sound design

def build_audio(path, rng, s):
    SR = S.SR
    P = S.Palette({"sound": {"rootNote": "C#", "scale": "minor", "brightness": 0.6, "character": "warm", "seed": 5}})
    n = int((DURATION + 0.5) * SR)
    out = np.zeros((n, 2))

    def put(st, t):
        i = int(round(t * SR))
        a, b = max(i, 0), min(i + len(st), n)
        if b > a:
            out[a:b] += st[a - i:b - i]

    letter_x = [260, 450, 635, 805, 950, 1075, 1245, 1430]  # for panning (native px)
    degrees = [0, 2, 3, 4, 5, 7, 9, 10]  # rising through C# minor as the word builds
    for i, t in enumerate(T_LETTERS):
        pan = (letter_x[i] - 800) / 800 * 0.8
        w, pk = S.whoosh(P, rng, 0.3, 0.85, 900, 6000, (pan * 0.3, pan), tone=False)
        put(w[: int(pk * SR)] * 0.2, t - pk - 0.025)  # air rush that stops just before the hit
        put(slam(P, rng, degrees[i], pan, size=1.0), t)
    # C/S: short riser into a big slam + sub drop
    r, rs = S.riser(P, rng, 0.6)
    put(r * 0.5, T_CS - rs)
    put(slam(P, rng, 0, 0.0, size=2.2), T_CS)
    hit, _ = S.impact(P, rng, 1.8, hard=True)
    put(hit * 0.9, T_CS)
    sub, _ = S.sub_drop(P, rng, 1.6)
    put(sub * 0.6, T_CS)
    # ornaments unsheathe: metallic shing sweeping outwards
    put(shing(P, rng), T_ORN + 0.03)
    # ignition + fire bed from C/S
    w, pk = S.whoosh(P, rng, 1.1, 0.35, 150, 3500, (0, 0), tone=True)
    put(w * 0.9, T_FIRE - pk + 0.1)
    import flame_sound as FS
    bed_len = DURATION - T_FIRE + 0.5
    bed = FS.roar(rng, bed_len) * 0.8 + FS.hiss(rng, bed_len) + FS.crackles(rng, bed_len) * 0.5
    env = np.clip(np.arange(len(bed)) / (0.6 * SR), 0, 1)[:, None]
    put(bed * env * 0.32, T_FIRE)
    # crown: falling whirr while spinning, landing chime, then a soft whirr per turn
    put(whirr(rng, T_CROWN_LAND - T_CROWN_DROP, rate_from=14, rate_to=3) * 0.5, T_CROWN_DROP)
    ch, _ = S.chime(P, rng, 2.0)
    put(ch * 0.7, T_CROWN_LAND)
    put(S.impact(P, rng, 1.0, hard=False)[0] * 0.5, T_CROWN_LAND)
    t = SPIN_START
    while t < DURATION:
        put(whirr(rng, SPIN_TURN, 2.5, 2.5) * 0.25, t)
        tk, _ = S.tink(P, rng) if hasattr(S, "tink") else (S.chime(P, rng, 0.6)[0], 0)
        put(tk * 0.35, t + SPIN_TURN)
        t += SPIN_PERIOD
    out[-int(0.5 * SR):] *= np.linspace(1, 0, int(0.5 * SR))[:, None]
    out = S.normalize(out, -11, -1.0)
    S.write_wav(path, out[: int(DURATION * SR)])
    print(f"audio: {path}  {S.max_momentary_lufs(out):.1f} LUFS-M max")


def slam(P, rng, degree, pan, size=1.0):
    """Chrome object hitting a wall: low thump + crack + short metallic ring tuned to the scale."""
    SR = S.SR
    d = 0.9 * size ** 0.5
    t = np.arange(int(d * SR)) / SR
    thump = np.sin(TAU * np.cumsum(55 + 140 * np.exp(-t / 0.03)) / SR) * np.exp(-t / (0.07 * size))
    crack = S.highpass(rng.standard_normal(len(t)), 1200) * np.exp(-t / 0.01)
    f0 = P.note(degree, 5)
    ring = sum(a * np.sin(TAU * f0 * r * t + rng.uniform(0, 6)) * np.exp(-t / dd)
               for r, a, dd in ((1, 0.5, 0.12 * size), (2.76, 0.3, 0.06 * size), (5.4, 0.15, 0.03)))
    x = S.saturate(thump * 1.2 + crack * 0.8 + ring * 0.35, 0.3)
    st = S.stereo(x, pan)
    return S.reverb(st, rng, 0.25 + 0.6 * (size - 1), 0.06 + 0.1 * (size - 1), damp=6000)


def shing(P, rng):
    """Blade 'shing': bright metallic partials with a fast upward sweep, panned outwards."""
    SR = S.SR
    d = 1.0
    t = np.arange(int(d * SR)) / SR
    sweep = 1 + 0.08 * (1 - np.exp(-t / 0.05))
    x = sum(a * np.sin(TAU * np.cumsum(f * sweep) / SR) * np.exp(-t / dd)
            for f, a, dd in ((2400, 0.5, 0.35), (3870, 0.35, 0.2), (5230, 0.25, 0.12), (7100, 0.15, 0.06)))
    x += S.highpass(rng.standard_normal(len(t)), 4000) * np.exp(-t / 0.04) * 0.3
    return S.reverb(S.widen(rng, x, 0.9) * 0.6, rng, 1.2, 0.25, damp=9000)


def whirr(rng, dur, rate_from, rate_to):
    """Spinning object: band-passed noise amplitude-modulated at the rotation rate."""
    SR = S.SR
    t = np.arange(int(dur * SR)) / SR
    rate = np.geomspace(rate_from, rate_to, len(t))
    am = 0.5 + 0.5 * np.sin(TAU * np.cumsum(rate * 2) / SR) ** 2
    x = S.stft_shape(rng.standard_normal(len(t)), S.bandpass_gain(1400, 1.0)) * am
    env = np.minimum(1, t / 0.1) * np.minimum(1, (dur - t) / 0.2)
    return S.widen(rng, x * env, 0.6)


def encode(out, fdir, fps, audio, W, H):
    frames = ["-framerate", str(fps), "-i", os.path.join(fdir, "f%04d.png")]
    base = os.path.join(out, "baddi3st_reveal")

    def run(args):
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)

    run([*frames, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0",
         "-crf", "24", "-row-mt", "1", "-auto-alt-ref", "0", "-c:a", "libopus", "-b:a", "192k", "-shortest", base + ".webm"])
    run([*frames, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "prores_ks", "-profile:v", "4444",
         "-pix_fmt", "yuva444p10le", "-vendor", "apl0", "-c:a", "pcm_s24le", "-shortest", base + ".mov"])
    for suffix, extra in (("_preview_black.mp4", ""), ("_preview_checker.mp4",
                          "geq=lum='if(eq(mod(floor(X/40)+floor(Y/40),2),0),110,80)':cb=128:cr=128,")):
        run(["-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={fps}", *frames, "-i", audio, "-filter_complex",
             f"[0:v]{extra}format=rgba[bg];[1:v]format=rgba[fg];[bg][fg]overlay=shortest=1,format=yuv420p[v]",
             "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-c:a", "aac",
             "-b:a", "256k", "-movflags", "+faststart", "-shortest", base + suffix])
    print("wrote", base + ".webm/.mov + previews")


if __name__ == "__main__":
    main()
