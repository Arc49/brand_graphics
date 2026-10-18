#!/usr/bin/env node
// Renders motion templates to editor-ready files:
//   <name>_<format>.mov       ProRes 4444 with alpha + 24-bit PCM SFX track (Premiere / Resolve / FCP)
//   <name>_<format>.webm      VP9 with alpha + Opus SFX (web, CapCut, browser-based editors)
//   <name>_<format>_sfx.wav   the SFX bed alone, sample-aligned to the overlay's first frame
//   <name>_<format>_preview.mp4  composited over a stand-in background, for review
//   <name>_<format>.png       poster frame
// and merges an entry per render into out/manifest.json for editing agents.
//
//   node render/render.mjs --job jobs/showcase.json [--only name,name] [--formats landscape] [--fast]
//   node render/render.mjs --template lower_third --props '{"name":"Sam"}' --formats landscape,vertical [--theme light]
import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { spawn, execSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function loadPlaywright() {
  try { return await import("playwright"); } catch (e) {
    const g = execSync("npm root -g").toString().trim();
    return createRequire(path.join(g, "noop.js"))("playwright");
  }
}

function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) {
    if (!a[i].startsWith("--")) continue;
    const k = a[i].slice(2), v = a[i + 1] && !a[i + 1].startsWith("--") ? a[++i] : true;
    o[k] = v;
  }
  return o;
}

const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".wav": "audio/wav", ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf", ".png": "image/png" };

function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, resp) => {
      const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
      if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { resp.writeHead(404); return resp.end(); }
      resp.writeHead(200, { "content-type": MIME[path.extname(p)] || "application/octet-stream" });
      fs.createReadStream(p).pipe(resp);
    });
    srv.listen(0, "127.0.0.1", () => res(srv));
  });
}

function ff(argv, label) {
  return new Promise((res, rej) => {
    const p = spawn("ffmpeg", ["-hide_banner", "-loglevel", "error", "-y", ...argv]);
    let err = "";
    p.stderr.on("data", (d) => (err += d));
    p.on("close", (c) => (c === 0 ? res() : rej(new Error(`ffmpeg ${label} failed:\n${err}`))));
  });
}

const sfxIndex = () => JSON.parse(fs.readFileSync(path.join(ROOT, "library/sfx/sfx.json"), "utf8"));

// Resolve cues to absolute start times. Returns lead-in needed if a sound must start before frame 0
// (e.g. a riser whose sync point is its end).
function planAudio(cues, sfx) {
  const items = [];
  for (const c of cues) {
    const s = sfx.sounds[c.sfx];
    if (!s) { console.warn(`  ! unknown sfx "${c.sfx}" — skipped`); continue; }
    let start = c.at - s.sync, trim = 0;
    // a few ms early: trim the (near-silent) head instead of adding a lead-in to the whole clip
    if (start < 0 && start > -0.04) { trim = -start; start = 0; }
    items.push({ ...c, file: path.join(ROOT, "library/sfx", s.file), start, trim, len: s.duration });
  }
  const lead = Math.max(0, -Math.min(0, ...items.map((i) => i.start)));
  return { items, lead };
}

