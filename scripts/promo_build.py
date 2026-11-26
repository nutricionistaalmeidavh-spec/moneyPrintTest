"""Two render workflows for the same promo request: ``short`` (9:16) and ``video`` (16:9).

    python -m scripts.promo_build --manifest requests/<x>.promo.json --format short --out outputs/promo

Inputs: a request JSON (narrations) plus a ``.promo.json`` manifest (per-section
voice file, stills, optional clip, bullets). The voice is produced elsewhere
(ElevenLabs, Kokoro...) and just dropped in as an audio file.

Both formats share: word-by-word karaoke captions timed from the real audio
(silence detection), progress bar, chapter chips, whoosh sounds on transitions.
``short`` is a native vertical layout (animated orbs, floating media frame with
push-in, staggered topic pills). ``video`` reuses the repo's motion-slide
renderer for the chapters and adds the shared layer on top.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import quality

REPO = Path(__file__).resolve().parent.parent
XF = 0.35               # transition length (s)
TAIL = XF + 0.12        # silence appended to each voice file so the crossfade never eats words
OUTRO_S = 3.2
FPS = 30
ACCENT_BGR = "F58AA3"   # ASS colours are BGR -> #A38AF5

FORMATS = {"video": (1920, 1080), "short": (1080, 1920)}


# ------------------------------------------------------------------ helpers
def run(cmd: list[str]) -> None:
    subprocess.run([str(c) for c in cmd], check=True)


def probe(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def ass_time(sec: float) -> str:
    cs = int(round(max(0.0, sec) * 100))
    return f"{cs // 360000}:{(cs // 6000) % 60:02d}:{(cs // 100) % 60:02d}.{cs % 100:02d}"


def esc(text: str) -> str:
    return text.replace("{", "(").replace("}", ")")


def circle_path(r: int) -> str:
    k = int(r * 0.5523)
    return (f"m 0 {r} b 0 {r - k} {r - k} 0 {r} 0 b {r + k} 0 {2 * r} {r - k} {2 * r} {r} "
            f"b {2 * r} {r + k} {r + k} {2 * r} {r} {2 * r} b {r - k} {2 * r} 0 {r + k} 0 {r}")


# ------------------------------------------------------------------ voice
def prepare_voice(src: Path, dst: Path) -> float:
    """Trim leading silence, add the crossfade tail, 48 kHz mono WAV."""
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", src,
             "-af", f"silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,highpass=f=70,apad=pad_dur={TAIL}",
             "-ar", 48000, "-ac", 1, dst])
    return probe(dst)


def speech_intervals(wav: Path, total: float) -> list[tuple[float, float]]:
    """Voiced intervals (s) from silencedetect, excluding the artificial tail."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "silencedetect=noise=-38dB:d=0.12",
                           "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", proc.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", proc.stderr)]
    end_speech = max(0.1, total - TAIL)
    return voiced_from_silences(starts, ends, end_speech)


def voiced_from_silences(starts: list[float], ends: list[float], end_speech: float) -> list[tuple[float, float]]:
    cur, out = 0.0, []
    for i, s in enumerate(starts):
        s = min(s, end_speech)
        if s - cur > 0.05:
            out.append((cur, s))
        cur = ends[i] if i < len(ends) else end_speech
        if cur >= end_speech:
            break
    if cur < end_speech - 0.05:
        out.append((cur, end_speech))
    return out or [(0.0, end_speech)]


def word_times(narration: str, intervals: list[tuple[float, float]]) -> list[tuple[str, float, float]]:
    """Spread words over voiced time proportionally to their length (pauses are skipped)."""
    words = narration.split()
    weights = [len(re.sub(r"\W", "", w)) + 1.5 for w in words]
    voiced = sum(b - a for a, b in intervals)
    total_w = sum(weights)

    def at(offset: float) -> float:
        for a, b in intervals:
            if offset <= b - a + 1e-9:
                return a + offset
            offset -= b - a
        return intervals[-1][1]

    out, acc = [], 0.0
    for w, wt in zip(words, weights):
        a = at(voiced * acc / total_w)
        acc += wt
        b = at(voiced * acc / total_w)
        out.append((w, a, b))
    return out


