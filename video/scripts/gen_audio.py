#!/usr/bin/env python3
"""
Generate the Promo's royalty-free SFX kit with the Python standard library
only (no numpy/ffmpeg). Outputs 16-bit mono PCM WAVs into public/.

SFX    : whoosh (page switch), sweep (graph/chart draw), pie (radial load),
         tick (numbers counting), click (buttons/toggles), chime (positive),
         pop (CTA).

The promo has no music bed — frame-synced SFX only.
Everything is synthesised from scratch -> 100% original / licence-free.
Re-run:  python3 scripts/gen_audio.py
"""
import math
import os
import random
import wave
from array import array

SR = 44100
random.seed(42)  # deterministic noise -> byte-identical re-runs
OUT = os.path.join(os.path.dirname(__file__), "..", "public")
os.makedirs(OUT, exist_ok=True)


# --------------------------------------------------------------------------- io
def write_wav(name, samples, sr=SR):
    buf = array("h")
    for s in samples:
        if s > 1.0:
            s = 1.0
        elif s < -1.0:
            s = -1.0
        buf.append(int(s * 32767))
    path = os.path.join(OUT, name)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(buf.tobytes())
    print(f"  {name}: {len(samples)/sr:.2f}s, {os.path.getsize(path)//1024} KB")


def normalize(buf, peak=0.9):
    m = max((abs(x) for x in buf), default=1.0) or 1.0
    g = peak / m
    return [x * g for x in buf]


# ----------------------------------------------------------------------- sfx
def make_whoosh():  # page / scene switch
    n = int(0.5 * SR)
    out = [0.0] * n
    y = 0.0
    for i in range(n):
        t = i / n
        x = random.gauss(0, 1)
        a = 0.02 + 0.22 * math.sin(math.pi * t)
        y = y + a * (x - y)
        out[i] = y * (math.sin(math.pi * t) ** 1.5)
    return [v * 0.6 for v in normalize(out, 0.9)]


def make_sweep():  # graph / chart / bar drawing in
    dur = 0.4
    n = int(dur * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        p = i / n
        f = 220.0 + 1000.0 * p          # rising pitch = value climbing
        air = random.gauss(0, 1) * 0.05 * (1 - p)
        env = math.sin(math.pi * p) ** 0.8
        out[i] = (math.sin(2 * math.pi * f * t) * 0.8 + air) * env
    return [v * 0.5 for v in normalize(out, 0.9)]


def make_pie():  # radial / pie load — rising whir with tremolo
    dur = 0.55
    n = int(dur * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        p = i / n
        f = 300.0 + 600.0 * p
        trem = 0.6 + 0.4 * math.sin(2 * math.pi * 18.0 * t)  # spinning feel
        env = (math.sin(math.pi * p) ** 0.7)
        s = (math.sin(2 * math.pi * f * t) * 0.6 +
             math.sin(2 * math.pi * f * 1.5 * t) * 0.3)
        out[i] = s * trem * env
    return [v * 0.5 for v in normalize(out, 0.9)]


def make_tick():  # numbers counting up
    n = int(0.05 * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 90.0)
        out[i] = (math.sin(2 * math.pi * 1250 * t) * 0.7 +
                  math.sin(2 * math.pi * 2500 * t) * 0.3) * env
    return [v * 0.5 for v in out]


def make_click():  # buttons / toggles
    n = int(0.04 * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.gauss(0, 1)
        hp = x - prev
        prev = x
        env = math.exp(-t * 320.0)
        out[i] = (hp * 0.6 + math.sin(2 * math.pi * 1800 * t) * 0.5) * env
    return [v * 0.55 for v in normalize(out, 0.9)]


def make_chime():  # positive accent
    dur = 0.7
    n = int(dur * SR)
    out = [0.0] * n
    partials = [(880.0, 1.0), (1760.0, 0.5), (2640.0 * 1.005, 0.25)]
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 5.0)
        out[i] = sum(math.sin(2 * math.pi * f * t) * a for f, a in partials) * env
    return [v * 0.5 for v in normalize(out, 0.9)]


def make_pop():  # CTA pop
    dur = 0.18
    n = int(dur * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        f = 700.0 * math.exp(-t * 14.0) + 170.0
        out[i] = math.sin(2 * math.pi * f * t) * math.exp(-t * 22.0)
    return [v * 0.6 for v in normalize(out, 0.9)]


if __name__ == "__main__":
    print("Generating SFX into public/ ...")
    write_wav("whoosh.wav", make_whoosh())
    write_wav("sweep.wav", make_sweep())
    write_wav("pie.wav", make_pie())
    write_wav("tick.wav", make_tick())
    write_wav("click.wav", make_click())
    write_wav("chime.wav", make_chime())
    write_wav("pop.wav", make_pop())
    print("Done.")
