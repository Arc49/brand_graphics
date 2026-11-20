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

## Reveal del logo (`logo_reveal.py`)

Animazione da 10 s, trasparente, con sound design sincronizzato:

| Tempo | Cosa succede | Suono |
|---|---|---|
| 0,35–1,75 s | B, A, D, D, I, 3, S, T arrivano una alla volta, in **cromo grigio/argento**, e si **spiaccicano** contro il muro (schiacciamento, flash, onda d'urto, scintille, tremolio) | colpo metallico per ogni lettera, nota che sale lettera dopo lettera |
| 2,25 s | **C/S** compatto si spiaccica, colpo più forte; l'onda d'urto fa apparire gli ornamenti | riser + colpo grande + sub, "shing" metallico |
| 2,45 s | le **fiamme** partono da C/S e si allargano verso l'esterno; insieme a loro il **rosa** si propaga su lettere e ornamenti (con un fronte luminoso) | accensione + fuoco continuo |
| 3,55–4,45 s | la **corona 3D** cade girando e si posa | ronzio di rotazione + rintocco |
| 5,4 s → | la corona 3D **ruota su se stessa** (un giro ogni 2,6 s) | fruscio ad ogni giro + "tink" quando torna di fronte |

La corona è un vero modello 3D (cartella `crown3d/`, Three.js): fascia con gemme, punte, archi
gotici e anello luminoso, in cromo rosa. Prima del reveal va renderizzato il giro completo:

```bash
cd crown3d && npm install && node render.mjs   # 180 angolazioni trasparenti in crown3d/frames/ (~2 min)
```

File in `export/`: `baddi3st_reveal.webm` (trasparente + audio), `baddi3st_reveal_preview_black.mp4`,
`baddi3st_reveal_preview_checker.mp4`, `baddi3st_reveal_sfx.wav`.
Il master ProRes 4444 (~1,3 GB) si rigenera con:

```bash
python3 logo_reveal.py baddi3st_logo.jpg --out out_reveal
# tempi e durate: costanti T_LETTERS, T_CS, T_FIRE, T_CROWN_* in cima allo script
```
