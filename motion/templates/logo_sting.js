Templates.logo_sting = {
  name: "Logo sting (intro)",
  category: "identity",
  description: "Brand mark + name reveal locked to the sonic logo. The opening signature of every video.",
  usage: "Right after the cold-open hook (5–20s in) in long-form; skip in Shorts or use the 'compact' variant at the end. Always with sonic_logo.",
  defaults: { name: null, tagline: null, background: true, compact: false },
  duration: (p) => (p.compact ? 2.0 : 3.2),
  anchor: () => ({ t: 0.47, event: "end of the cold-open hook (hard cut)" }),
  cues: () => [{ at: 0.47, sfx: "sonic_logo", gain: 0 }],
  build(root, p, k, f) {
    const u = f.u;
    const hit = 0.47;
    const end = p.compact ? 2.0 : 3.2;
    const bg = k.el("div", "abs", root);
    Object.assign(bg.style, { inset: 0, display: p.background ? "block" : "none",
      background: "radial-gradient(70% 60% at 50% 50%, color-mix(in srgb, var(--accent) 16%, var(--bg)), var(--bg) 70%)" });

    const center = k.el("div", "abs", root);
    Object.assign(center.style, { left: "50%", top: "50%", transform: "translate(-50%,-50%)", display: "flex",
      flexDirection: f.vertical ? "column" : "row", alignItems: "center", gap: 40 * u + "px" });

    const markBox = k.el("div", null, center);
    Object.assign(markBox.style, { position: "relative", width: 200 * u + "px", height: 200 * u + "px" });
    const rings = [0, 1].map(() => {
      const r = k.el("div", "abs", markBox);
      Object.assign(r.style, { inset: 0, borderRadius: "50%", border: `${4 * u}px solid var(--accent)` });
      return r;
    });
    const mark = k.el("div", "abs logo", markBox, k.logoSVG);
    Object.assign(mark.style, { inset: 0, color: "var(--accent)" });

    const textBox = k.el("div", null, center);
    textBox.style.textAlign = f.vertical ? "center" : "left";
    const nameMask = k.el("div", "mask", textBox);
    const name = k.el("div", "display", nameMask);
    const wm = k.brand.wordmark || {};
    Object.assign(name.style, { fontSize: (wm.uppercase ? 92 : 120) * u + "px", color: "var(--text)", paddingBottom: "0.06em",
      whiteSpace: "nowrap", textTransform: wm.uppercase ? "uppercase" : "none", letterSpacing: wm.tracking || "inherit" });
    const chars = k.split(name, p.name || k.brand.name, "char");
    // two-tone wordmark: colour one word with the accent (e.g. VISUAL in green, CRANIO in white)
    if (wm.accentWord != null) {
      let word = 0;
      for (const node of name.childNodes) {
        if (node.nodeType === 3) { word++; continue; }
        if (word === wm.accentWord) node.style.color = "var(--accent)";
      }
    }
    let tag = null;
    if (p.tagline || k.brand.handle) {
      k.el("br", null, textBox);
      const tm = k.el("div", "mask", textBox);
      tag = k.el("div", "body", tm);
      tag.textContent = p.tagline || k.brand.handle;
      Object.assign(tag.style, { fontSize: 36 * u + "px", color: "var(--textMuted)", marginTop: 4 * u + "px" });
    }

    return (t) => {
      // converge: two rings collapse onto the mark, which springs in on the audio hit
      rings.forEach((r, i) => {
        const c = k.p(t, i * 0.08, hit - i * 0.08, "move");
        r.style.transform = `scale(${3.2 - 2.2 * c})`;
        r.style.opacity = String(t < hit ? c * 0.8 : Math.max(0, 0.8 - (t - hit) * 3));
        if (t >= hit) r.style.transform = `scale(${1 + (t - hit) * (1.6 + i)})`;
      });
      const s = t < hit ? 0 : k.spring(t, hit, { stiffness: 240, damping: 16, mass: 1 });
      const ex = k.p(t, end - 0.55, 0.5, "exit");
      mark.style.transform = `scale(${s}) rotate(${(1 - Math.min(s, 1)) * -40}deg)`;
      chars.forEach((c, i) => {
        const q = k.p(t, hit + 0.18 + i * 0.025, k.D.medium);
        c.style.transform = `translateY(${(1 - q) * 105}%)`;
      });
      if (tag) tag.style.transform = `translateY(${(1 - k.p(t, hit + 0.45, k.D.medium)) * 110}%)`;
      center.style.opacity = String(1 - ex);
      center.style.transform = `translate(-50%,-50%) scale(${1 + ex * 0.08})`;
      bg.style.opacity = p.background ? String(1 - k.p(t, end - 0.3, 0.3, "exit")) : "0";
    };
  },
};
