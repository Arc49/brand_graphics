Templates.callout = {
  name: "Callout / keyword pop",
  category: "emphasis",
  description: "Small pill that pops in to highlight a keyword, tip or number next to the speaker.",
  usage: "On the exact word being emphasised. Max one every ~8s; keep text to 1–4 words. Place opposite the speaker's face.",
  defaults: { text: "Key insight", icon: "★", x: 0.68, y: 0.3, style: "accent", hold: null },
  duration: (p, k) => 0.5 + (p.hold ?? k.brand.motion.hold.callout) + 0.35,
  anchor: () => ({ t: 0.02, event: "the emphasised word is spoken" }),
  cues(p, k) {
    const out = 0.5 + (p.hold ?? k.brand.motion.hold.callout);
    return [{ at: 0.02, sfx: "pop_01", gain: 0 }, { at: out, sfx: "blip_down", gain: -8 }];
  },
  build(root, p, k, f) {
    const u = f.u;
    const outAt = 0.5 + (p.hold ?? k.brand.motion.hold.callout);
    const accent = p.style !== "surface";
    const anchor = k.el("div", "abs", root);
    Object.assign(anchor.style, { left: p.x * f.width + "px", top: p.y * f.height + "px" });
    const pill = k.el("div", "abs", anchor);
    Object.assign(pill.style, {
      transform: "translate(-50%,-50%)", display: "flex", alignItems: "center", gap: 18 * u + "px",
      padding: `${18 * u}px ${34 * u}px`, borderRadius: 999 + "px", whiteSpace: "nowrap",
      background: accent ? "var(--accent)" : "var(--surface)", color: accent ? "var(--onAccent)" : "var(--text)",
      boxShadow: `0 ${12 * u}px ${36 * u}px rgba(0,0,0,.35)`,
    });
    let icon = null;
    if (p.icon) {
      icon = k.el("div", "display", pill);
      icon.textContent = p.icon;
      Object.assign(icon.style, { fontSize: 44 * u + "px", lineHeight: 1 });
    }
    const label = k.el("div", "display", pill);
    label.textContent = p.text;
    label.style.fontSize = 52 * u + "px";

    return (t) => {
      const s = k.spring(t, 0) * (1 - k.p(t, outAt, k.D.short, "exit"));
      pill.style.transform = `translate(-50%,-50%) scale(${Math.max(0, s)}) rotate(${(1 - Math.min(1, s)) * -8}deg)`;
      pill.style.opacity = String(Math.min(1, s * 3));
      if (icon) icon.style.transform = `rotate(${Math.sin(Math.min(t, 1.2) * 14) * (1 - Math.min(1, t / 1.2)) * 18}deg)`;
    };
  },
};
