Templates.list_reveal = {
  name: "List / checklist reveal",
  category: "data",
  description: "Heading plus items that tick in one at a time — steps, tips, agenda, takeaways.",
  usage: "When the speaker enumerates points. Time each item's tick to when it is spoken (set `times`), or use the even `gap`. 3–5 items.",
  defaults: { heading: "3 things to fix today", items: ["Consistent motion", "Signature sound", "Clear structure"], gap: 0.7, times: null, hold: 2.0, panel: true },
  anchor: (p) => ({ t: p.times ? p.times[0] : 0.7, event: "first item is spoken" }),
  duration(p) {
    const last = p.times ? p.times[p.times.length - 1] : 0.7 + (p.items.length - 1) * p.gap;
    return last + p.hold + 0.6;
  },
  cues(p) {
    const at = (i) => (p.times ? p.times[i] : 0.7 + i * p.gap);
    const c = [{ at: 0.05, sfx: "whoosh_short_03", gain: -5 }];
    p.items.forEach((_, i) => { c.push({ at: at(i), sfx: "pop_0" + ((i % 3) + 1), gain: -1 }); c.push({ at: at(i) + 0.12, sfx: "tick_02", gain: -6 }); });
    c.push({ at: this.duration(p) - 0.5, sfx: "swish_01", gain: -6 });
    return c;
  },
  build(root, p, k, f) {
    const u = f.u;
    const at = (i) => (p.times ? p.times[i] : 0.7 + i * p.gap);
    const outAt = Templates.list_reveal.duration(p) - 0.55;
    const box = k.el("div", "abs", root);
    Object.assign(box.style, { left: f.safeX + "px", top: "50%", padding: `${44 * u}px ${54 * u}px`,
      maxWidth: (f.vertical ? f.width - 2 * f.safeX : 900 * u) + "px",
      background: p.panel ? "color-mix(in srgb, var(--bg) 82%, transparent)" : "none", borderRadius: "var(--radius)",
      boxShadow: p.panel ? `0 ${16 * u}px ${50 * u}px rgba(0,0,0,.35)` : "none" });
    const head = k.el("div", "display", box);
    head.textContent = p.heading;
    Object.assign(head.style, { fontSize: 64 * u + "px", marginBottom: 30 * u + "px" });
    const rows = p.items.map((txt) => {
      const row = k.el("div", null, box);
      Object.assign(row.style, { display: "flex", alignItems: "center", gap: 26 * u + "px", margin: `${18 * u}px 0` });
      const chk = k.el("div", null, row);
      const s = 52 * u;
      chk.innerHTML = `<svg width="${s}" height="${s}" viewBox="0 0 52 52"><rect x="3" y="3" width="46" height="46" rx="12" fill="none" stroke="var(--textMuted)" stroke-width="4"/>
        <rect class="fill" x="3" y="3" width="46" height="46" rx="12" fill="var(--action)"/>
        <path class="tick" d="M14 27 l8 8 l16 -18" fill="none" stroke="var(--onAction)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="40"/></svg>`;
      const label = k.el("div", "body", row);
      label.textContent = txt;
      Object.assign(label.style, { fontSize: 46 * u + "px" });
      return { row, fill: chk.querySelector(".fill"), tick: chk.querySelector(".tick"), label };
    });
    return (t) => {
      const bIn = k.p(t, 0, k.D.medium), ex = k.p(t, outAt, k.D.short + 0.1, "exit");
      box.style.transform = `translate(${(1 - bIn) * -60 * u - ex * 60 * u}px, -50%)`;
      box.style.opacity = String(bIn * (1 - ex));
      rows.forEach((r, i) => {
        const a = at(i);
        const show = k.p(t, a - 0.25, k.D.short);
        r.row.style.opacity = String(0.25 + 0.75 * show);
        r.row.style.transform = `translateX(${(1 - show) * 30 * u}px)`;
        const pop = t < a ? 0 : k.spring(t, a, { stiffness: 300, damping: 16, mass: 1 });
        r.fill.setAttribute("transform", `translate(26 26) scale(${pop}) translate(-26 -26)`);
        r.tick.style.strokeDashoffset = String(40 * (1 - k.p(t, a + 0.06, 0.25)));
        r.label.style.color = t >= a ? "var(--text)" : "var(--textMuted)";
      });
    };
  },
};
