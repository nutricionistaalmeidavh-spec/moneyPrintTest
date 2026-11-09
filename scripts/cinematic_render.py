"""Cinematic MoneyPrint editor: browser footage + licensed b-roll + verified news.

A dedicated FFmpeg path preserves legacy MPT modes. The supplied reference
video is never read or reused: all scenes are newly captured or sourced.
"""
from __future__ import annotations

import json
import math
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.ai_director import (
    fetch_news_headline, official_repo_gif, official_repo_image, plan_with_local_ai, suggest_broll_query,
)
from scripts.browser_capture import capture_repositories
from scripts.commons_media import find_free_videos

WIDTH, HEIGHT, FPS = 1920, 1080, 24
DARK = (10, 14, 30)
PURPLE = (125, 101, 215)
FONT_PATHS = {
    "light": ["/usr/share/fonts/truetype/lato/Lato-Light.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "regular": ["/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "medium": ["/usr/share/fonts/truetype/lato/Lato-Medium.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "semibold": ["/usr/share/fonts/truetype/lato/Lato-Semibold.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
}


def font(weight: str, size: int):
    for source in FONT_PATHS[weight]:
        if Path(source).is_file():
            return ImageFont.truetype(source, size)
    raise RuntimeError("Fontes livres Lato/DejaVu ausentes")


def run_ffmpeg(args: list[str], *, timeout=1800):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                    "-nostdin", "-y", *args], check=True, timeout=timeout)


def media_duration(path: Path) -> float:
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
        str(path)], text=True, timeout=30)
    return float(raw.strip())


def wrap_text(draw, text: str, face, max_width: int, max_lines: int) -> list[str]:
    lines = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=face)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(lines)) < len(text) * 0.83:
        lines[-1] = lines[-1].rstrip(" .") + "…"
    return lines


def make_cover(target: Path, title: str) -> None:
    """Soft, dark cosmic canvas; typography stays restrained and legible."""
    random.seed(43)
    canvas = Image.new("RGB", (WIDTH, HEIGHT))
    pix = canvas.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Subtle indigo nebula, not neon.
            glow = math.exp(-((x-WIDTH*.56)**2/(WIDTH*.56)**2
                              + (y-HEIGHT*.46)**2/(HEIGHT*.55)**2)*5)
            pix[x, y] = (int(10+24*glow), int(13+10*glow), int(32+49*glow))
    draw = ImageDraw.Draw(canvas)
    for _ in range(185):
        x, y = random.randrange(WIDTH), random.randrange(HEIGHT)
        shade = random.randrange(65, 148)
        draw.ellipse((x, y, x+2, y+2), fill=(shade, shade, min(255, shade+35)))
    draw.text((140, 324), "ARTISYS   /   OPEN SOURCE",
              font=font("medium", 33), fill=(173, 158, 228))
    lines = wrap_text(draw, title, font("light", 101), 1600, 2)
    for i, line in enumerate(lines):
        draw.text((140, 428+i*120), line,
                  font=font("light", 101), fill=(243, 243, 249))
    draw.line((140, 746, 500, 746), fill=PURPLE, width=3)
    draw.text((140, 796), "Tecnologia real. Aplicações práticas.",
              font=font("regular", 36), fill=(172, 177, 199))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def lower_third(target: Path, title: str, index: int, total: int) -> None:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(HEIGHT-210, HEIGHT):
        opacity = int(148 * (y-(HEIGHT-210)) / 210)
        for x in range(WIDTH):
            pixels[x, y] = (7, 11, 22, opacity)
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((88, 892, 95, 975), radius=3, fill=(169, 148, 228, 222))
    draw.text((120, 903), title, font=font("semibold", 54), fill=(245, 245, 251, 250))
    target.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(target)


