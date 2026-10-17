Templates.punch_text = {
  name: "Punch text (hook)",
  category: "emphasis",
  description: "Big centred words that slam in one by one. Wrap words in *asterisks* to highlight them.",
  usage: "Hooks in the first 2s of Shorts, and big statements in long-form. One per video section; 2–7 words.",
  defaults: { text: "Stop making *boring* videos", wordGap: 0.22, hold: 1.4, scrim: true },
  duration: (p) => 0.3 + p.text.split(/\s+/).length * p.wordGap + p.hold + 0.45,
  anchor: () => ({ t: 0.1, event: "first word of the statement is spoken" }),
  cues(p) {
    const words = p.text.split(/\s+/);
    const c = words.map((w, i) => ({ at: 0.1 + i * p.wordGap, sfx: /^\*.*\*$/.test(w) ? "impact_soft" : `click_0${(i % 3) + 1}`,
      gain: /^\*.*\*$/.test(w) ? -4 : 0 }));
    c.push({ at: 0.3 + words.length * p.wordGap + p.hold + 0.1, sfx: "whoosh_short_03", gain: -4 });
    return c;
  },
  build(root, p, k, f) {
    const u = f.u;
    const words = p.text.split(/\s+/);
    const outAt = 0.3 + words.length * p.wordGap + p.hold;
    const scrim = k.el("div", "abs", root);
    Object.assign(scrim.style, { inset: 0, background: "radial-gradient(80% 60% at 50% 50%, rgba(0,0,0,.55), rgba(0,0,0,.15))",
      display: p.scrim ? "block" : "none" });
    const box = k.el("div", "abs display", root);
    Object.assign(box.style, { left: f.safeX + "px", right: f.safeX + "px", top: "50%", textAlign: "center",
      fontSize: (f.vertical ? 140 : 150) * u + "px", lineHeight: 1.08, transform: "translateY(-50%)", color: "var(--text)" });
    const spans = words.map((w, i) => {
      const hl = /^\*.*\*$/.test(w);
      const s = k.el("span", null, box);
      s.textContent = hl ? w.slice(1, -1) : w;
      Object.assign(s.style, { display: "inline-block", margin: `0 ${18 * u}px`, padding: hl ? `0 ${22 * u}px` : 0,
        borderRadius: 14 * u + "px", textShadow: hl ? "none" : `0 ${6 * u}px ${24 * u}px rgba(0,0,0,.4)` });
      if (hl) { s.style.background = "var(--accent)"; s.style.color = "var(--onAccent)"; }
      return { s, hl, at: 0.1 + i * p.wordGap - 0.06 };
    });
    return (t) => {
      const ex = k.p(t, outAt, k.D.short + 0.1, "exit");
      scrim.style.opacity = String(Math.min(1, t / 0.25) * (1 - ex));
      for (const { s, hl, at } of spans) {
        const sp = k.spring(t, at, { stiffness: 260, damping: hl ? 14 : 22, mass: 1 });
        const scale = t < at ? 0 : 1.5 - 0.5 * sp;
        s.style.opacity = String((t < at ? 0 : Math.min(1, (t - at) / 0.05)) * (1 - ex));
        s.style.transform = `scale(${scale}) translateY(${ex * 80 * u}px) rotate(${hl ? (1 - sp) * -6 : 0}deg)`;
      }
    };
  },
};
