"""MoneyPrint: extract meaningful vertical Shorts from a finished narrated MP4.
Free self-hosted core: Python, FFmpeg, faster-whisper. No TTS, no paid APIs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

THEMES = (
    ("Seu site esta seguro?", ("site", "seguro", "pentest", "seguranca")),
    ("Pentest com ferramentas gratuitas", ("gratis", "gratuito", "ferramenta", "open source", "abert")),
    ("Como detectar vulnerabilidades", ("vulnerabilidade", "nuclei", "scanner", "zap", "sqlmap", "risco")),
    ("O que um pentest realmente faz", ("autoriz", "escopo", "valid", "reconhec", "teste")),
    ("Da analise ao relatorio", ("relatorio", "corrigir", "correcao", "prioriz", "resultado")),
)

def probe(path: Path) -> dict:
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ], text=True))
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    audios = [s for s in data["streams"] if s["codec_type"] == "audio"]
    if len(videos) != 1 or not audios:
        raise ValueError("Fonte precisa conter exatamente um video e pelo menos uma faixa de audio")
    return {"duration": float(data["format"]["duration"]), "width": int(videos[0]["width"]),
            "height": int(videos[0]["height"]), "audio": True, "video": True}

def transcribe(source: Path, model_name: str) -> list[dict]:
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    pieces, _ = model.transcribe(str(source), language="pt", beam_size=5,
                                 vad_filter=True, word_timestamps=True,
                                 initial_prompt="Pentest, OWASP ZAP, Nuclei, SQLmap, httpx, Katana, Subfinder, segurança web.")
    return [{"start": float(s.start), "end": float(s.end), "text": s.text.strip(),
             "words": [{"start": float(w.start), "end": float(w.end), "word": w.word}
                       for w in (s.words or []) if w.start is not None and w.end is not None]}
            for s in pieces if s.text.strip()]

def validate_segments(rows: list, duration: float) -> list[dict]:
    clean = []
    last = -0.01
    for r in rows:
        start, end = float(r["start"]), float(r["end"])
        if not (math.isfinite(start) and math.isfinite(end) and last <= start < end <= duration + 0.25):
            raise ValueError("Segmentos da transcricao fora de ordem ou fora do video")
        text = str(r["text"]).strip()
        if text:
            clean.append({"start": start, "end": min(end, duration), "text": text,
                          "words": r.get("words", [])})
        last = start
    if not clean:
        raise ValueError("Transcricao sem voz; nao produzir cortes mudos")
    return clean

def _normalize(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))

def make_candidates(segs: list[dict], minimum: float, maximum: float) -> list[dict]:
    results = []
    for i, first in enumerate(segs):
        for j in range(i, len(segs)):
            last = segs[j]
            duration = last["end"] - first["start"]
            if duration > maximum + 0.01:
                break
            if duration < minimum:
                continue
            selected = segs[i:j+1]
            if any(b["start"] - a["end"] > 2.0 for a, b in zip(selected, selected[1:])):
                continue
            text = " ".join(r["text"] for r in selected)
            normalized = _normalize(text)
            theme_scores = [sum(3 if word in normalized else 0 for word in terms)
                            for _, terms in THEMES]
            speech = sum(min(1, len(s["text"].split()) / 6) for s in selected)
            start_bonus = 2 if i == 0 or re.search(r"[.!?]$", segs[i-1]["text"]) else 0
            end_bonus = 3 if re.search(r"[.!?]$", last["text"]) else 0
            duration_bonus = max(0, 3 - abs(duration - 38) / 8)
            results.append({"start": first["start"], "end": last["end"], "i": i, "j": j,
                            "text": text, "theme_scores": theme_scores,
                            "quality": speech / max(1, len(selected)) + start_bonus + end_bonus + duration_bonus})
    return results

def choose_clips(segs: list[dict], count: int, minimum: float = 25, maximum: float = 55) -> list[dict]:
    if not 1 <= count <= 12 or not 5 <= minimum < maximum <= 180:
        raise ValueError("Parametros de clipes invalidos")
    candidates = make_candidates(segs, minimum, maximum)
    chosen: list[dict] = []
    used_themes = set()
    for _ in range(count):
        choices = []
        for c in candidates:
            if any(max(0, min(c["end"], p["end"]) - max(c["start"], p["start"])) > 0.25
                   for p in chosen):
                continue
            free = [k for k in range(len(THEMES)) if k not in used_themes]
            if not free:
                free = list(range(len(THEMES)))
            theme = max(free, key=lambda k: (c["theme_scores"][k], -k))
            score = c["quality"] + c["theme_scores"][theme] - (2 if c["theme_scores"][theme] == 0 else 0)
            choices.append((score, -abs((c["end"]-c["start"]) - 38), -c["start"], theme, c))
        if not choices:
            break
        _, _, _, theme, winner = max(choices, key=lambda item: item[:3])
        used_themes.add(theme)
        chosen.append({**winner, "title": THEMES[theme][0], "theme": theme})
    return sorted(chosen, key=lambda c: c["start"])

def _ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")

def _time(t: float) -> str:
    hundredths = round(max(0, t) * 100)
    return f"{hundredths // 360000}:{hundredths // 6000 % 60:02}:{hundredths // 100 % 60:02}.{hundredths % 100:02}"

def write_captions(path: Path, selected: list[dict], offset: float, length: float) -> None:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,61,&H00FFFFFF,&H00FFFFFF,&H00301911,&H90000000,-1,0,0,0,100,100,0,0,1,5,1,2,75,75,420,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for seg in selected:
        words = [w for w in seg.get("words", []) if offset <= float(w["start"]) <= offset + length]
        if not words:
            tokens = seg["text"].split()
            step = max(.1, (seg["end"] - seg["start"]) / max(1, len(tokens)))
            words = [{"word": w, "start": seg["start"] + i*step,
                      "end": min(seg["end"], seg["start"] + (i+1)*step)} for i, w in enumerate(tokens)]
        group = []
        for word in words:
            if group and (len(group) >= 5 or float(word["end"]) - float(group[0]["start"]) > 2.0):
                text = _ass_escape(" ".join(str(x["word"]).strip() for x in group))
                a = max(0, float(group[0]["start"]) - offset)
                b = min(length, float(group[-1]["end"]) - offset)
                if b > a: events.append(f"Dialogue: 0,{_time(a)},{_time(b)},Default,,0,0,0,,{text}")
                group = []
            group.append(word)
        if group:
            text = _ass_escape(" ".join(str(x["word"]).strip() for x in group))
            a = max(0, float(group[0]["start"]) - offset)
            b = min(length, float(group[-1]["end"]) - offset)
            if b > a: events.append(f"Dialogue: 0,{_time(a)},{_time(b)},Default,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")

def _ffpath(path: Path) -> str:
    return path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

def render_clip(source: Path, out: Path, selected: list[dict], clip: dict, captions: bool = True) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    start, end = clip["start"], clip["end"]
    title = re.sub(r"[^a-zA-Z0-9 ?!\-\n]", "", clip["title"])
    title_path = out.with_suffix(".title.txt")
    title_path.write_text(title, encoding="utf-8")
    ass_path = out.with_suffix(".ass")
    if captions:
        write_captions(ass_path, selected, start, end - start)
    graph = (
        "[0:v]fps=30,split=2[bg0][main0];"
        "[bg0]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "boxblur=28:3,eq=brightness=-0.14[bg];"
        "[main0]scale=1020:1020:force_original_aspect_ratio=decrease[main];"
        "[bg][main]overlay=x=(W-w)/2:y=(H-h)/2-140:shortest=1,"
        "drawbox=x=0:y=0:w=1080:h=150:color=black@0.46:t=fill,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"textfile='{_ffpath(title_path)}':fontcolor=white:fontsize=52:x=(w-text_w)/2:y=240,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "text='ArtiSys  /  CYBERSECURITY':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=80"
    )
    graph += f",ass='{_ffpath(ass_path)}'" if captions else ""
    graph += ",format=yuv420p[v]"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-ss", f"{start:.3f}",
           "-i", str(source), "-t", f"{end-start:.3f}", "-filter_complex", graph,
           "-map", "[v]", "-map", "0:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    info = probe(out)
    if (info["width"], info["height"]) != (1080, 1920) or abs(info["duration"] - (end-start)) > 0.4:
        raise ValueError("QA falhou: 9:16, audio ou duracao incorretos")
    return info

def main() -> None:
    parser = argparse.ArgumentParser(description="MoneyPrint: cortes reais de um MP4 existente em 9:16")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--min-duration", type=float, default=25)
    parser.add_argument("--max-duration", type=float, default=55)
    parser.add_argument("--model", default="small")
    parser.add_argument("--transcript-json", type=Path, help="Transcricao existente com start/end/text/words")
    parser.add_argument("--no-captions", action="store_true")
    args = parser.parse_args()
    for command in ("ffmpeg", "ffprobe"):
        if not shutil.which(command): parser.error(f"{command} ausente")
    if not args.input.is_file(): parser.error("MP4 original nao encontrado")
    info = probe(args.input)
    if not 40 <= info["duration"] <= 7200: parser.error("Video fora do intervalo esperado")
    segments = (json.loads(args.transcript_json.read_text(encoding="utf-8"))
                if args.transcript_json else transcribe(args.input, args.model))
    segments = validate_segments(segments, info["duration"])
    clips = choose_clips(segments, args.count, args.min_duration, args.max_duration)
    if not clips: raise RuntimeError("Nao foram identificados trechos com fala continua")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, clip in enumerate(clips, 1):
        name = f"Pentest_V3_Short_{idx:02d}_9x16.mp4"
        path = args.output_dir / name
        render = render_clip(args.input, path, segments[clip["i"]:clip["j"]+1], clip,
                             captions=not args.no_captions)
        results.append({"file": name, "title": clip["title"], "source_start": clip["start"],
                        "source_end": clip["end"], "seconds": render["duration"],
                        "width": render["width"], "height": render["height"], "audio": True})
    manifest = {"source_file": args.input.name, "source_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
                "source_duration": info["duration"], "engine": "FFmpeg + faster-whisper local",
                "auto_publish": False, "paid_services": False, "clips": results}
    (args.output_dir/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
