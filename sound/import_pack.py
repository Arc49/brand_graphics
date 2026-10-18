#!/usr/bin/env python3
"""Import a third-party SFX pack into the library, conformed to the house format.

Every file is converted to 48 kHz / 24-bit stereo WAV, loudness-normalised to a
tier from brand.json (default "ui"), tail-trimmed, and registered in
library/sfx/sfx.json with its source and license. Only import packs whose license
allows commercial use and redistribution (e.g. CC0).

  python3 sound/import_pack.py --src ~/Downloads/kenney_interface-sounds/Audio \
      --pack kenney_interface --license CC0-1.0 --source https://kenney.nl/assets/interface-sounds \
      --license-file ~/Downloads/kenney_interface-sounds/License.txt
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = (".ogg", ".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a")


def decode(path, sr):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).astype(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="folder of audio files")
    ap.add_argument("--pack", required=True, help="library sub-folder / category name")
    ap.add_argument("--license", required=True)
    ap.add_argument("--source", required=True, help="where the pack came from (URL)")
    ap.add_argument("--license-file", help="license text to copy next to the files")
    ap.add_argument("--tier", default="ui", help="loudness tier from brand.json sound.loudness")
    ap.add_argument("--prefix", default="", help="prefix for sound names (avoids clashes)")
    args = ap.parse_args()

    brand = json.load(open(os.path.join(ROOT, "brand", "brand.json")))
    synth.SR = sr = int(brand["sound"].get("sampleRate", 48000))
    bits = int(brand["sound"].get("bitDepth", 24))
    loud = brand["sound"]["loudness"]
    out_dir = os.path.join(ROOT, "library", "sfx", args.pack)
    mpath = os.path.join(ROOT, "library", "sfx", "sfx.json")
    manifest = json.load(open(mpath))

    files = sorted(f for f in os.listdir(args.src) if f.lower().endswith(AUDIO))
    for f in files:
        name = args.prefix + os.path.splitext(f)[0].lower().replace(" ", "_").replace("-", "_")
        st = decode(os.path.join(args.src, f), sr)
        if len(st) < 16 or np.max(np.abs(st)) < 1e-5:
            print(f"  skip {f} (silent)")
            continue
        st = synth.trim_tail(synth.normalize(st, loud[args.tier], loud["truePeakCeiling"]), fade=0.01)
        rel = f"{args.pack}/{name}.wav"
        synth.write_wav(os.path.join(ROOT, "library", "sfx", rel), st, bits)
        manifest["sounds"][name] = {
            "file": rel, "category": args.pack, "description": f"{args.pack} — {os.path.splitext(f)[0]}",
            "duration": round(len(st) / sr, 3), "sync": 0.0,
            "lufsMomentaryMax": round(synth.max_momentary_lufs(st), 1), "truePeakDb": round(synth.true_peak_db(st), 1),
            "license": args.license, "source": args.source,
        }
    if args.license_file:
        shutil.copy(args.license_file, os.path.join(out_dir, "LICENSE.txt"))
    with open(mpath, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"imported {len(files)} files into library/sfx/{args.pack}/")


if __name__ == "__main__":
    main()