def make_news_card(target: Path, news: dict) -> None:
    canvas = Image.new("RGB", (WIDTH, HEIGHT), (14, 18, 32))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((120, 155, 1800, 915), radius=32,
                           fill=(25, 28, 45), outline=(56, 54, 84), width=2)
    draw.text((194, 233), "NOTÍCIA VERIFICADA",
              font=font("semibold", 32), fill=(169, 151, 225))
    draw.line((194, 313, 1730, 313), fill=(65, 64, 90), width=2)
    headline = news["headline"]
    for size in (76, 68, 61, 54):
        face = font("light", size)
        lines = wrap_text(draw, headline, face, 1450, 4)
        if len(" ".join(lines)) >= len(headline) * .85:
            break
    for index, line in enumerate(lines):
        draw.text((194, 382+index*(size+18)), line, font=face, fill=(247, 247, 250))
    draw.text((197, 830),
              f"{news['publisher']}  ·  {news['published_at'][:10]}",
              font=font("regular", 29), fill=(178, 182, 202))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


def prepare_shots(plan: list[dict], approved: dict[str, Path], duration: float) -> list[tuple[Path, float]]:
    if duration <= 0:
        raise ValueError("Narração sem áudio")
    valid = [shot for shot in plan if shot["asset_id"] in approved
             and approved[shot["asset_id"]].is_file()]
    if not valid:
        raise RuntimeError("Nenhum take disponível")
    result = []
    remaining = duration
    idx = 0
    while remaining > .025:
        shot = valid[idx % len(valid)]
        seconds = min(float(shot["seconds"]), remaining)
        result.append((approved[shot["asset_id"]], seconds))
        remaining -= seconds
        idx += 1
    return result


