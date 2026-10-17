// Big statement text in the story style: heavy display type, one *highlighted* word,
// optional sub-line with an *action* phrase and a nudging arrow ("Let's fix that. *Tap through* →").
Templates.punch_text = {
  name: "Punch text (hook)",
  category: "emphasis",
  description: "Big statement that builds word by word. *Stars* mark the highlight word; `sub` adds a smaller line with an *action* phrase and arrow.",
  usage: "Hooks in the first 2s of Shorts / story frames, and big statements in long-form. One per section; 3–8 words.",
  defaults: { text: "5 glow-up *myths* keeping you average.", sub: "Let's fix that. *Tap through* →", wordGap: 0.16,
    hold: 1.8, anim: "rise", align: null, background: false, scrim: true },
  _words: (p) => p.text.split(/\s+/).filter(Boolean),
  _subAt: (p) => 0.15 + Templates.punch_text._words(p).length * p.wordGap + 0.15,
  _outAt(p) { return this._subAt(p) + (p.sub ? 0.35 : 0) + p.hold; },
  duration(p) { return this._outAt(p) + 0.45; },
  anchor: () => ({ t: 0.1, event: "first word of the statement is spoken" }),
  cues(p) {
    const words = this._words(p);
    const c = words.map((w, i) => {
      const hl = /^\*.*\*$/.test(w);
      return { at: 0.1 + i * p.wordGap, sfx: hl ? "impact_soft" : `click_0${(i % 3) + 1}`, gain: hl ? -3 : p.anim === "slam" ? 0 : -6 };
    });
    if (p.sub) c.push({ at: this._subAt(p) + 0.05, sfx: "swish_01", gain: -4 }, { at: this._subAt(p) + 0.45, sfx: "blip_up", gain: -8 });
    c.push({ at: this._outAt(p) + 0.1, sfx: "whoosh_short_03", gain: -4 });
    return c;
  },
  build(root, p, k, f) {
    const u = f.u;
    const T = Templates.punch_text;
    const words = T._words(p);
    const outAt = T._outAt(p), subAt = T._subAt(p);
    const align = p.align || (k.brand.text && k.brand.text.align) || "center";
    const colorHL = !k.brand.text || k.brand.text.highlight !== "box";

    const back = k.el("div", "abs", root);
    Object.assign(back.style, { inset: 0 });
    if (p.background) back.style.background = "var(--bg)";
    else if (p.scrim) back.style.background = "radial-gradient(90% 70% at 40% 50%, rgba(0,0,0,.55), rgba(0,0,0,.12))";
    else back.style.display = "none";

    const box = k.el("div", "abs", root);
    Object.assign(box.style, { left: f.safeX + "px", right: f.safeX + "px", top: "50%", textAlign: align, transform: "translateY(-50%)" });
    const big = k.el("div", "display", box);
    Object.assign(big.style, { fontSize: (f.vertical ? 132 : 138) * u + "px", color: "var(--text)",
      maxWidth: (f.vertical ? 960 : 1300) * u + "px", marginLeft: align === "center" ? "auto" : 0, marginRight: align === "center" ? "auto" : 0 });
    const shadow = p.background ? "none" : `0 ${6 * u}px ${28 * u}px rgba(0,0,0,.45)`;
    const spans = words.map((w, i) => {
      const hl = /^\*.*\*$/.test(w);
      if (i) big.appendChild(document.createTextNode(" "));
      const mask = k.el("span", "mask", big);
      mask.style.paddingBottom = "0.1em"; mask.style.marginBottom = "-0.1em";
      const s = k.el("span", null, mask);
      s.textContent = hl ? w.slice(1, -1) : w;
      Object.assign(s.style, { display: "inline-block", textShadow: shadow, transformOrigin: "50% 80%" });
      if (hl && colorHL) s.style.color = "var(--highlight)";
      if (hl && !colorHL) Object.assign(s.style, { background: "var(--highlight)", color: "var(--onAccent)", padding: `0 ${18 * u}px`, borderRadius: 12 * u + "px" });
      if (p.anim === "slam") mask.style.overflow = "visible";
      return { s, hl, at: 0.1 + i * p.wordGap - 0.06 };
    });

    let sub = null, arrow = null;
    if (p.sub) {
      sub = k.el("div", "strong", box);
      Object.assign(sub.style, { fontSize: (f.vertical ? 50 : 48) * u + "px", marginTop: 34 * u + "px", color: "var(--text)",
        display: "flex", alignItems: "center", gap: 18 * u + "px", textShadow: shadow,
        justifyContent: align === "center" ? "center" : "flex-start" });
      const html = p.sub.replace(/→\s*$/, "").trim()
        .replace(/\*(.+?)\*/g, '<span style="color:var(--action)">$1</span>');
      k.el("span", null, sub, html);
      if (/→\s*$/.test(p.sub)) {
        arrow = k.el("span", null, sub);
        arrow.innerHTML = `<svg width="${62 * u}" height="${40 * u}" viewBox="0 0 62 40"><path d="M4 20 H52 M36 6 L54 20 L36 34" fill="none" stroke="var(--action)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        arrow.style.display = "inline-flex";
      }
    }

    return (t) => {
      const ex = k.p(t, outAt, k.D.short + 0.1, "exit");
      back.style.opacity = String(Math.min(1, t / 0.2) * (1 - ex));
      for (const { s, hl, at } of spans) {
        if (p.anim === "slam") {
          const sp = k.spring(t, at, { stiffness: 260, damping: hl ? 14 : 22, mass: 1 });
          s.style.opacity = String((t < at ? 0 : Math.min(1, (t - at) / 0.05)) * (1 - ex));
          s.style.transform = `scale(${t < at ? 0 : 1.5 - 0.5 * sp}) translateY(${ex * 80 * u}px)`;
        } else {
          const r = k.p(t, at, k.D.medium);
          const pop = hl ? 1 + 0.12 * Math.sin(Math.PI * k.clamp((t - at - 0.12) / 0.35)) : 1;
          s.style.transform = `translateY(${(1 - r) * 130 + ex * -130}%) scale(${pop})`;
        }
      }
      if (sub) {
        const r = k.p(t, subAt, k.D.medium);
        sub.style.opacity = String(r * (1 - ex));
        sub.style.transform = `translateY(${(1 - r) * 24 * u}px)`;
        if (arrow) {
          const a = Math.max(0, t - subAt - 0.35);
          arrow.style.transform = `translateX(${(1 - k.p(t, subAt + 0.2, k.D.medium)) * -30 * u + Math.sin(a * 6) ** 2 * 12 * u}px)`;
        }
      }
    };
  },
};
