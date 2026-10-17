Templates.cta_subscribe = {
  name: "Subscribe / follow CTA",
  category: "cta",
  description: "Button slides in, a cursor clicks it, it flips to the confirmed state and the bell rings.",
  usage: "Once in long-form, right after the first payoff (~30–90s in), not at the start. In Shorts use label 'Follow' near the end.",
  defaults: { label: "Subscribe", doneLabel: "Subscribed", hold: null },
  duration: (p, k) => 1.25 + (p.hold ?? k.brand.motion.hold.cta) + 0.5,
  anchor: () => ({ t: 1.25, event: "the click lands as the speaker says 'subscribe'/'follow'" }),
  cues(p, k) {
    const out = 1.25 + (p.hold ?? k.brand.motion.hold.cta);
    return [
      { at: 0.15, sfx: "whoosh_short_01", gain: -4 },
      { at: 1.25, sfx: "click_02", gain: 2 },
      { at: 1.3, sfx: "blip_up", gain: 0 },
      { at: 1.55, sfx: "shimmer", gain: -10 },
      { at: out + 0.05, sfx: "swish_01", gain: -6 },
    ];
  },
  build(root, p, k, f) {
    const u = f.u;
    const outAt = 1.25 + (p.hold ?? k.brand.motion.hold.cta);
    const clickAt = 1.25;
    const wrap = k.el("div", "abs", root);
    Object.assign(wrap.style, { left: "50%", top: (f.vertical ? 0.72 : 0.8) * f.height + "px", transform: "translate(-50%,-50%)" });
    const btn = k.el("div", null, wrap);
    Object.assign(btn.style, { display: "flex", alignItems: "center", gap: 24 * u + "px", padding: `${26 * u}px ${48 * u}px ${26 * u}px ${36 * u}px`,
      borderRadius: 999 + "px", whiteSpace: "nowrap", boxShadow: `0 ${14 * u}px ${40 * u}px rgba(0,0,0,.4)` });
    const bell = k.el("div", null, btn);
    bell.innerHTML = `<svg viewBox="0 0 24 24" width="${64 * u}" height="${64 * u}"><path fill="currentColor" d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22Zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1Z"/></svg>`;
    bell.style.transformOrigin = "50% 10%";
    const label = k.el("div", "display", btn);
    label.style.fontSize = 60 * u + "px";
    const cursor = k.el("div", "abs", wrap);
    cursor.innerHTML = `<svg viewBox="0 0 24 24" width="${64 * u}" height="${64 * u}"><path d="M4 2l15 11-6.5 1.2L16 21l-3 1.4-3.4-6.8L4 20Z" fill="#fff" stroke="#000" stroke-width="1.3" stroke-linejoin="round"/></svg>`;
    Object.assign(cursor.style, { left: "62%", top: "45%", filter: `drop-shadow(0 ${4 * u}px ${8 * u}px rgba(0,0,0,.4))` });
    const ripple = k.el("div", "abs", wrap);
    Object.assign(ripple.style, { left: "64%", top: "50%", width: 120 * u + "px", height: 120 * u + "px", marginLeft: -60 * u + "px",
      marginTop: -60 * u + "px", borderRadius: "50%", border: `${4 * u}px solid var(--text)`, opacity: 0 });

    return (t) => {
      const sIn = k.spring(t, 0.05, { stiffness: 210, damping: 19, mass: 1 });
      const ex = k.p(t, outAt, k.D.short + 0.1, "exit");
      wrap.style.transform = `translate(-50%, calc(-50% + ${(1 - sIn) * 160 * u + ex * 120 * u}px))`;
      wrap.style.opacity = String(Math.min(1, t / 0.12) * (1 - ex));
      const done = t >= clickAt;
      btn.style.background = done ? "var(--surface)" : "var(--action)";
      btn.style.color = done ? "var(--textMuted)" : "var(--onAction)";
      label.textContent = done ? p.doneLabel + " ✓" : p.label;
      const press = t > clickAt - 0.08 && t < clickAt + 0.14 ? 0.93 : 1;
      btn.style.transform = `scale(${press})`;
      // cursor glides in, clicks, glides away
      const cIn = k.p(t, 0.55, 0.6, "move"), cOut = k.p(t, clickAt + 0.45, 0.5, "exit");
      cursor.style.transform = `translate(${(1 - cIn) * 260 * u + cOut * 200 * u}px, ${(1 - cIn) * 160 * u + cOut * 140 * u}px) scale(${press === 1 ? 1 : 0.88})`;
      cursor.style.opacity = String(Math.min(cIn * 2, 1) * (1 - cOut));
      const r = k.clamp((t - clickAt) / 0.45);
      ripple.style.opacity = t >= clickAt ? String((1 - r) * 0.7) : "0";
      ripple.style.transform = `scale(${0.4 + r * 0.9})`;
      const ring = k.clamp((t - clickAt - 0.05) / 0.9);
      bell.style.transform = `rotate(${t > clickAt ? Math.sin(ring * 26) * 22 * (1 - ring) : 0}deg)`;
    };
  },
};