async function mixAudio(items, lead, outWav) {
  if (!items.length) return false;
  const inputs = items.flatMap((i) => ["-i", i.file]);
  const chains = items.map((i, n) => {
    const ms = Math.round((i.start + lead) * 1000);
    const trim = i.trim ? `atrim=start=${i.trim.toFixed(4)},asetpts=PTS-STARTPTS,` : "";
    return `[${n}:a]${trim}volume=${i.gain || 0}dB,adelay=${ms}:all=1[a${n}]`;
  });
  const mixIn = items.map((_, n) => `[a${n}]`).join("");
  const graph = `${chains.join(";")};${mixIn}amix=inputs=${items.length}:normalize=0:dropout_transition=0,alimiter=limit=0.89:level=false[out]`;
  await ff([...inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s24le", outWav], "audio mix");
  return true;
}

async function renderOne(page, base, job, fmtKey, opts) {
  const brand = JSON.parse(fs.readFileSync(path.join(ROOT, "brand/brand.json"), "utf8"));
  const theme = job.theme || opts.theme || brand.theme;
  const base_ = job.name || `${job.template}_${theme}`;
  const name = `${base_}_${fmtKey}`;
  const dir = path.join(opts.out, base_);
  fs.mkdirSync(dir, { recursive: true });
  const f = brand.formats[fmtKey];
  await page.setViewportSize({ width: f.width, height: f.height });
  await page.goto(`${base}/motion/stage.html?mode=render`);
  const info = await page.evaluate(([id, props, fk, th]) => window.__mount(id, props, fk, th), [job.template, job.props || {}, fmtKey, theme]);
  const meta = await page.evaluate((id) => {
    const T = Templates[id];
    return { usage: T.usage, description: T.description, category: T.category, name: T.name };
  }, job.template);
  const anchor = await page.evaluate(([id, props]) => {
    const T = Templates[id];
    const p = Object.assign({}, T.defaults || {}, props);
    return T.anchor ? T.anchor(p) : { t: 0, event: "start" };
  }, [job.template, job.props || {}]);

  const fps = Number(opts.fps || info.fps);
  const { items, lead } = planAudio(info.cues, sfxIndex());
  const leadFrames = Math.ceil(lead * fps);
  const leadT = leadFrames / fps;
  const nFrames = leadFrames + Math.round(info.duration * fps) + 1;

  const tmp = path.join(opts.out, ".frames", name);
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  const t0 = Date.now();
  for (let i = 0; i < nFrames; i++) {
    const t = i / fps - leadT;
    await page.evaluate((tt) => window.__seek(tt), t);
    await page.screenshot({ path: path.join(tmp, `f${String(i).padStart(5, "0")}.png`), omitBackground: true });
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(1);

  const wav = path.join(dir, `${name}_sfx.wav`);
  const hasAudio = await mixAudio(items, leadT, wav);
  const frames = ["-framerate", String(fps), "-i", path.join(tmp, "f%05d.png")];
  const aIn = hasAudio ? ["-i", wav] : [];
  const files = {};

  if (!opts.fast) {
    files.mov = `${name}.mov`;
    await ff([...frames, ...aIn, "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0",
      ...(hasAudio ? ["-c:a", "pcm_s24le"] : []), path.join(dir, files.mov)], "prores");
  }
  files.webm = `${name}.webm`;
  await ff([...frames, ...aIn, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "28", "-row-mt", "1",
    "-auto-alt-ref", "0", "-deadline", "good", "-cpu-used", "4", ...(hasAudio ? ["-c:a", "libopus", "-b:a", "160k"] : []),
    path.join(dir, files.webm)], "webm");

  // review copy: overlay on a moving stand-in background so motion + sound can be judged together
  files.preview = `${name}_preview.mp4`;
  const bg = `gradients=s=${f.width}x${f.height}:c0=0x5a6577:c1=0x1d222b:c2=0x37404f:n=3:speed=0.015:r=${fps}`;
  await ff(["-f", "lavfi", "-i", bg, ...frames, ...aIn, "-filter_complex", "[0:v][1:v]overlay=shortest=1,format=yuv420p[v]",
    "-map", "[v]", ...(hasAudio ? ["-map", "2:a", "-c:a", "aac", "-b:a", "192k"] : []), "-c:v", "libx264", "-crf", "20",
    "-preset", "medium", "-movflags", "+faststart", path.join(dir, files.preview)], "preview");

  files.poster = `${name}.png`;
  const posterT = Math.min(info.duration - 0.05, anchor.t + 0.8);
  fs.copyFileSync(path.join(tmp, `f${String(leadFrames + Math.round(posterT * fps)).padStart(5, "0")}.png`), path.join(dir, files.poster));
  if (hasAudio) files.wav = `${name}_sfx.wav`; else fs.rmSync(wav, { force: true });
  fs.rmSync(tmp, { recursive: true, force: true });

  console.log(`  ✓ ${name}  ${nFrames} frames in ${secs}s${leadFrames ? `  (lead-in ${leadT.toFixed(2)}s)` : ""}`);
  return {
    id: name, template: job.template, templateName: meta.name, category: meta.category, format: fmtKey, theme,
    width: f.width, height: f.height, fps, duration: +(nFrames / fps).toFixed(3), leadIn: +leadT.toFixed(3),
    dir: path.relative(opts.out, dir), files, props: info.props,
    anchor: { t: +(anchor.t + leadT).toFixed(3), event: anchor.event },
    cues: items.map((i) => ({ sfx: i.sfx, at: +(i.at + leadT).toFixed(3), gain: i.gain || 0 })),
    description: meta.description, usage: meta.usage,
  };
}

async function main() {
  const a = args();
  const opts = { out: path.resolve(ROOT, a.out || "out"), fast: !!a.fast, fps: a.fps, theme: a.theme };
  let jobs;
  if (a.job) jobs = JSON.parse(fs.readFileSync(path.resolve(a.job), "utf8")).renders;
  else if (a.template) jobs = [{ name: a.name, template: a.template, props: a.props ? JSON.parse(a.props) : {} }];
  else { console.error("usage: render.mjs --job jobs/showcase.json | --template <id> [--props JSON]"); process.exit(1); }
  if (a.only) { const s = new Set(String(a.only).split(",")); jobs = jobs.filter((j) => s.has(j.name || j.template)); }
  const fmtOverride = a.formats ? String(a.formats).split(",") : null;

  if (!fs.existsSync(path.join(ROOT, "library/sfx/sfx.json"))) {
    console.log("SFX library missing — generating…");
    execSync(`python3 ${path.join(ROOT, "sound/synth.py")}`, { stdio: "inherit" });
  }

  const srv = await serve();
  const base = `http://127.0.0.1:${srv.address().port}`;
  const { chromium } = await loadPlaywright();
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  page.on("pageerror", (e) => console.error("  page error:", e.message));

  const brandTheme = JSON.parse(fs.readFileSync(path.join(ROOT, "brand/brand.json"), "utf8")).theme;
  const manifestPath = path.join(opts.out, "manifest.json");
  const manifest = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, "utf8")) : { assets: {} };
  const save = () => {
    manifest.generated = new Date().toISOString();
    manifest.brand = JSON.parse(fs.readFileSync(path.join(ROOT, "brand/brand.json"), "utf8")).name;
    fs.mkdirSync(opts.out, { recursive: true });
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  };
  try {
    for (const job of jobs) {
      for (const fk of fmtOverride || job.formats || ["landscape", "vertical"]) {
        const th = job.theme || opts.theme || brandTheme;
        const done = Object.values(manifest.assets).find((e) => e.format === fk && e.dir === (job.name || `${job.template}_${th}`));
        if (a.resume && done && fs.existsSync(path.join(opts.out, done.dir, done.files.webm))) { console.log(`  · ${done.id} (kept)`); continue; }
        const entry = await renderOne(page, base, job, fk, opts);
        manifest.assets[entry.id] = entry;
        save(); // after every render, so an interrupted run can --resume
      }
    }
  } finally {
    await browser.close();
    srv.close();
    save();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
