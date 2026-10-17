Templates.stat_counter = {
  name: "Stat counter",
  category: "data",
  description: "A number that counts up with a progress ring and label — for results, metrics, money.",
  usage: "When stating a number that matters. Let the count finish on the spoken number. One stat at a time.",
  defaults: { value: 250000, prefix: "", suffix: "+", decimals: 0, label: "views in 30 days", countDur: 1.6, hold: 1.8, x: 0.5, y: 0.5 },
  duration: (p) => 0.4 + p.countDur + p.hold + 0.45,
  anchor: (p) => ({ t: 0.4 + p.countDur, event: "the number is spoken (count lands on it)" }),
  cues(p) {
    const c = [{ at: 0.05, sfx: "whoosh_short_02", gain: -4 }];
    const n = 8;
    for (let i = 0; i < n; i++) {
      // ticks follow the ease-out of the count, so they slow down as the number settles
      const x = 1 - Math.pow(1 - (i + 1) / (n + 1), 0.6);
      c.push({ at: 0.4 + x * p.countDur * 0.9, sfx: `tick_0${(i % 3) + 1}`, gain: -2 });
    }
    c.push({ at: 0.4 + p.countDur, sfx: "success", gain: -2 });
    c.push({ at: 0.4 + p.countDur + p.hold, sfx: "swish_01", gain: -6 });
    return c;
  },
  build(root, p, k, f) {
    const u = f.u;
    const outAt = 0.4 + p.countDur + p.hold;
    const countEase = k.bezier(0.22, 1, 0.36, 1);
    const box = k.el("div", "abs", root);
    Object.assign(box.style, { left: p.x * f.width + "px", top: p.y * f.height + "px", transform: "translate(-50%,-50%)",
      display: "flex", flexDirection: "column", alignItems: "center", gap: 10 * u + "px" });
    const R = 230 * u, sw = 14 * u;
    const ring = k.el("div", null, box);
    ring.innerHTML = `<svg width="${R * 2 + sw * 2}" height="${R * 2 + sw * 2}" viewBox="0 0 ${R * 2 + sw * 2} ${R * 2 + sw * 2}">
      <circle cx="${R + sw}" cy="${R + sw}" r="${R}" fill="color-mix(in srgb, var(--bg) 78%, transparent)" stroke="var(--surface)" stroke-width="${sw}"/>
      <circle class="arc" cx="${R + sw}" cy="${R + sw}" r="${R}" fill="none" stroke="var(--accent)" stroke-width="${sw}"
        stroke-linecap="round" transform="rotate(-90 ${R + sw} ${R + sw})" stroke-dasharray="${2 * Math.PI * R}"/></svg>`;
    ring.style.position = "relative";
    const arc = ring.querySelector(".arc");
    const num = k.el("div", "display abs", ring);
    Object.assign(num.style, { inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 118 * u + "px", color: "var(--text)", fontVariantNumeric: "tabular-nums" });
    const label = k.el("div", "body", box);
    label.textContent = p.label;
    Object.assign(label.style, { fontSize: 40 * u + "px", color: "var(--text)", textShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,.5)` });

    const fmtNum = (v) => {
      const abs = Math.abs(v);
      let s;
      if (p.compact !== false && abs >= 1e6) s = (v / 1e6).toFixed(abs >= 1e7 ? 0 : 1) + "M";
      else if (p.compact !== false && abs >= 1e4) s = (v / 1e3).toFixed(0) + "K";
      else s = v.toLocaleString("en-US", { minimumFractionDigits: p.decimals, maximumFractionDigits: p.decimals });
      return p.prefix + s + p.suffix;
    };
    return (t) => {
      const sIn = k.spring(t, 0, { stiffness: 200, damping: 22, mass: 1 });
      const ex = k.p(t, outAt, k.D.short + 0.1, "exit");
      box.style.transform = `translate(-50%,-50%) scale(${(0.6 + 0.4 * sIn) * (1 - 0.15 * ex)})`;
      box.style.opacity = String(Math.min(1, t / 0.15) * (1 - ex));
      const c = countEase(k.clamp((t - 0.4) / p.countDur));
      const v = p.value * c;
      num.textContent = fmtNum(p.decimals ? v : Math.round(v));
      arc.style.strokeDashoffset = String(2 * Math.PI * R * (1 - c));
      label.style.transform = `translateY(${(1 - k.p(t, 0.3, k.D.medium)) * 30 * u}px)`;
      label.style.opacity = String(k.p(t, 0.3, k.D.medium));
    };
  },
};
