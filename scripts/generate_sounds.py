"""Regenerate the bundled WAV files in scrapy_beep/sounds/.

Run from the repo root:
    python scripts/generate_sounds.py

Tweak the note sequences or harmonics below to change the sounds,
then commit the updated .wav files.
"""

import math
import pathlib
import struct
import wave

RATE = 44100
OUT_DIR = pathlib.Path(__file__).parent.parent / "scrapy_beep" / "sounds"


def tone(freq, dur_ms, vol=0.55, harmonics=None):
    n = int(RATE * dur_ms / 1000)
    fade = int(RATE * 0.012)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(i, n - i, fade) / fade
        v = math.sin(2 * math.pi * freq * t)
        if harmonics:
            for mult, amp in harmonics:
                v += amp * math.sin(2 * math.pi * freq * mult * t)
            v /= 1 + sum(a for _, a in harmonics)
        out.append(int(env * vol * 32767 * v))
    return out


def slide(f0, f1, dur_ms, vol=0.55, harmonics=None):
    n = int(RATE * dur_ms / 1000)
    fade = int(RATE * 0.012)
    phase = [0.0] * (1 + (len(harmonics) if harmonics else 0))
    out = []
    for i in range(n):
        env = min(i, n - i, fade) / fade
        freq = f0 + (f1 - f0) * (i / n)
        phase[0] += 2 * math.pi * freq / RATE
        v = math.sin(phase[0])
        if harmonics:
            for j, (mult, amp) in enumerate(harmonics):
                phase[j + 1] += 2 * math.pi * freq * mult / RATE
                v += amp * math.sin(phase[j + 1])
            v /= 1 + sum(a for _, a in harmonics)
        out.append(int(env * vol * 32767 * v))
    return out


def write_wav(samples, path):
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        for s in samples:
            f.writeframes(struct.pack("<h", max(-32767, min(32767, s))))


# Brass-like harmonics for the fanfare
brass = [(2, 0.45), (3, 0.2), (4, 0.08)]

# Trombone-like harmonics for the sad trombone
trombone = [(2, 0.55), (3, 0.35), (4, 0.15)]

success_samples = (
    tone(392,  80,  harmonics=brass) +   # G4
    tone(523,  80,  harmonics=brass) +   # C5
    tone(659,  80,  harmonics=brass) +   # E5
    tone(784,  100, harmonics=brass) +   # G5
    tone(1047, 420, harmonics=brass)     # C6 — big finish
)

failure_samples = (
    tone(466, 220, harmonics=trombone) +    # Bb4
    tone(440, 220, harmonics=trombone) +    # A4
    tone(415, 220, harmonics=trombone) +    # Ab4
    slide(392, 185, 600, harmonics=trombone)  # G4 → F#3 slide
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
write_wav(success_samples, OUT_DIR / "success.wav")
write_wav(failure_samples, OUT_DIR / "failure.wav")
print(f"Written to {OUT_DIR}/")
