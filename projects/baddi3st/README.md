# BADDI3ST C/S: fiamme animate + sound design

Loop da 6 s (1920×1080, 30 fps) del logo con le fiamme animate. Lettere, corona e
ornamenti cromati restano fermi; lo sfondo nero è rimosso (canale alfa).

| File (`export/`) | Cosa |
|---|---|
| `baddi3st_logo_flames_loop.webm` | video **trasparente** (VP9 + alfa) con audio: per web, OBS, CapCut, browser |
| `baddi3st_logo_flames_loop_preview_black.mp4` | anteprima su nero, con audio |
| `baddi3st_logo_flames_loop_preview_checker.mp4` | anteprima su scacchiera, per vedere la trasparenza |
| `baddi3st_fire_loop.wav` | sound design in loop (fuoco, crepitii, ondate, scintille), stessa durata del video |
| `baddi3st_ignite.wav` | one-shot di apertura: risucchio → accensione → colpo + brillio (colpo a 1,00 s) |

Il master **ProRes 4444 con alfa** (`.mov`, per Premiere/Resolve/Final Cut) pesa ~1,2 GB,
quindi non è nel repository: si rigenera con i comandi qui sotto (finisce in `out/`).

```bash
python3 flame_sound.py --out out
python3 animate_flames.py baddi3st_logo.jpg --out out --size 1920x1080 --audio out/baddi3st_fire_loop.wav
# opzioni: --seconds 8  --strength 1.4 (fiamme più mosse)  --embers 120  --keep-black
```
