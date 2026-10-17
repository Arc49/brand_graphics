Templates.end_card = {
  name: "End card / outro",
  category: "cta",
  description: "Closing screen. Landscape leaves exact slots for YouTube end-screen elements; vertical shows a follow prompt.",
  usage: "Last 5–20s of long-form (YouTube end screens need ≥5s). In Shorts use 1.5–3s or skip — Shorts loop.",
  defaults: { heading: null, sub: null, hold: 8, placeholders: true },
  duration: (p) => 1.4 + p.hold,
  anchor: () => ({ t: 0, event: "last spoken line ends" }),
  cues: () => [{ at: 0.3, sfx: "whoosh_long_01", gain: -3 }, { at: 0.95, sfx: "chime", gain: -2 }],
  build(root, p, k, f) {
    const u = f.u;
    const bg = k.el("div", "abs", root);
    Object.assign(bg.style, { inset: 0, background: "var(--bg)" });
    const glow = k.el("div", "abs", root);
    Object.assign(glow.style, { width: 1400 * u + "px", height: 1400 * u + "px", borderRadius: "50%",
      background: "radial-gradient(closest-side, color-mix(in srgb, var(--accent) 22%, transparent), transparent)" });

    const head = k.el("div", "display abs", root);
    head.textContent = p.heading || (f.vertical ? "Follow for more" : "Watch next");
    const sub = k.el("div", "body abs", root);
    sub.textContent = p.sub || k.brand.handle;
    const mark = k.el("div", "abs logo", root, k.logoSVG);
    mark.style.color = "var(--accent)";

    const slots = [];
    if (f.vertical) {
      Object.assign(mark.style, { width: 220 * u + "px", height: 220 * u + "px", left: "50%", top: 0.36 * f.height + "px", marginLeft: -110 * u + "px" });
      Object.assign(head.style, { left: 0, right: 0, textAlign: "center", top: 0.36 * f.height + 280 * u + "px", fontSize: 96 * u + "px" });
      Object.assign(sub.style, { left: 0, right: 0, textAlign: "center", top: 0.36 * f.height + 400 * u + "px", fontSize: 44 * u + "px", color: "var(--textMuted)" });
    } else {
      // YouTube end-screen layout: two 16:9 video slots + a round subscribe slot (logo) — leave them clean
      Object.assign(head.style, { left: f.safeX + "px", top: f.safeY + 20 * u + "px", fontSize: 84 * u + "px" });
      Object.assign(sub.style, { left: f.safeX + "px", bottom: f.safeY + "px", fontSize: 38 * u + "px", color: "var(--textMuted)" });
      const W = 0.32 * f.width, H = W * 9 / 16, top = 0.36 * f.height;
      for (const x of [0.12, 0.56]) {
        const s = k.el("div", "abs", root);
        Object.assign(s.style, { left: x * f.width + "px", top: top + "px", width: W + "px", height: H + "px",
          borderRadius: "var(--radius)", border: p.placeholders ? `${3 * u}px dashed color-mix(in srgb, var(--text) 30%, transparent)` : "none",
          background: "color-mix(in srgb, var(--surface) 70%, transparent)" });
        slots.push(s);
      }
      const d = 230 * u;
      Object.assign(mark.style, { width: d + "px", height: d + "px", left: f.width / 2 - d / 2 + "px", top: top + H + 70 * u + "px" });
    }

    return (t) => {
      const bIn = k.p(t, 0, k.D.long, "move");
      bg.style.clipPath = `circle(${bIn * 75}% at 50% 50%)`;
      const drift = t * 0.25;
      glow.style.left = f.width / 2 - 700 * u + Math.sin(drift) * 160 * u + "px";
      glow.style.top = f.height / 2 - 700 * u + Math.cos(drift * 0.8) * 120 * u + "px";
      glow.style.opacity = String(bIn);
      const hIn = k.p(t, 0.45, k.D.medium);
      head.style.transform = `translateY(${(1 - hIn) * 40 * u}px)`; head.style.opacity = String(hIn);
      const sIn = k.p(t, 0.6, k.D.medium);
      sub.style.transform = `translateY(${(1 - sIn) * 30 * u}px)`; sub.style.opacity = String(sIn);
      slots.forEach((s, i) => {
        const q = k.spring(t, 0.55 + i * 0.1, { stiffness: 180, damping: 22, mass: 1 });
        s.style.transform = `scale(${0.85 + 0.15 * q})`; s.style.opacity = String(Math.min(1, q));
      });
      const m = k.spring(t, 0.95, { stiffness: 220, damping: 15, mass: 1 });
      mark.style.transform = `scale(${t < 0.95 ? 0 : m}) rotate(${(1 - Math.min(m, 1)) * -30}deg)`;
    };
  },
};
