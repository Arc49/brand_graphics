// Motion core: deterministic, seekable animation helpers shared by every template.
// A template is a pure function of time — render(t) must give the same frame for the
// same t, so the renderer can capture frame-by-frame and the preview can scrub.
(function () {
  "use strict";

  // CSS-style cubic-bezier solver (same curve as the browser's cubic-bezier()).
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return function (x) {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(t) - x, d = dx(t);
        if (Math.abs(e) < 1e-6) break;
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1;
      for (let i = 0; i < 20 && Math.abs(sx(t) - x) > 1e-6; i++) {
        if (sx(t) < x) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return sy(t);
    };
  }

  // Analytic damped spring (0 -> 1), matches stiffness/damping/mass feel of UI springs.
  function spring({ stiffness = 170, damping = 20, mass = 1 } = {}) {
    const w0 = Math.sqrt(stiffness / mass);
    const zeta = damping / (2 * Math.sqrt(stiffness * mass));
    return function (t) {
      if (t <= 0) return 0;
      if (zeta < 1) {
        const wd = w0 * Math.sqrt(1 - zeta * zeta);
        return 1 - Math.exp(-zeta * w0 * t) * (Math.cos(wd * t) + (zeta * w0 / wd) * Math.sin(wd * t));
      }
      return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    };
  }

  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, p) => a + (b - a) * p;

  function makeKit(brand) {
    const m = brand.motion;
    const ease = {};
    for (const [k, v] of Object.entries(m.ease)) ease[k] = bezier(...v);
    const springFn = spring(m.spring);

    return {
      brand, ease, clamp, lerp, bezier,
      D: m.duration,
      stagger: m.stagger,
      // Progress of a segment [start, start+dur] at time t, eased.
      p(t, start, dur, e = "enter") {
        const fn = typeof e === "function" ? e : ease[e];
        return fn(clamp((t - start) / dur));
      },
      // Spring progress starting at `start` (can overshoot past 1).
      spring(t, start, opts) {
        return (opts ? spring(opts) : springFn)(Math.max(0, t - start));
      },
      // Enter at `inAt`, exit at `outAt`: returns {p, phase} where p goes 0->1->0.
      inOut(t, inAt, outAt, dIn = m.duration.medium, dOut = m.duration.short) {
        if (t < outAt) return this.p(t, inAt, dIn, "enter");
        return 1 - this.p(t, outAt, dOut, "exit");
      },
      // Split text into spans (by "word" or "char") for staggered reveals.
      split(el, text, by = "word") {
        el.textContent = "";
        const parts = by === "char" ? [...text] : text.split(/(\s+)/);
        return parts.map((s) => {
          // plain text node for spaces so wrapped lines don't start with a space
          if (/^\s+$/.test(s)) { el.appendChild(document.createTextNode(by === "char" ? " " : " ")); return null; }
          const span = document.createElement("span");
          span.textContent = s;
          span.style.display = "inline-block";
          span.style.willChange = "transform, opacity";
          el.appendChild(span);
          return span;
        }).filter(Boolean);
      },
      el(tag, cls, parent, html) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html != null) e.innerHTML = html;
        if (parent) parent.appendChild(e);
        return e;
      },
    };
  }

  window.MotionCore = { bezier, spring, clamp, lerp, makeKit };
  window.Templates = window.Templates || {};
})();
