Templates.transition = {
  name: "Transition wipe",
  category: "transition",
  description: "Full-frame branded wipe. The frame is fully covered at the cut point (half-way), so the cut hides underneath.",
  usage: "Place so its midpoint sits exactly on the cut between scenes/topics. Use sparingly: max one per ~45s in long-form, ~10s in Shorts. Never on a jump cut inside a sentence.",
  formatsNote: "styles: bands | iris | slide",
  defaults: { style: "bands", dur: 1.0 },
  duration: (p) => p.dur,
  anchor: (p) => ({ t: p.dur / 2, event: "the cut between the two shots" }),
  cues(p) {
    const mid = p.dur / 2;
    if (p.style === "iris") return [{ at: mid, sfx: "reverse_swell", gain: -3 }, { at: mid, sfx: "impact_soft", gain: -8 }];
    return [{ at: mid, sfx: p.style === "slide" ? "whoosh_long_02" : "whoosh_long_01", gain: 0 }];
  },
  build(root, p, k, f) {
    const mid = p.dur / 2;
    const half = mid * 0.85; // time to cover; same to uncover

    if (p.style === "iris") {
      const ring = k.el("div", "abs", root); // accent ring leads…
      const disc = k.el("div", "abs", root); // …and the bg disc fills in on top of it
      const diag = Math.hypot(f.width, f.height);
      for (const d of [disc, ring]) Object.assign(d.style, { left: "50%", top: "50%", width: diag + "px", height: diag + "px",
        marginLeft: -diag / 2 + "px", marginTop: -diag / 2 + "px", borderRadius: "50%" });
      disc.style.background = "var(--bg)";
      ring.style.background = "var(--accent)";
      return (t) => {
        const a = k.p(t, mid - half, half, "move"), b = k.p(t, mid - half + 0.08, half - 0.08, "move");
        const outA = k.p(t, mid, half, "move"), outB = k.p(t, mid + 0.06, half - 0.06, "move");
        ring.style.transform = `scale(${t < mid ? a : 1})`;
        ring.style.opacity = t < mid ? 1 : String(1 - outB);
        disc.style.transform = `scale(${t < mid ? b : 1 - outA})`;
        ring.style.clipPath = t < mid ? "none" : `circle(${(1 - outB) * 50}% at 50% 50%)`;
      };
    }

    const colors = ["var(--accent2)", "var(--accent)", "var(--bg)"];
    const angle = p.style === "slide" ? 0 : -12;
    const bands = colors.map((c, i) => {
      const b = k.el("div", "abs", root);
      const w = f.width * 1.6;
      Object.assign(b.style, { top: -f.height * 0.5 + "px", height: f.height * 2 + "px", width: w + "px", left: 0,
        background: c, transformOrigin: "50% 50%" });
      return { b, w, delay: i * 0.08, delayOut: (colors.length - 1 - i) * 0.08 };
    });
    return (t) => {
      for (const { b, w, delay, delayOut } of bands) {
        // colour bands lead on the way in and trail on the way out; the bg band covers the cut
        const inP = k.p(t, delay, half - delay, "move");
        const outP = k.p(t, mid + delayOut, half - delayOut, "move");
        // travels from fully left (-w) to covering (−(w−W)/2) to fully right (+W)
        const cover = -(w - f.width) / 2;
        const x = t < mid ? k.lerp(-w - f.width * 0.2, cover, inP) : k.lerp(cover, f.width * 1.2, outP);
        b.style.transform = `translateX(${x}px) rotate(${angle}deg)`;
      }
    };
  },
};
