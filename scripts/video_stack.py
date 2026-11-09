#!/usr/bin/env python3
"""MoneyPrint local editor: deterministic hard cuts, scene indexing and opt-in adapters."""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
ALLOWED_VIDEO = {".mp4", ".mov", ".webm", ".mkv", ".gif"}
ASSET_PATTERN = re.compile(r"assets/[A-Za-z0-9_.\-/]{1,170}\Z")


class VideoStackError(ValueError):
    pass


def safe_asset(raw: str, asset_root: Path) -> Path:
    """Only allow media from the versioned repository assets directory."""
    if (not isinstance(raw, str) or not ASSET_PATTERN.fullmatch(raw)
            or ".." in Path(raw).parts or Path(raw).suffix.lower() not in ALLOWED_VIDEO):
        raise VideoStackError("Vídeo deve ser arquivo local dentro de assets/")
    root = asset_root.resolve()
    candidate = (root / Path(raw).relative_to("assets")).resolve()
    if not candidate.is_relative_to(root):
        raise VideoStackError("Caminho de mídia fora de assets/")
    return candidate


def normalize_motion_options(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise VideoStackError("motion deve ser um objeto JSON")
    allowed = {"hook_asset", "hook_seconds", "universe_seconds", "universe_title",
               "auto_cut", "scene_index", "transition", "aspect", "hyperframes_project",
               "openscreen_project", "motion_canvas_clip", "threejs"}
    if set(raw) - allowed:
        raise VideoStackError("Opções de edição desconhecidas")
    opts = {"hook_asset": None, "hook_seconds": 3.0, "universe_seconds": 0.0,
            "universe_title": "UNIVERSO OPEN SOURCE", "auto_cut": False,
            "scene_index": False, "transition": "cut", "aspect": "16:9",
            "hyperframes_project": None, "openscreen_project": None,
            "motion_canvas_clip": None, "threejs": False}
    opts.update(raw)
    for key, limit in (("hook_seconds", 8), ("universe_seconds", 8)):
        value = opts[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:
            raise VideoStackError(f"{key} fora dos limites")
    for key in ("auto_cut", "scene_index", "threejs"):
        if type(opts[key]) is not bool:
            raise VideoStackError(f"{key} deve ser booleano")
    if opts["threejs"] and opts["universe_seconds"] <= 0:
        raise VideoStackError("threejs exige universe_seconds > 0")
    if opts["transition"] not in ("cut", "fade", "wipeleft", "slideleft", "smoothleft", "circleopen"):
        raise VideoStackError("Transição não permitida; sem flash branco")
    if opts["aspect"] not in FORMATS:
        raise VideoStackError("Proporção inválida")
    if (not isinstance(opts["universe_title"], str) or len(opts["universe_title"]) > 100
            or any(ord(c) < 32 for c in opts["universe_title"])):
        raise VideoStackError("Título de abertura inválido")
    for key in ("hook_asset", "motion_canvas_clip"):
        if opts[key] is not None:
            safe_asset(opts[key], Path("assets"))
    if opts["hook_asset"] is None and "hook_seconds" in raw:
        raise VideoStackError("hook_seconds requer hook_asset")
    for key in ("hyperframes_project", "openscreen_project"):
        value = opts[key]
        if value is not None and (
                not isinstance(value, str) or not re.fullmatch(r"assets/[A-Za-z0-9_.\-/]{1,150}", value)
                or ".." in Path(value).parts):
            raise VideoStackError(f"{key} fora de assets/")
    return opts


def plan_intro(hook_seconds: float, universe_seconds: float, body_seconds: float):
    if any(type(x) not in (int, float) or not math.isfinite(x) or x < 0
           for x in (hook_seconds, universe_seconds, body_seconds)) or body_seconds <= 0:
        raise VideoStackError("Duração inválida")
    return ([(name, duration) for name, duration in
             (("hook", hook_seconds), ("universe", universe_seconds), ("body", body_seconds))
             if duration > 0])


def ffprobe_media(path: str | Path) -> dict:
    completed = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_type,width,height",
        "-of", "json", str(path)], check=True, capture_output=True,
        text=True, timeout=30)
    data = json.loads(completed.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise VideoStackError("Arquivo de mídia não contém vídeo")
    duration = float(data["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise VideoStackError("Duração inválida da mídia")
    return {"duration": duration, "width": video.get("width"),
            "height": video.get("height"),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams)}


def scene_detect_api(source):
    try:
        from scenedetect import ContentDetector, detect
    except ImportError as exc:
        raise VideoStackError("Instale scenedetect para indexação de cortes") from exc
    return detect(str(source), ContentDetector())


def index_scenes(source: str | Path) -> list[dict]:
    """PySceneDetect indexes cuts; no downloads or external AI."""
    return [{"start": round(start.get_seconds(), 3),
             "end": round(end.get_seconds(), 3)}
            for start, end in scene_detect_api(source)]


def checked_run(argv: list[str], timeout: int = 1800):
    subprocess.run(argv, check=True, timeout=timeout, capture_output=True)


def auto_cut_silence(source: Path, target: Path) -> Path:
    """Only opt-in; never change the timing of an approved narration silently."""
    if not shutil.which("auto-editor"):
        raise VideoStackError("auto-editor não instalado: instale o adaptador opcional")
    if not ffprobe_media(source)["has_audio"]:
        raise VideoStackError("Auto-Editor exige áudio na fonte")
    checked_run(["auto-editor", str(source), "--margin", "0.18s",
                 "--output", str(target)], timeout=1800)
    if not target.is_file() or target.stat().st_size < 1000:
        raise VideoStackError("Auto-Editor não produziu vídeo")
    return target


def render_adapter(kind: str, source: Path, target: Path) -> Path:
    """Use installed open-source CLIs. No installation, network or credentials hidden."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if kind == "openscreen":
        if not shutil.which("openscreen"):
            raise VideoStackError("OpenScreen CLI ausente")
        checked_run(["openscreen", "export", str(source), "-o", str(target), "--json"])
    elif kind == "hyperframes":
        if not source.is_dir() or not (source / "index.html").is_file():
            raise VideoStackError("HyperFrames necessita de projeto com index.html")
        executable = shutil.which("hyperframes")
        if not executable:
            raise VideoStackError("Instale HyperFrames CLI localmente com Node.js 22+")
        # CLI emits into the project. Use a copy of the project, never touch source files.
        with tempfile.TemporaryDirectory(prefix="moneyprint-hyperframes-") as temp:
            folder = Path(temp) / "project"
            shutil.copytree(source, folder, ignore=shutil.ignore_patterns("node_modules"))
            subprocess.run([executable, "render", "--output", str(target.resolve())],
                           cwd=folder, check=True, text=True,
                           capture_output=True, timeout=1800)
            if not target.is_file():
                raise VideoStackError("HyperFrames não exportou MP4")
    else:
        raise VideoStackError("Adaptador desconhecido")
    ffprobe_media(target)
    return target


def render_stack(source: Path, output: Path, *, options: dict | None = None,
                 assets: Path | None = None) -> dict:
    """Re-encode for consistent format, concatenate hard cuts, align audio exactly."""
    opts = normalize_motion_options(options or {})
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise VideoStackError("Vídeo principal inexistente")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise VideoStackError("FFmpeg + FFprobe precisam estar instalados")
    assets = (assets or Path.cwd() / "assets").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    w, h = FORMATS[opts["aspect"]]
    fps = 30
    with tempfile.TemporaryDirectory(prefix="moneyprint-stack-") as tmp:
        root = Path(tmp)
        body = source
        if opts["auto_cut"]:
            body = auto_cut_silence(source, root / "trimmed.mp4")
        body_meta = ffprobe_media(body)
        timeline = []
        if opts["hook_asset"]:
            hook = safe_asset(opts["hook_asset"], assets)
            if not hook.is_file():
                raise VideoStackError("Gancho não encontrado em assets/")
            hook_seconds = opts["hook_seconds"]
            if hook_seconds <= 0 or ffprobe_media(hook)["duration"] + 0.015 < hook_seconds:
                raise VideoStackError("Gancho menor que duração solicitada")
            timeline.append(("hook", hook, hook_seconds))
        if opts["universe_seconds"] > 0:
            from scripts.motion_design import render_threejs_universe, render_universe
            if opts["threejs"]:
                render_universe = render_threejs_universe
            universe = root / "universe.mp4"
            render_universe(universe, title=opts["universe_title"],
                            seconds=opts["universe_seconds"], size=(w, h), fps=fps)
            timeline.append(("universe", universe, opts["universe_seconds"]))
        if opts["motion_canvas_clip"]:
            clip = safe_asset(opts["motion_canvas_clip"], assets)
            if not clip.is_file():
                raise VideoStackError("Clipe Motion Canvas não encontrado")
            timeline.append(("motion_canvas", clip, ffprobe_media(clip)["duration"]))
        if opts["openscreen_project"]:
            path = (assets / Path(opts["openscreen_project"]).relative_to("assets")).resolve()
            if not path.is_relative_to(assets) or path.suffix != ".openscreen":
                raise VideoStackError("Projeto OpenScreen inválido")
            clip = render_adapter("openscreen", path, root / "openscreen.mp4")
            timeline.append(("openscreen", clip, ffprobe_media(clip)["duration"]))
        if opts["hyperframes_project"]:
            path = (assets / Path(opts["hyperframes_project"]).relative_to("assets")).resolve()
            if not path.is_relative_to(assets):
                raise VideoStackError("Projeto HyperFrames inválido")
            clip = render_adapter("hyperframes", path, root / "hyperframes.mp4")
            timeline.append(("hyperframes", clip, ffprobe_media(clip)["duration"]))
        timeline.append(("body", body, body_meta["duration"]))
        normalized = []
        for idx, (name, clip, seconds) in enumerate(timeline):
            destination = root / f"segment-{idx:03d}.mp4"
            checked_run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-i", str(clip), "-t", str(seconds),
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
                       f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x080d1e,setsar=1,fps={fps},format=yuv420p",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", str(destination)], timeout=1800)
            normalized.append(destination)
        durations = [ffprobe_media(p)["duration"] for p in normalized]
        transition = opts["transition"]
        overlap = 0.24 if transition != "cut" and len(normalized) > 1 else 0.0
        if overlap and min(durations) <= overlap + 0.08:
            raise VideoStackError("Clipe curto demais para a transição escolhida")
        joined = root / "joined.mp4"
        if overlap:
            inputs = []
            stages = []
            for idx, clip in enumerate(normalized):
                inputs.extend(["-i", str(clip)])
                # Normalized segments already share FPS, pixel format and dimensions.
            accumulated = durations[0]
            previous = "0:v"
            for idx in range(1, len(normalized)):
                out_label = f"x{idx}"
                stages.append(
                    f"[{previous}][{idx}:v]xfade=transition={transition}:"
                    f"duration={overlap}:offset={accumulated-overlap:.5f}[{out_label}]"
                )
                accumulated += durations[idx] - overlap
                previous = out_label
            checked_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                         "-y", *inputs, "-filter_complex", ";".join(stages),
                         "-map", f"[{previous}]", "-an", "-c:v", "libx264",
                         "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                         "-movflags", "+faststart", str(joined)], timeout=1800)
        else:
            listfile = root / "concat.txt"
            listfile.write_text("".join(f"file '{p.as_posix()}'\n" for p in normalized),
                                encoding="utf-8")
            checked_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                         "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
                         "-c", "copy", str(joined)])
        intro_duration = sum(durations[:-1]) - overlap * (len(normalized) - 1)
        duration = sum(durations) - overlap * (len(normalized) - 1)
        hook_entry = next(((clip, seconds) for name, clip, seconds in timeline
                           if name == "hook"), None)
        has_hook_audio = bool(hook_entry and ffprobe_media(hook_entry[0])["has_audio"])
        if body_meta["has_audio"] or has_hook_audio:
            inputs = ["-i", str(joined), "-i", str(body)]
            filters = []
            if body_meta["has_audio"]:
                delay = max(0, round(intro_duration * 1000))
                filters.append(f"[1:a:0]adelay={delay}:all=1,apad[bodyaudio]")
            if has_hook_audio:
                inputs.extend(["-i", str(hook_entry[0])])
                hook_seconds = hook_entry[1]
                filters.append(
                    f"[2:a:0]atrim=duration={hook_seconds:.5f},"
                    f"asetpts=PTS-STARTPTS,apad[hookaudio]"
                )
            if body_meta["has_audio"] and has_hook_audio:
                filters.append("[bodyaudio][hookaudio]amix=inputs=2:"
                               "duration=longest:normalize=0,alimiter=limit=0.95[a]")
            elif body_meta["has_audio"]:
                filters.append("[bodyaudio]anull[a]")
            else:
                filters.append("[hookaudio]anull[a]")
            checked_run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                         "-y", *inputs, "-filter_complex", ";".join(filters),
                         "-map", "0:v:0", "-map", "[a]", "-c:v", "copy",
                         "-c:a", "aac", "-b:a", "160k", "-t", str(duration),
                         "-movflags", "+faststart", str(output)], timeout=1800)
        else:
            shutil.copy2(joined, output)
        final = ffprobe_media(output)
        if abs(final["duration"] - duration) > 0.25:
            raise VideoStackError("Duração de renderização não bate com timeline")
        result = {"output": str(output), "duration_seconds": final["duration"],
                  "width": w, "height": h, "fps": fps, "transition": "hard_cut" if transition == "cut" else transition,
                  "clips": [{"type": name, "seconds": round(seconds, 3)}
                            for name, _, seconds in timeline],
                  "audio_preserved": body_meta["has_audio"]}
        if opts["scene_index"]:
            result["scenes"] = index_scenes(output)
        return result


def main():
    parser = argparse.ArgumentParser(description="MoneyPrint open source video stack")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--hook")
    parser.add_argument("--hook-seconds", type=float, default=3)
    parser.add_argument("--universe-seconds", type=float, default=0)
    parser.add_argument("--universe-title", default="OPEN SOURCE")
    parser.add_argument("--aspect", choices=FORMATS, default="16:9")
    parser.add_argument("--auto-cut", action="store_true")
    parser.add_argument("--scene-index", action="store_true")
    parser.add_argument("--transition", choices=["cut", "fade", "wipeleft", "slideleft", "smoothleft", "circleopen"], default="cut")
    parser.add_argument("--options-json", help="JSON with motion options")
    args = parser.parse_args()
    options = json.loads(Path(args.options_json).read_text()) if args.options_json else {
        "universe_seconds": args.universe_seconds, "universe_title": args.universe_title,
        "aspect": args.aspect, "auto_cut": args.auto_cut, "scene_index": args.scene_index,
        "transition": args.transition}
    if args.hook:
        source = Path(args.hook).resolve()
        asset_root = (Path.cwd() / "assets").resolve()
        if not source.is_relative_to(asset_root):
            parser.error("Gancho deve estar em assets/")
        options.update({"hook_asset": "assets/" + source.relative_to(asset_root).as_posix(),
                        "hook_seconds": args.hook_seconds})
    try:
        print(json.dumps(render_stack(Path(args.input), Path(args.output),
                                      options=options), ensure_ascii=False))
    except (VideoStackError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Erro: {exc}\n")


if __name__ == "__main__":
    main()
