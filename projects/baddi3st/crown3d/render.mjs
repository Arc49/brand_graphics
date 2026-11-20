#!/usr/bin/env node
// Renders the 3D crown as transparent turntable frames: frames/a000.png … (one per `step` degrees)
// plus anchors.json (where the front of the band lands, for compositing into the logo).
//   node render.mjs [--step 2] [--w 1600 --h 1150] [--only 0,30,90]
import fs from "node:fs";
import path from "node:path";
import http from "node:http";
import { execSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf("--" + k); return i >= 0 ? argv[i + 1] : d; };
const step = +opt("step", 2), w = +opt("w", 1600), h = +opt("h", 1150);
const only = opt("only", null);
const outDir = path.join(DIR, opt("out", "frames"));
fs.mkdirSync(outDir, { recursive: true });

let pw;
try { pw = await import("playwright"); } catch { pw = createRequire(path.join(execSync("npm root -g").toString().trim(), "x.js"))("playwright"); }
const MIME = { ".html": "text/html", ".js": "text/javascript" };
const srv = http.createServer((q, r) => {
  const p = path.join(DIR, decodeURIComponent(new URL(q.url, "http://x").pathname));
  if (!p.startsWith(DIR) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { r.writeHead(404); return r.end(); }
  r.writeHead(200, { "content-type": MIME[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(r);
}).listen(0);

const browser = await pw.chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const page = await browser.newPage({ viewport: { width: w, height: h } });
page.on("pageerror", (e) => console.error("page error:", e.message));
page.on("console", (m) => { if (m.type() === "error") console.error("console:", m.text()); });
await page.goto(`http://127.0.0.1:${srv.address().port}/crown.html?w=${w}&h=${h}`);
await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
fs.writeFileSync(path.join(DIR, "anchors.json"), JSON.stringify(await page.evaluate(() => window.anchors()), null, 2));

const angles = only ? only.split(",").map(Number) : Array.from({ length: Math.round(360 / step) }, (_, i) => i * step);
const t0 = Date.now();
for (const [i, a] of angles.entries()) {
  const data = await page.evaluate((deg) => { window.setAngle(deg); return window.snapshot(); }, a);
  fs.writeFileSync(path.join(outDir, `a${String(a).padStart(3, "0")}.png`), Buffer.from(data.split(",")[1], "base64"));
  if (i % 30 === 0) console.log(`  ${i}/${angles.length}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
}
await browser.close();
srv.close();
console.log("done", angles.length, "frames →", outDir);