def caption_chunks(words: list[tuple[str, float, float]], max_words: int, max_chars: int) -> list[list[tuple[str, float, float]]]:
    chunks, cur = [], []
    for item in words:
        cur.append(item)
        chars = sum(len(w) + 1 for w, _, _ in cur)
        if len(cur) >= max_words or chars >= max_chars or (item[0].endswith((".", "?", "!")) and len(cur) >= 2):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


# ------------------------------------------------------------------ ASS
class Ass:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.events: list[str] = []

    def add(self, a: float, b: float, style: str, body: str, layer: int = 0) -> None:
        self.events.append(f"Dialogue: {layer},{ass_time(a)},{ass_time(b)},{style},,0,0,0,,{body}")

    def karaoke(self, start_off: float, chunks, style: str, pos: tuple[int, int], layer: int = 3) -> None:
        for ci, chunk in enumerate(chunks):
            a = chunk[0][1]
            nxt = chunks[ci + 1][0][1] if ci + 1 < len(chunks) else chunk[-1][2]
            b = max(chunk[-1][2] + 0.05, min(nxt, chunk[-1][2] + 0.5)) - 0.01
            parts = []
            for wi, (w, ws, we) in enumerate(chunk):
                end = chunk[wi + 1][1] if wi + 1 < len(chunk) else we
                cs = max(5, int(round((end - ws) * 100)))
                parts.append(r"{\kf" + str(cs) + "}" + esc(w.upper()) + " ")
            body = (r"{\an5\pos(%d,%d)\fscx85\fscy85\t(0,130,\fscx100\fscy100)}" % pos) + "".join(parts).rstrip()
            self.add(start_off + a, start_off + b, style, body, layer)

    def render(self, styles: str) -> str:
        return ("[Script Info]\nScriptType: v4.00+\n"
                f"PlayResX: {self.w}\nPlayResY: {self.h}\nScaledBorderAndShadow: yes\nWrapStyle: 0\n[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                "MarginR, MarginV, Encoding\n" + styles +
                "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                + "\n".join(self.events) + "\n")


def style(name, size, primary="FFFFFF", secondary=None, outline="000000", bold=1, border=1, outline_w=0, align=5,
          spacing=0, margin_lr=10, outline_alpha="00"):
    secondary = secondary or primary
    return (f"Style: {name},Inter,{size},&H00{primary},&H00{secondary},&H{outline_alpha}{outline},&H00000000,{-bold},0,0,0,"
            f"100,100,{spacing},0,{border},{outline_w},0,{align},{margin_lr},{margin_lr},10,1\n")


def orbs(ass: Ass, total: float, seed_pts: list[tuple[int, int, int, str]]) -> None:
    """Large blurred colour blobs drifting slowly: cheap 'living background' motion."""
    for i, (x, y, r, col) in enumerate(seed_pts):
        dx, dy = (1 if i % 2 == 0 else -1) * ass.w * 0.12, (1 if i % 3 else -1) * ass.h * 0.05
        t_ms = int(total * 1000)
        ass.add(0, total, "Shape",
                (r"{\an7\move(%d,%d,%d,%d,0,%d)\blur90\1c&H%s&\alpha&HA4&\p1}" % (x - r, y - r, x - r + dx, y - r + dy, t_ms, col))
                + circle_path(r), layer=0)


# ------------------------------------------------------------------ sfx
def whoosh_inputs(times: list[float]) -> tuple[list[str], list[str], str]:
    """ffmpeg inputs/filters producing one pink-noise whoosh per transition time."""
    inputs, filt, labels = [], [], []
    for i, t in enumerate(times):
        inputs += ["-f", "lavfi", "-t", "0.6", "-i", "anoisesrc=d=0.6:c=pink:r=48000:a=0.6"]
        ms = int(max(0, t) * 1000)
        filt.append(f"[{{n{i}}}:a]highpass=f=500,lowpass=f=7000,afade=t=in:d=0.28,afade=t=out:st=0.28:d=0.3,"
                    f"volume=0.22,adelay={ms}|{ms},aformat=channel_layouts=stereo[w{i}]")
        labels.append(f"[w{i}]")
    return inputs, filt, "".join(labels)


# ------------------------------------------------------------------ short: native vertical chapters
SW, SH = 1080, 1920
FRAME_W, FRAME_H, FRAME_Y = 1000, 560, 720        # media window (centre y)


def make_background(path: Path) -> None:
    import numpy as np
    y = np.linspace(0, 1, SH)[:, None]
    base = np.array([10, 13, 28]) * (1 - y[..., None]) + np.array([20, 25, 52]) * y[..., None]
    rng = np.random.default_rng(7)
    arr = base.repeat(SW, axis=1) + rng.normal(0, 0.9, (SH, SW, 1))
    Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).save(path)


