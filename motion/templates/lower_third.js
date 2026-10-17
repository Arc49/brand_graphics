Templates.lower_third = {
  name: "Lower third",
  category: "identity",
  description: "Name + role tag that introduces a speaker or guest.",
  usage: "First appearance of each speaker, within their first 3s on screen. Never over another graphic. Max once per speaker per video.",
  defaults: { name: "Alex Rivera", title: "Founder · Your Brand", hold: null },
  duration: (p, k) => 0.9 + (p.hold ?? k.brand.motion.hold.lowerThird) + 0.5,
  anchor: () => ({ t: 0, event: "speaker first appears / starts talking" }),
  cues(p, k) {
    const out = 0.9 + (p.hold ?? k.brand.motion.hold.lowerThird);
    return [
      { at: 0.12, sfx: "swish_01", gain: 0 },
      { at: 0.32, sfx: "click_01", gain: -4 },
      { at: out + 0.05, sfx: "swish_01", gain: -5 },
    ];
  },
  build(root, p, k, f) {
    const u = f.u;
    const outAt = 0.9 + (p.hold ?? k.brand.motion.hold.lowerThird);
    const wrap = k.el("div", "abs", root);
    wrap.style.left = f.safeX + "px";
    wrap.style.top = (f.vertical ? f.height * 0.64 : f.height - f.safeY - 170 * u) + "px";
    Object.assign(wrap.style, { display: "flex", alignItems: "stretch", gap: 14 * u + "px",
      filter: `drop-shadow(0 ${10 * u}px ${30 * u}px rgba(0,0,0,.35))` });

    const bar = k.el("div", null, wrap);
    Object.assign(bar.style, { width: 12 * u + "px", flex: "none",
      background: "var(--accent)", borderRadius: 6 * u + "px", transformOrigin: "50% 100%" });

    const panel = k.el("div", null, wrap);
    Object.assign(panel.style, { padding: `${22 * u}px ${40 * u}px ${24 * u}px`,
      background: "var(--surface)", borderRadius: `var(--radius)`, whiteSpace: "nowrap" });

    const nameMask = k.el("div", "mask", panel);
    const name = k.el("div", "display", nameMask, "");
    name.textContent = p.name;
    Object.assign(name.style, { fontSize: 66 * u + "px", color: "var(--text)", paddingBottom: 4 * u + "px" });
    k.el("br", null, panel);
    const titleMask = k.el("div", "mask", panel);
    const title = k.el("div", "body", titleMask);
    title.textContent = p.title;
    Object.assign(title.style, { fontSize: 34 * u + "px", color: "var(--textMuted)", marginTop: 6 * u + "px" });

    return (t) => {
      const D = k.D;
      const barIn = k.p(t, 0, D.short);
      const panelIn = k.p(t, 0.1, D.medium);
      const nameIn = k.p(t, 0.22, D.medium);
      const titleIn = k.p(t, 0.3, D.medium);
      const ex = k.p(t, outAt, D.short + 0.1, "exit");
      const barOut = k.p(t, outAt + 0.15, D.short, "exit");

      bar.style.transform = `scaleY(${barIn * (1 - barOut)})`;
      const right = (1 - panelIn) * 100 + ex * 100;
      panel.style.clipPath = `inset(0 ${Math.min(100, right)}% 0 0 round ${k.brand.shape.radius * u}px)`;
      panel.style.transform = `translateX(${(1 - panelIn) * -30 * u}px)`;
      name.style.transform = `translateY(${(1 - nameIn) * 110}%)`;
      title.style.transform = `translateY(${(1 - titleIn) * 110}%)`;
      name.style.opacity = title.style.opacity = String(1 - ex);
    };
  },
};
