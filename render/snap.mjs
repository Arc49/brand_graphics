#!/usr/bin/env node
// Quick look without encoding: screenshots a template at several times and tiles them into one PNG.
//   node render/snap.mjs <template> [format] [--times 0.2,0.5,1] [--props JSON] [--out file.png]
import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { execSync, execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf("--" + k); return i >= 0 ? argv[i + 1] : d; };
const pos = argv.filter((a, i) => !a.startsWith("--") && !(i > 0 && argv[i - 1].startsWith("--")));
const [tpl, fmt = "landscape"] = pos;

let pw;
try { pw = await import("playwright"); } catch { pw = createRequire(path.join(execSync("npm root -g").toString().trim(), "x.js"))("playwright"); }
const srv = http.createServer((q, r) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(q.url, "http://x").pathname));
  if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "content-type": { ".js": "text/javascript", ".svg": "image/svg+xml", ".css": "text/css", ".html": "text/html" }[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(r);
}).listen(0);
const brand = JSON.parse(fs.readFileSync(path.join(ROOT, "brand/brand.json"), "utf8"));
const F = brand.formats[fmt];
const browser = await pw.chromium.launch();
const page = await browser.newPage({ viewport: { width: F.width, height: F.height } });
page.on("pageerror", (e) => console.error("page error:", e.message));
await page.goto(`http://127.0.0.1:${srv.address().port}/motion/stage.html?mode=render`);
await page.addStyleTag({ content: "body{background:#4a5363 !important}" });
const info = await page.evaluate(([t, p, f]) => window.__mount(t, p, f), [tpl, JSON.parse(opt("props", "{}")), fmt]);
const times = opt("times") ? opt("times").split(",").map(Number) : Array.from({ length: 8 }, (_, i) => (info.duration * (i + 0.5)) / 8);
const dir = fs.mkdtempSync("/tmp/snap-");
for (const [i, t] of times.entries()) {
  await page.evaluate((tt) => window.__seek(tt), t);
  await page.screenshot({ path: `${dir}/${i}.png` });
}
await browser.close(); srv.close();
const out = opt("out", path.join(ROOT, "out", `snap_${tpl}_${fmt}.png`));
fs.mkdirSync(path.dirname(out), { recursive: true });
const cols = Math.min(4, times.length), rows = Math.ceil(times.length / cols);
execFileSync("ffmpeg", ["-v", "error", "-y", "-framerate", "1", "-i", `${dir}/%d.png`, "-vf",
  `scale=${fmt === "vertical" ? 270 : 480}:-1,drawtext=text='%{n}':x=8:y=8:fontcolor=white:fontsize=18,tile=${cols}x${rows}`, "-frames:v", "1", out]);
console.log(out, "times:", times.map((t) => t.toFixed(2)).join(", "), "duration:", info.duration.toFixed(2));