def render_section(section: dict, shots: list[tuple[Path, float]], overlay: Path,
                   narration: Path, target: Path, duration: float) -> None:
    inputs = []
    filters = []
    for i, (media, seconds) in enumerate(shots):
        if media.suffix.lower() in (".png", ".jpg", ".jpeg"):
            inputs += ["-loop", "1", "-framerate", str(FPS), "-i", str(media)]
            vf = (f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                  f"crop={WIDTH}:{HEIGHT},zoompan=z='min(zoom+0.0006,1.065)':"
                  f"d=1:s={WIDTH}x{HEIGHT}:fps={FPS},")
        else:
            inputs += ["-stream_loop", "-1", "-i", str(media)]
            vf = (f"[{i}:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                  f"crop={WIDTH}:{HEIGHT},fps={FPS},")
        vf += (f"trim=duration={seconds:.5f},setpts=PTS-STARTPTS,"
               f"format=yuv420p[v{i}]")
        filters.append(vf)
    oidx = len(shots)
    inputs += ["-loop", "1", "-i", str(overlay), "-i", str(narration)]
    joined = "".join(f"[v{i}]" for i in range(len(shots)))
    filters.append(f"{joined}concat=n={len(shots)}:v=1:a=0[scenes]")
    filters.append(f"[scenes][{oidx}:v]overlay=0:0:format=auto:enable=\'between(t,0.25,3.4)\',"

                   "format=yuv420p[finished]")
    run_ffmpeg([
        *inputs, "-filter_complex", ";".join(filters),
        "-map", "[finished]", "-map", f"{oidx+1}:a:0",
        "-t", f"{duration:.4f}", "-r", str(FPS), "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-threads", "2", "-c:a", "aac", "-b:a", "144k",
        "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(target)
    ], timeout=1800)
    if not target.is_file() or target.stat().st_size < 8192:
        raise RuntimeError("FFmpeg não produziu seção válida")


def estimate_subtitles(narration: str, offset: float, duration: float) -> list[dict]:
    """Editable subtitle cues; timings are estimates, not Whisper alignments."""
    words = narration.replace("\n", " ").split()
    chunks = [" ".join(words[i:i+10]) for i in range(0, len(words), 10)]
    total = max(1, sum(len(chunk.split()) for chunk in chunks))
    elapsed = 0
    cues = []
    for chunk in chunks:
        span = duration * len(chunk.split()) / total
        cues.append({"start": round(offset+elapsed, 3),
                     "end": round(offset+elapsed+span, 3), "text": chunk})
        elapsed += span
    return cues


def write_srt(path: Path, cues: list[dict]) -> None:
    def timecode(seconds):
        ms = max(0, round(seconds*1000))
        hours, rem = divmod(ms, 3600000)
        minutes, rem = divmod(rem, 60000)
        sec, millis = divmod(rem, 1000)
        return f"{hours:02d}:{minutes:02d}:{sec:02d},{millis:03d}"
    with path.open("w", encoding="utf-8") as out:
        for i, cue in enumerate(cues, 1):
            out.write(f"{i}\n{timecode(cue['start'])} --> {timecode(cue['end'])}\n"
                      f"{cue['text']}\n\n")


def render_cinematic(request: dict, dest: Path, runtime: Path, env: dict) -> dict:
    """Run a new eight-section documentary; never read the example MOV."""
    from scripts.render_request import download_piper, start_ollama
    from scripts.commons_media import source_credits

    dest.mkdir(parents=True, exist_ok=True)
    sections = request["sections"]
    repos = request["repo_urls"]
    plan_seconds = request["duration_seconds"]
    cover = dest / "opening.png"
    use_old_cover = not request.get("motion", {}).get("universe_seconds", 0)
    if use_old_cover:
        make_cover(cover, request["topic"])

    # Capture websites afresh; files are captured by Chromium on runner, not user phone.
    browser = capture_repositories(repos, plan_seconds, dest / "browser", focus_readme=True)
    if len(browser) != len(repos):
        raise RuntimeError("Nem todos os repositórios foram gravados")

    llm_started = False
    llm_available = False
    try:
        try:
            llm_started = start_ollama()
            llm_available = True
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f"Aviso: diretor Ollama indisponível ({type(exc).__name__}), usando edição determinística", flush=True)

        piper_voice = download_piper(runtime / "piper-model")
        clips = []
        cues = []
        credit_lines = ["ArtiSys — créditos e proveniência do novo vídeo",
                        "Capturas das páginas públicas do GitHub feitas por Chromium/Playwright.", ""]
        media_records = []
        shot_report = []
        elapsed = 0.0
        for idx, section in enumerate(sections):
            n = idx + 1
            folder = dest / f"secao_{n:02d}"
            folder.mkdir(exist_ok=True)
            voice = folder / "narracao.wav"
            subprocess.run(
                ["piper", "--model", str(piper_voice), "--output_file", str(voice)],
                input=section["narration"], text=True, check=True,
                capture_output=True, timeout=150)
            audio_seconds = media_duration(voice)
            if audio_seconds < 2:
                raise RuntimeError(f"Narração vazia da seção {n}")
            assets = [{"id": f"repo_{n}", "kind": "github", "path": browser[idx]}]
            credit_lines.append(f"{n:02d}. Captura oficial: {section['repo_url']}")

            if idx == 0 and use_old_cover:
                assets.append({"id": "opening", "kind": "motion_title",
                               "path": str(cover.resolve())})

            # Optional user footage is never classified as invalid by subject:
            # only file existence, path containment and codec handling matter.
            for k, supplied in enumerate(request.get("media_clips", []), 1):
                if supplied["repo_index"] != n:
                    continue
                root = (Path.cwd() / "assets").resolve()
                candidate = (Path.cwd() / supplied["path"]).resolve()
                if not candidate.is_relative_to(root) or not candidate.is_file():
                    continue
                if candidate.suffix.lower() == ".gif":
                    converted = folder / f"extra_{k:02d}.mp4"
                    run_ffmpeg([
                        "-stream_loop", "-1", "-i", str(candidate), "-t", "12",
                        "-an", "-vf", "fps=24,scale=1280:720:"
                                     "force_original_aspect_ratio=decrease,"
                                     "pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
                        "-pix_fmt", "yuv420p", str(converted)], timeout=160)
                    candidate = converted
                assets.append({"id": f"own_{n}_{k}", "kind": "user_video",
                               "path": str(candidate)})
                credit_lines.append(f"     Vídeo fornecido: {supplied['path']}")

            screenshot = official_repo_image(section["repo_url"], folder / "screenshot")
            if screenshot:
                assets.append({"id": f"image_{n}", "kind": "official_screenshot",
                               "path": screenshot})
                credit_lines.append(f"     Imagem do README: {section['repo_url']}")

            gif_file = official_repo_gif(section["repo_url"], folder / "demo")
            if gif_file:
                assets.append({"id": f"demo_{n}", "kind": "official_gif",
                               "path": gif_file})
                credit_lines.append(f"     GIF do README oficial: {section['repo_url']}")

            query, search_source = (suggest_broll_query(section)
                                    if llm_available else
                                    (section.get("broll_query") or "working on laptop", "fallback"))
            try:
                clips_found, credits = find_free_videos(
                    [query], folder / "broll", max_results=1)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                print(f"Aviso: sem b-roll da seção {n}: {type(exc).__name__}", flush=True)
                clips_found, credits = [], []
            for p, item in zip(clips_found, credits):
                assets.append({"id": f"broll_{n}", "kind": "context_broll",
                               "path": p})
                media_records.append({"repo": section["repo_url"],
                                      "kind": "broll", "source": item})
                credit_lines.append(source_credits([item]))

            news = (fetch_news_headline(section["repo_url"])
                    if request.get("include_verified_news", False) else None)
            if news:
                card = folder / "news_verified.png"
                make_news_card(card, news)
                assets.append({"id": f"news_{n}", "kind": "verified_news_card",
                               "path": str(card.resolve())})
                media_records.append({"repo": section["repo_url"],
                                      "kind": "news", "source": news})
                credit_lines.append(f"     Notícia: {news['headline']} | "
                                    f"{news['publisher']} | {news['published_at']} | {news['url']}")

            if llm_available:
                plan, director_source = plan_with_local_ai(section, assets)
            else:
                from scripts.ai_director import build_fallback_plan
                plan = build_fallback_plan([a["id"] for a in assets],
                                           [a["id"] for a in assets[1:]])
                director_source = "fallback:no_ollama"

            if idx == 0 and use_old_cover:
                # Intro takes 3 seconds, without reusing a frame from the reference.
                plan = [{"asset_id": "opening", "seconds": 3}] + plan
            overlay = folder / "lower_third.png"
            lower_third(overlay, section["title"], n, len(sections))
            approved = {a["id"]: Path(a["path"]) for a in assets}
            shots = prepare_shots(plan, approved, audio_seconds+.12)
            output = folder / "chapter.mp4"
            render_section(section, shots, overlay, voice, output, audio_seconds+.12)
            clips.append(output)
            cues.extend(estimate_subtitles(section["narration"], elapsed, audio_seconds))
            elapsed += media_duration(output)
            shot_report.append({
                "section": n, "title": section["title"], "duration": audio_seconds,
                "director": director_source, "broll_search": query,
                "search_source": search_source, "assets": [
                    {"id": a["id"], "type": a["kind"]} for a in assets],
                "shots": [{"asset": p.name, "seconds": round(t, 2)} for p, t in shots],
            })
            print(f"Seção {n}/{len(sections)}: {section['title']} "
                  f"({audio_seconds:.1f}s, {director_source})", flush=True)

        concat_file = dest / "chapter_list.txt"
        concat_file.write_text("".join(
            f"file '{p.resolve()}'\n" for p in clips), encoding="utf-8")
        target = dest / "video_1.mp4"
        run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_file),
                    "-c", "copy", "-movflags", "+faststart", str(target)], timeout=600)
        write_srt(dest / "legendas_estimadas.srt", cues)
        (dest / "creditos.txt").write_text("\n".join(credit_lines), encoding="utf-8")
        (dest / "licencas_midia.json").write_text(
            json.dumps(media_records, ensure_ascii=False, indent=2), encoding="utf-8")
        (dest / "direcao_ia.json").write_text(
            json.dumps(shot_report, ensure_ascii=False, indent=2), encoding="utf-8")
        (dest / "roteiro.txt").write_text(
            "\n\n".join(sec["narration"] for sec in sections), encoding="utf-8")
        report = {"status": "success", "topic": request["topic"],
                  "visual_source": "chromium_playwright+commons+official_demo+verified_news",
                  "director": "ollama_local" if llm_available else "deterministic_fallback",
                  "output": str(target), "duration_seconds": media_duration(target),
                  "reference_video_used": False, "sections": len(sections),
                  "subtitle_note": "SRT com tempos estimados; revisão recomendada"}
        (dest / "resultado.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        if llm_started:
            subprocess.run(["docker", "stop", "moneyprint-ollama"],
                           check=False, capture_output=True, timeout=30)
