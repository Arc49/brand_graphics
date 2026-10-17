Templates.title_card = {
  name: "Chapter / title card",
  category: "structure",
  description: "Full-screen section card: chapter number + title. Use as a hard topic change.",
  usage: "At each major topic change in long-form (every ~2–4 min). Cut to it on the sentence before the new topic; the card covers the cut.",
  defaults: { label: "Chapter 02", title: "Why most videos feel amateur", background: true, hold: null },
  duration: (p, k) => 1.0 + (p.hold ?? k.brand.motion.hold.titleCard) + 0.6,
  anchor: () => ({ t: 0.35, event: "the cut into the new section (card is fully opaque from here)" }),
  cues(p, k) {
    const out = 1.0 + (p.hold ?? k.brand.motion.hold.titleCard);
    return [
      { at: 0.22, sfx: "whoosh_short_01", gain: 0 },
      { at: 0.62, sfx: "impact_soft", gain: -3 },
      { at: out + 0.3, sfx: "whoosh_short_02", gain: -2 },
    ];
  },
  build(root, p, k, f) {
    const u = f.u;
    const outAt = 1.0 + (p.hold ?? k.brand.motion.hold.titleCard);

    const sheetA = k.el("div", "abs", root);
    const sheetB = k.el("div", "abs", root);
    for (const [s, c] of [[sheetA, "var(--accent)"], [sheetB, "var(--bg)"]])
      Object.assign(s.style, { inset: 0, background: c, display: p.background ? "block" : "none" });
    sheetB.style.background = `radial-gradient(90% 70% at 85% 110%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 60%), var(--bg)`;

    const box = k.el("div", "abs", root);
    Object.assign(box.style, { left: f.safeX + (f.vertical ? 0 : 60 * u) + "px", right: f.safeX + "px",
      top: "50%", transform: "translateY(-50%)" });

    const labelMask = k.el("div", "mask", box);
    const label = k.el("div", "mono", labelMask);
    label.textContent = p.label.toUpperCase();
    Object.assign(label.style, { fontSize: 30 * u + "px", color: "var(--accent)", letterSpacing: "0.18em", marginBottom: 26 * u + "px" });

    const title = k.el("div", "display", box);
    Object.assign(title.style, { fontSize: (f.vertical ? 112 : 128) * u + "px", maxWidth: (f.vertical ? 900 : 1500) * u + "px", color: "var(--text)" });
    const words = k.split(title, p.title, "word").map((w) => {
      const m = document.createElement("span");
      m.className = "mask"; m.style.paddingBottom = "0.08em";
      w.replaceWith(m); m.appendChild(w); return w;
    });

    const line = k.el("div", null, box);
    Object.assign(line.style, { height: 8 * u + "px", width: 220 * u + "px", background: "var(--accent)",
      borderRadius: 4 * u + "px", marginTop: 40 * u + "px", transformOrigin: "0 50%" });

    return (t) => {
      const D = k.D;
      const aIn = k.p(t, 0, D.medium, "move"), bIn = k.p(t, 0.1, D.medium, "move");
      const aOut = k.p(t, outAt + 0.15, D.medium, "move"), bOut = k.p(t, outAt + 0.05, D.medium, "move");
      sheetA.style.clipPath = `inset(${(1 - aIn) * 100}% 0 ${aOut * 100}% 0)`;
      sheetB.style.clipPath = `inset(${(1 - bIn) * 100}% 0 ${bOut * 100}% 0)`;

      const exit = k.p(t, outAt, D.short + 0.1, "exit");
      box.style.opacity = String(1 - exit);
      box.style.transform = `translateY(calc(-50% - ${exit * 60 * u}px))`;
      label.style.transform = `translateY(${(1 - k.p(t, 0.35, D.medium)) * 110}%)`;
      words.forEach((w, i) => {
        const s = k.p(t, 0.42 + i * k.stagger, D.medium + 0.1);
        w.style.transform = `translateY(${(1 - s) * 105}%)`;
      });
      line.style.transform = `scaleX(${k.p(t, 0.6 + words.length * k.stagger, D.long)})`;
    };
  },
};
