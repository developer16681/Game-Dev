"""
Procedural audio fallback (standard library only: math, wave, array).

If you have not put real files into assets/audio/, AudioManager asks this module to
synthesise simple chiptune-style sounds and caches them as assets/audio/_generated/gen_<name>.wav.
They are only generated once; delete the folder to regenerate.
"""
import math
import random
import sys
import wave
from array import array
from pathlib import Path

SR = 22050


# ------------------------------------------------------------------ primitives
def _midi_to_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def _osc(kind, phase):
    p = phase % 1.0
    if kind == "sine":
        return math.sin(2 * math.pi * p)
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "pulse":
        return 1.0 if p < 0.25 else -1.0
    if kind == "saw":
        return 2 * p - 1
    if kind == "tri":
        return 4 * abs(p - 0.5) - 1
    return 0.0


def tone(freq, dur, kind="sine", vol=1.0, attack=0.004, decay=5.0, freq_end=None):
    """A single oscillator note with an exponential decay and optional pitch sweep."""
    n = max(1, int(SR * dur))
    out, phase = [], 0.0
    for i in range(n):
        frac = i / max(1, n - 1)
        f = freq if freq_end is None else freq + (freq_end - freq) * frac
        phase += f / SR
        env = math.exp(-decay * frac)
        if attack > 0:
            env *= min(1.0, (i / SR) / attack)
        out.append(_osc(kind, phase) * env * vol)
    return out


def noise(dur, vol=1.0, a0=0.5, a1=0.5, decay=4.0, bell=False):
    """Low-passed white noise. a0/a1 = filter coefficient at start/end (small = darker)."""
    n = max(1, int(SR * dur))
    out, y = [], 0.0
    for i in range(n):
        frac = i / max(1, n - 1)
        a = a0 + (a1 - a0) * frac
        y += a * (random.uniform(-1, 1) - y)
        env = math.sin(math.pi * frac) if bell else math.exp(-decay * frac)
        out.append(y * env * vol)
    return out


def _mix_into(buf, samples, start, gain=1.0):
    for i, s in enumerate(samples):
        j = start + i
        if j >= len(buf):
            break
        buf[j] += s * gain


def _sum(*parts):
    n = max(len(p) for p in parts)
    buf = [0.0] * n
    for p in parts:
        _mix_into(buf, p, 0)
    return buf


def _concat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out


def write_wav(path, samples, peak=0.9):
    m = max((abs(s) for s in samples), default=0.0)
    scale = peak / m if m > peak else 1.0
    data = array("h", (int(max(-1.0, min(1.0, s * scale)) * 32767) for s in samples))
    if sys.byteorder == "big":
        data.byteswap()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ------------------------------------------------------------------ sound builders
def _build_jump():
    return tone(330, 0.20, "square", 0.35, decay=4, freq_end=760)


def _build_slide():
    return _sum(noise(0.38, 2.4, a0=0.55, a1=0.06, decay=2.2),
                tone(320, 0.38, "sine", 0.35, decay=3, freq_end=110))


def _build_lane_switch():  # whoosh
    return noise(0.22, 3.0, a0=0.06, a1=0.40, bell=True)


def _build_land():
    return _sum(tone(160, 0.14, "sine", 0.8, decay=6, freq_end=50),
                noise(0.06, 1.2, a0=0.5, a1=0.2, decay=6))


def _build_crash():
    return _sum(noise(0.70, 2.0, a0=0.6, a1=0.05, decay=3.5),
                tone(120, 0.70, "saw", 0.45, decay=5, freq_end=35))


def _build_game_over():
    notes = ((440, 0.18), (392, 0.18), (349, 0.18), (262, 0.60))
    return _concat(*[tone(f, d, "pulse", 0.30, decay=2.5) for f, d in notes])


def _build_start():
    notes = ((392, 0.07), (523, 0.07), (659, 0.07), (784, 0.20))
    return _concat(*[tone(f, d, "pulse", 0.25, decay=2.0) for f, d in notes])


def _build_bgm():
    """8-bar upbeat loop @140 BPM in A minor (Am - F - C - G): kick, snare, hats, bass, arp, lead."""
    bpm, bars = 140, 8
    step = 60.0 / bpm / 4                         # one 16th note
    total = int(SR * step * 16 * bars)            # exact length => seamless loop
    buf = [0.0] * total
    chords = [(57, (0, 3, 7)), (53, (0, 4, 7)), (48, (0, 4, 7)), (55, (0, 4, 7))]
    for bar in range(bars):
        root, iv = chords[bar % 4]
        for s in range(16):
            start = int(SR * step * (bar * 16 + s))
            if s % 4 == 0:                                         # kick
                _mix_into(buf, tone(120, 0.14, "sine", 0.9, decay=6, freq_end=45), start)
            if s in (4, 12):                                       # snare
                _mix_into(buf, noise(0.12, 1.4, 0.5, 0.5, decay=5), start, 0.5)
            if s % 2 == 1:                                         # hi-hat
                _mix_into(buf, noise(0.035, 1.2, 0.9, 0.9, decay=5), start, 0.22)
            if s % 2 == 0:                                         # bass
                m = root - 12 + (12 if s % 8 == 4 else 0)
                _mix_into(buf, tone(_midi_to_freq(m), step * 1.8, "tri", 0.55, decay=2.5), start)
            m = root + 12 + iv[(0, 1, 2, 1)[s % 4]] + (12 if (s // 4) % 2 else 0)   # arp
            _mix_into(buf, tone(_midi_to_freq(m), step * 1.4, "pulse", 0.15, decay=4), start)
            if bar >= 4 and s in (0, 3, 6, 8, 11):                 # lead (second half only)
                m = root + 24 + iv[(s // 3) % 3]
                _mix_into(buf, tone(_midi_to_freq(m), step * (3 if s in (0, 6) else 2),
                                    "square", 0.10, decay=3), start)
    return buf


BUILDERS = {
    "bgm": _build_bgm,
    "lane_switch": _build_lane_switch,
    "jump": _build_jump,
    "slide": _build_slide,
    "crash": _build_crash,
    "game_over": _build_game_over,
    "land": _build_land,
    "start": _build_start,
}


def generate(name, out_dir):
    """Create gen_<name>.wav in out_dir if it does not exist yet; return its Path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"gen_{name}.wav"
    if not path.exists():
        write_wav(path, BUILDERS[name]())
    return path