def make_frame_assets(out: Path) -> dict[str, Path]:
    r = 38
    mask = Image.new("L", (FRAME_W, FRAME_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, FRAME_W - 1, FRAME_H - 1), r, fill=255)
    ring = Image.new("RGBA", (FRAME_W, FRAME_H), (0, 0, 0, 0))
    ImageDraw.Draw(ring).rounded_rectangle((0, 0, FRAME_W - 1, FRAME_H - 1), r, outline=(163, 138, 245, 210), width=3)
    pad = 90
    shadow = Image.new("RGBA", (FRAME_W + 2 * pad, FRAME_H + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((pad, pad, pad + FRAME_W, pad + FRAME_H), r, fill=(0, 0, 0, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(34))
    paths = {"mask": out / "frame_mask.png", "ring": out / "frame_ring.png", "shadow": out / "frame_shadow.png"}
    mask.save(paths["mask"]); ring.save(paths["ring"]); shadow.save(paths["shadow"])
    return paths


def render_short_chapter(media: Path, dur: float, voice: Path, bg: Path, frame: dict[str, Path], out: Path) -> None:
    x0 = (SW - FRAME_W) // 2
    n = int(dur * FPS) + 5
    is_video = media.suffix.lower() in {".mp4", ".mov", ".webm"}
    media_in = (["-stream_loop", "-1", "-i", media] if is_video else ["-loop", "1", "-framerate", FPS, "-i", media])
    fy = f"{FRAME_Y - FRAME_H // 2}+10*sin(2*PI*t/3.5)"
    if is_video:
        fit = "scale=2200:1300:force_original_aspect_ratio=increase,crop=2200:1300"
    else:
        iw, ih = Image.open(media).size
        # very wide stills would lose their sides when cropped to the frame: letterbox them instead
        fit = ("scale=2200:-2,pad=2200:1300:(ow-iw)/2:(oh-ih)/2:color=0x10152a" if iw / ih > 2.0
               else "scale=2200:1300:force_original_aspect_ratio=increase,crop=2200:1300")
    fc = (
        f"[1:v]{fit},"
        f"zoompan=z='1+0.12*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={FRAME_W}x{FRAME_H}:fps={FPS},"
        f"format=yuv420p[m0];[m0][2:v]alphamerge[m1];"
        f"[0:v][3:v]overlay=x={x0 - 90}:y='{fy}-90+22':shortest=1[b0];"
        f"[b0][m1]overlay=x={x0}:y='{fy}':shortest=1[b1];"
        f"[b1][4:v]overlay=x={x0}:y='{fy}':shortest=1,format=yuv420p[v]"
    )
    run(["ffmpeg", "-loglevel", "error", "-y",
         "-loop", "1", "-framerate", FPS, "-t", f"{dur:.3f}", "-i", bg,
         *media_in,
         "-loop", "1", "-framerate", FPS, "-i", frame["mask"],
         "-loop", "1", "-framerate", FPS, "-i", frame["shadow"],
         "-loop", "1", "-framerate", FPS, "-i", frame["ring"],
         "-i", voice, "-filter_complex", fc, "-map", "[v]", "-map", "5:a", "-t", f"{dur:.3f}",
         *quality.intermediate_args(), "-c:a", "aac", "-b:a", "192k", "-ar", 48000, "-ac", 2, out])


def render_card(bg: Path | None, dur: float, w: int, h: int, out: Path, still: Path | None = None) -> None:
    """Silent outro card with stereo silence."""
    src = ["-loop", "1", "-framerate", FPS, "-t", f"{dur:.3f}", "-i", still or bg]
    run(["ffmpeg", "-loglevel", "error", "-y", *src, "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", f"scale={w}:{h}:{quality.SCALE_FLAGS},format=yuv420p", *quality.intermediate_args(),
         "-c:a", "aac", "-b:a", "192k", "-shortest", out])


# ------------------------------------------------------------------ build
def load(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    req = json.loads((REPO / manifest["request"]).read_text(encoding="utf-8"))
    asset_dir = REPO / manifest["asset_dir"]
    secs = []
    for rs, ms in zip(req["sections"], manifest["sections"]):
        secs.append({**rs, **ms,
                     "voice": asset_dir / ms["voice"],
                     "stills": [asset_dir / s for s in ms.get("stills", [])],
                     "media": asset_dir / ms["media"] if ms.get("media") else None})
    return manifest, req, secs


def timeline(durs: list[float]) -> tuple[list[float], float]:
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d - XF
    return starts, t + XF


def assemble(chapter_files: list[Path], ass_path: Path, out: Path, trans: list[str], w: int, h: int,
             durs: list[float]) -> None:
    n = len(chapter_files)
    starts, _ = timeline(durs)
    inputs, fc = [], []
    for p in chapter_files:
        inputs += ["-i", p]
    cv, ca, acc = "0:v", "0:a", 0.0
    for k in range(1, n):
        acc += durs[k - 1] - XF
        fc.append(f"[{cv}][{k}:v]xfade=transition={trans[(k - 1) % len(trans)]}:duration={XF}:offset={acc:.3f}[v{k}]")
        fc.append(f"[{ca}][{k}:a]acrossfade=d={XF}[a{k}]")
        cv, ca = f"v{k}", f"a{k}"
    # whoosh on every transition (centred on the crossfade)
    w_in, w_f, w_lab = whoosh_inputs([starts[k] - 0.1 for k in range(1, n)])
    base = n
    w_f = [f.replace(f"{{n{i}}}", str(base + i)) for i, f in enumerate(w_f)]
    fc += w_f
    fc.append(f"[{ca}]aformat=channel_layouts=stereo[vo]")
    fc.append(f"[vo]{w_lab}amix=inputs={n}:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    fc.append(f"[{cv}]ass=filename={ass_path},noise=alls={2 if h > w else 3}:allf=u:all_seed=77,format=yuv420p[vout]")
    run(["ffmpeg", "-loglevel", "error", "-y", *inputs, *w_in, "-filter_complex", ";".join(fc), "-map", "[vout]",
         "-map", "[aout]", *quality.x264_args(threads=2), "-c:a", "aac", "-b:a", "192k", "-ar", 48000,
         "-movflags", "+faststart", out])


def build_short(manifest, secs, work: Path, out: Path) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    bg = work / "bg_short.png"; make_background(bg)
    frame = make_frame_assets(work)
    chapters, durs, voices = [], [], []
    for i, sec in enumerate(secs):
        v = work / f"voice{i}.wav"
        d = prepare_voice(sec["voice"], v)
        media = sec["media"] or sec["stills"][0]
        ch = work / f"short_c{i}.mp4"
        if not ch.exists():
            render_short_chapter(media, d, v, bg, frame, ch)
        chapters.append(ch); durs.append(d); voices.append(v)
    outro = work / "short_outro.mp4"
    if not outro.exists():
        render_card(bg, OUTRO_S, SW, SH, outro)
    chapters.append(outro); durs.append(probe(outro))
    starts, total = timeline(durs)

    ass = Ass(SW, SH)
    ass.add(0, total, "Shape", r"{\an7\pos(0,0)\1c&H%s&\t(0,%d,\fscx100)\fscx1\p1}m 0 0 l 1080 0 l 1080 12 l 0 12" % (ACCENT_BGR, int(total * 1000)), layer=6)
    orbs(ass, total, [(160, 360, 380, ACCENT_BGR), (940, 1150, 420, "C8B04A"), (300, 1650, 360, "B05AE0")])
    n = len(secs)
    for i, sec in enumerate(secs):
        s = starts[i]
        iv = speech_intervals(voices[i], durs[i])
        words = word_times(sec["narration"], iv)
        speech_end = iv[-1][1]
        # header: chip + title pop + underline sweep
        ass.add(s + 0.1, s + durs[i] - 0.3, "Chip",
                r"{\an5\pos(540,205)\fscx70\fscy70\alpha&HFF&\t(0,260,\fscx100\fscy100\alpha&H00&)}" + f"FERRAMENTA {i + 1}/{n}", 4)
        ass.add(s + 0.2, s + durs[i] - 0.3, "Title",
                r"{\an5\move(540,372,540,342,0,420)\blur6\alpha&HFF&\t(0,420,\blur0\alpha&H00&)}" + esc(sec["title"]), 4)
        ass.add(s + 0.45, s + 3.2, "Shape",
                r"{\an7\pos(180,415)\1c&H%s&\fscx1\t(0,700,\fscx100)\fad(0,500)\p1}m 0 0 l 720 0 l 720 6 l 0 6" % ACCENT_BGR, 4)
        # staggered topic pills, timed across the narration
        for bi, bullet in enumerate(sec.get("bullets", [])):
            t0 = s + max(0.8, speech_end * (0.22 + 0.22 * bi))
            y = 1100 + bi * 105
            ass.add(t0, s + durs[i] - 0.25, "Pill",
                    (r"{\an5\move(%d,%d,540,%d,0,260)\alpha&HFF&\t(0,260,\alpha&H00&)\fscx90\fscy90\t(0,260,\fscx100\fscy100)}" % (880, y, y))
                    + r"{\1c&H%s&}+{\1c&HFFFFFF&} " % ACCENT_BGR + esc(bullet), 5)
        ass.karaoke(s, caption_chunks(words, 4, 22), "Cap", (540, 1500))
    o = starts[-1]
    t1, t2 = manifest["outro"]["title"]
    ass.add(o + 0.1, o + OUTRO_S, "Big", r"{\an5\pos(540,820)\fscx60\fscy60\alpha&HFF&\t(0,350,\fscx100\fscy100\alpha&H00&)}" + esc(t1), 5)
    ass.add(o + 0.2, o + OUTRO_S, "Big", r"{\an5\pos(540,950)\fscx60\fscy60\alpha&HFF&\t(0,350,\fscx100\fscy100\alpha&H00&)}" + esc(t2), 5)
    ass.add(o + 0.55, o + OUTRO_S, "Sub", r"{\an5\pos(540,1085)\alpha&HFF&\t(0,400,\alpha&H00&)}" + r"\N".join(esc(x) for x in manifest["outro"]["subtitle"]), 5)
    ass.add(o + 0.9, o + OUTRO_S, "Handle", r"{\an5\pos(540,1260)\fscx70\fscy70\alpha&HFF&\t(0,350,\fscx100\fscy100\alpha&H00&)}" + esc(manifest["handle"]), 5)

    styles = (style("Cap", 84, primary=ACCENT_BGR, secondary="FFFFFF", outline="000000", outline_w=6, outline_alpha="64", margin_lr=60)
              + style("Chip", 36, primary="FFFFFF", border=3, outline_w=16, outline=ACCENT_BGR, spacing=4)
              + style("Title", 124)
              + style("Pill", 54, border=3, outline_w=20, outline="30201A", outline_alpha="55", bold=1)
              + style("Big", 124) + style("Sub", 52, primary="DDDAFA", bold=0)
              + style("Handle", 80, primary=ACCENT_BGR) + style("Shape", 20, align=7))
    ass_path = work / "short.ass"
    ass_path.write_text(ass.render(styles), encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    final = out / "short_9x16.mp4"
    assemble(chapters, ass_path, final, ["slideleft", "wipeleft", "slideleft", "fadeblack"], SW, SH, durs)
    return final


def build_video(manifest, secs, work: Path, out: Path) -> Path:
    from . import animated_slides as A
    work.mkdir(parents=True, exist_ok=True)
    W, H = FORMATS["video"]
    chapters, durs, voices = [], [], []
    for i, sec in enumerate(secs):
        v = work / f"voice{i}.wav"
        d = prepare_voice(sec["voice"], v)
        folder = work / f"video_c{i}"; folder.mkdir(exist_ok=True)
        ch = folder / "chapter.mp4"
        if not ch.exists():
            section = {k: sec[k] for k in ("title", "narration", "repo_url") if k in sec}
            if sec.get("note"):
                section["note"] = sec["note"]
            A.render_animated_section(section, i + 1, len(secs), v, d, folder,
                                      screenshots=[str(p) for p in sec["stills"]],
                                      media=[{"path": str(sec["media"])}] if sec["media"] else [])
        chapters.append(ch); durs.append(d); voices.append(v)
    oim, od = A._canvas((W * 2, H * 2))
    A._header(od, "Salve este vídeo", len(secs), len(secs), (W * 2, H * 2))
    still = work / "video_outro.png"; oim.save(still)
    outro = work / "video_outro.mp4"
    if not outro.exists():
        render_card(None, OUTRO_S, W, H, outro, still=still)
    chapters.append(outro); durs.append(probe(outro))
    starts, total = timeline(durs)

    ass = Ass(W, H)
    ass.add(0, total, "Shape", r"{\an7\pos(0,0)\1c&H%s&\fscx1\t(0,%d,\fscx100)\p1}m 0 0 l 1920 0 l 1920 9 l 0 9" % (ACCENT_BGR, int(total * 1000)), layer=6)
    for i, sec in enumerate(secs):
        s = starts[i]
        ass.add(s + (0.9 if i == 0 else 0.15), s + 2.55, "Shape",
                r"{\an7\pos(90,243)\1c&H%s&\fscx1\t(0,650,\fscx100)\fad(0,500)\p1}m 0 0 l 1740 0 l 1740 5 l 0 5" % ACCENT_BGR, 5)
        ass.add(s + (0.9 if i == 0 else 0.15), s + 2.55, "Chip",
                r"{\an9\pos(1830,150)\fscx60\fscy60\alpha&HFF&\t(0,260,\fscx100\fscy100\alpha&H00&)\fad(0,400)}" + f"FERRAMENTA {i + 1}/{len(secs)}", 5)
        iv = speech_intervals(voices[i], durs[i])
        ass.karaoke(s, caption_chunks(word_times(sec["narration"], iv), 4, 30), "Cap", (960, 1030))
    o = starts[-1]
    t1, t2 = manifest["outro"]["title"]
    ass.add(o + 0.1, o + OUTRO_S, "Big", r"{\an5\pos(960,430)\fscx60\fscy60\alpha&HFF&\t(0,350,\fscx100\fscy100\alpha&H00&)}" + esc(f"{t1} {t2}"), 5)
    ass.add(o + 0.45, o + OUTRO_S, "Sub", r"{\an5\pos(960,610)\alpha&HFF&\t(0,400,\alpha&H00&)}" + esc(" ".join(manifest["outro"]["subtitle"])), 5)
    ass.add(o + 0.8, o + OUTRO_S, "Handle", r"{\an5\pos(960,740)\fscx70\fscy70\alpha&HFF&\t(0,350,\fscx100\fscy100\alpha&H00&)}" + esc(manifest["handle"]), 5)
    styles = (style("Cap", 64, primary=ACCENT_BGR, secondary="FFFFFF", outline_w=5, outline_alpha="64", margin_lr=10)
              + style("Chip", 26, border=1, primary=ACCENT_BGR, spacing=3, align=9)
              + style("Big", 110) + style("Sub", 46, primary="DDDAFA", bold=0)
              + style("Handle", 70, primary=ACCENT_BGR) + style("Shape", 20, align=7))
    ass_path = work / "video.ass"
    ass_path.write_text(ass.render(styles), encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    final = out / "video_16x9.mp4"
    assemble(chapters, ass_path, final, ["slideleft", "wipeleft", "slideleft", "fadeblack"], W, H, durs)
    return final


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--format", choices=["short", "video", "both"], default="both")
    ap.add_argument("--out", type=Path, default=REPO / "outputs" / "promo")
    ap.add_argument("--work", type=Path, default=None, help="cache dir (default: <out>/_work)")
    args = ap.parse_args(argv)
    manifest, _req, secs = load(args.manifest if args.manifest.is_absolute() else REPO / args.manifest)
    work = args.work or args.out / "_work"
    for fmt in (["short", "video"] if args.format == "both" else [args.format]):
        final = (build_short if fmt == "short" else build_video)(manifest, secs, work, args.out)
        print(f"{fmt}: {final} ({probe(final):.1f}s, {final.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
