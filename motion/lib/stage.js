// Stage runtime: loads brand tokens + templates, mounts a template at a format,
// and exposes window.__mount / window.__seek for the renderer. With ?mode=preview
// it also provides a scrubbable player that triggers the SFX cues live.
(function () {
  "use strict";
  const qs = new URLSearchParams(location.search);
  const MODE = qs.get("mode") || "preview";
  const ROOT = "../";
  const stage = document.getElementById("stage");
  const frame = document.getElementById("frame");

  let brand, kit, current = null, sfxIndex = null;

  async function loadJSON(p) {
    const r = await fetch(p, { cache: "no-store" });
    if (!r.ok) throw new Error(`${p}: ${r.status}`);
    return r.json();
  }

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.onload = res; s.onerror = () => rej(new Error("failed " + src));
      document.head.appendChild(s);
    });
  }

  function applyBrand(b) {
    const css = [];
    for (const [k, f] of Object.entries(b.font)) {
      if (f.file) css.push(`@font-face{font-family:"${f.family}";src:url("${ROOT}${f.file}");font-weight:${f.weight};}`);
    }
    const v = {
      "--font-display": `"${b.font.display.family}", Inter, sans-serif`,
      "--display-weight": b.font.display.weight,
      "--display-tracking": b.font.display.tracking,
      "--font-body": `"${b.font.body.family}", Inter, sans-serif`,
      "--body-weight": b.font.body.weight,
      "--body-tracking": b.font.body.tracking,
      "--font-mono": `"${b.font.mono.family}", monospace`,
      "--radius": b.shape.radius + "px",
      "--stroke": b.shape.stroke + "px",
    };
    for (const [k, c] of Object.entries(b.color)) v["--" + k] = c;
    css.push(":root{" + Object.entries(v).map(([k, x]) => `${k}:${x}`).join(";") + "}");
    const style = document.createElement("style");
    style.textContent = css.join("\n");
    document.head.appendChild(style);
  }

  const ready = (async () => {
    brand = await loadJSON(ROOT + "brand/brand.json");
    applyBrand(brand);
    kit = MotionCore.makeKit(brand);
    try { kit.logoSVG = await (await fetch(ROOT + brand.logo)).text(); } catch (e) { kit.logoSVG = ""; }
    const list = await loadJSON("templates/index.json");
    for (const f of list) await loadScript("templates/" + f);
    await document.fonts.ready;
    return true;
  })();

  function fmtFor(key) {
    const f = brand.formats[key];
    if (!f) throw new Error("unknown format " + key);
    const vertical = f.height > f.width;
    // u = 1px at a 1080px short edge; templates size everything in u.
    const u = Math.min(f.width, f.height) / 1080;
    const safe = brand.shape.safeMargin;
    return { key, width: f.width, height: f.height, vertical, u,
      safeX: f.width * safe, safeY: f.height * (vertical ? safe * 1.6 : safe), fps: brand.motion.fps };
  }

  async function mount(id, props = {}, formatKey = "landscape") {
    await ready;
    const T = Templates[id];
    if (!T) throw new Error("unknown template " + id + " (have: " + Object.keys(Templates).join(", ") + ")");
    const fmt = fmtFor(formatKey);
    const p = Object.assign({}, T.defaults || {}, props);
    stage.innerHTML = "";
    stage.style.width = fmt.width + "px";
    stage.style.height = fmt.height + "px";
    stage.style.setProperty("--u", fmt.u + "px");
    frame.style.width = fmt.width + "px";
    frame.style.height = fmt.height + "px";
    const duration = typeof T.duration === "function" ? T.duration(p, kit, fmt) : T.duration;
    const cues = (T.cues ? T.cues(p, kit, fmt) : []).map((c) => Object.assign({ gain: 0 }, c));
    const render = T.build(stage, p, kit, fmt);
    await document.fonts.ready;
    current = { id, T, p, fmt, duration, cues, render };
    render(0);
    return { id, duration, cues, fps: fmt.fps, width: fmt.width, height: fmt.height, props: p };
  }

  function seek(t) {
    if (current) current.render(Math.max(0, Math.min(t, current.duration)));
  }

  window.__ready = ready;
  window.__mount = mount;
  window.__seek = seek;
  window.__list = async () => {
    await ready;
    return Object.entries(Templates).map(([id, T]) => ({
      id, name: T.name, category: T.category, description: T.description, usage: T.usage,
      defaults: T.defaults, formats: T.formats || Object.keys(brand.formats),
    }));
  };

  if (MODE !== "preview") return;

  // ------------------------------------------------------------- preview player
  document.body.classList.add("preview");
  const ui = document.getElementById("ui");
  ui.hidden = false;
  const $ = (id) => document.getElementById(id);
  let playing = false, t0 = 0, tNow = 0, firedCues = new Set();
  let actx = null;
  const buffers = {};

  async function sfxBuffer(name) {
    if (!sfxIndex) sfxIndex = await loadJSON(ROOT + "library/sfx/sfx.json").catch(() => ({ sounds: {} }));
    const s = sfxIndex.sounds[name];
    if (!s) return null;
    if (!buffers[name]) {
      const data = await (await fetch(ROOT + "library/sfx/" + s.file)).arrayBuffer();
      buffers[name] = await actx.decodeAudioData(data);
    }
    return { buf: buffers[name], sync: s.sync };
  }

  async function scheduleCues(from) {
    if (!$("snd").checked) return;
    actx = actx || new AudioContext();
    const now = actx.currentTime;
    for (const c of current.cues) {
      const b = await sfxBuffer(c.sfx);
      if (!b) continue;
      const startAt = c.at - b.sync - from; // seconds from now
      const offset = Math.max(0, -startAt);
      if (offset >= b.buf.duration) continue;
      const src = actx.createBufferSource();
      const g = actx.createGain();
      g.gain.value = Math.pow(10, (c.gain || 0) / 20);
      src.buffer = b.buf; src.connect(g).connect(actx.destination);
      src.start(now + Math.max(0, startAt), offset);
      firedCues.add(src);
    }
  }

  function stopAudio() { firedCues.forEach((s) => { try { s.stop(); } catch (e) {} }); firedCues.clear(); }

  function fit() {
    if (!current) return;
    const maxW = Math.min(window.innerWidth - 32, 1100), maxH = window.innerHeight * 0.62;
    const s = Math.min(maxW / current.fmt.width, maxH / current.fmt.height);
    frame.style.transform = `scale(${s})`;
    frame.style.marginBottom = `${current.fmt.height * (s - 1)}px`;
    frame.style.marginLeft = `calc(50% - ${(current.fmt.width * s) / 2}px)`;
  }

  function drawCues() {
    $("cues").innerHTML = current.cues.map((c) =>
      `<span style="left:${(c.at / current.duration) * 100}%">${c.sfx}</span>`).join("");
  }

  function tick() {
    if (!playing) return;
    tNow = (performance.now() - t0) / 1000;
    if (tNow >= current.duration) { tNow = current.duration; playing = false; $("play").textContent = "▶ Play"; }
    show(tNow);
    if (playing) requestAnimationFrame(tick);
  }

  function show(t) {
    seek(t);
    $("time").textContent = t.toFixed(2) + "s / " + current.duration.toFixed(2) + "s";
    $("scrub").value = String(Math.round((t / current.duration) * 1000));
  }

  async function remount() {
    let props = {};
    try { props = JSON.parse($("props").value || "{}"); } catch (e) { }
    stopAudio(); playing = false; $("play").textContent = "▶ Play";
    await mount($("tpl").value, props, $("fmt").value);
    fit(); drawCues(); show(0);
    const u = new URL(location.href);
    u.searchParams.set("t", $("tpl").value); u.searchParams.set("f", $("fmt").value);
    history.replaceState(null, "", u);
  }

  (async () => {
    const list = await window.__list();
    $("tpl").innerHTML = list.map((x) => `<option value="${x.id}">${x.name}</option>`).join("");
    $("fmt").innerHTML = Object.entries(brand.formats).map(([k, f]) => `<option value="${k}">${f.label}</option>`).join("");
    if (qs.get("t")) $("tpl").value = qs.get("t");
    if (qs.get("f")) $("fmt").value = qs.get("f");
    const setProps = () => { $("props").value = JSON.stringify(Templates[$("tpl").value].defaults || {}, null, 2); };
    setProps();
    frame.className = "bg-" + $("bgsel").value;
    $("tpl").onchange = () => { setProps(); remount(); };
    $("fmt").onchange = remount;
    $("props").onchange = remount;
    $("bgsel").onchange = () => { frame.className = "bg-" + $("bgsel").value; };
    $("play").onclick = () => {
      if (playing) { playing = false; stopAudio(); $("play").textContent = "▶ Play"; return; }
      if (tNow >= current.duration) tNow = 0;
      playing = true; $("play").textContent = "❚❚ Pause";
      t0 = performance.now() - tNow * 1000;
      scheduleCues(tNow);
      requestAnimationFrame(tick);
    };
    $("scrub").oninput = () => {
      playing = false; stopAudio(); $("play").textContent = "▶ Play";
      tNow = ($("scrub").value / 1000) * current.duration; show(tNow);
    };
    window.addEventListener("resize", fit);
    document.addEventListener("keydown", (e) => { if (e.code === "Space" && e.target.tagName !== "TEXTAREA") { e.preventDefault(); $("play").click(); } });
    await remount();
  })();
})();
