"""Opt-in standalone Remotion renderer for MoneyPrint Studio V3.

This adapter never imports Video Talkcraft and never substitutes FFmpeg when
Remotion is unavailable. FFmpeg is used only to prepare audio/media and validate
the final MP4. The existing open-source Studio renderer is unchanged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess

from scripts.studio_render import (
    IMAGE_EXT, VIDEO_EXT, RenderError, build_plan, word_cues,
)


class RemotionError(RenderError):
    """Explicit Remotion adapter failure (no implicit fallback)."""


DIMENSIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def _run(command: list[str], *, text: str | None = None) -> None:
    subprocess.run(
        [str(item) for item in command], check=True,
        input=text.encode("utf-8") if text is not None else None,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800,
    )


def _probe(path: Path) -> dict:
    try:
        return json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-count_frames", "-show_streams",
             "-of", "json", str(path)], text=True, timeout=180,
        ))
    except (ValueError, subprocess.SubprocessError) as exc:
        raise RemotionError("Falha na verificação técnica do arquivo") from exc


def prepare_manifest(project: dict, root: Path, public_dir: Path,
                     *, captures: dict[str, Path] | None = None) -> dict:
    """Validate timeline/provenance and copy approved sources to an isolated public dir."""
    plan = build_plan(project)
    if project.get("render_engine") not in ("remotion", None):
        raise RemotionError("Adaptador Remotion requer render_engine=remotion")
    if plan["visual_style"] == "talkcraft_edu":
        raise RemotionError("Video Talkcraft não pode ser usado no adaptador Remotion independente")
    root = root.resolve()
    safe_root = (root / "assets").resolve()
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "media").mkdir(exist_ok=True)
    result = []
    for scene in plan["scenes"]:
        media_path = None
        media_kind = None
        asset = plan["assets"].get(scene.get("asset_id"))
        original = None
        if asset:
            original = (root / asset["path"]).resolve()
            if not original.is_relative_to(safe_root) or not original.is_file():
                raise RemotionError("Mídia ausente ou caminho inseguro: " + asset["path"])
            if original.stat().st_size > 250 * 1024 * 1024:
                raise RemotionError("Mídia excede 250 MB")
        elif captures and scene.get("repo_url") in captures:
            original = Path(captures[scene["repo_url"]]).resolve()
            if not original.is_file() or original.suffix.lower() not in IMAGE_EXT:
                raise RemotionError("Captura real do GitHub indisponível")
        if original:
            ext = original.suffix.lower()
            if ext not in IMAGE_EXT | VIDEO_EXT:
                raise RemotionError("Formato visual não suportado pelo adaptador")
            # MOV/MKV/GIF are transcoded for predictable browser playback.
            convert = ext in {".mov", ".mkv", ".gif"}
            dest_ext = ".mp4" if convert else ext
            dest = public_dir / "media" / (scene["id"] + dest_ext)
            if convert:
                _run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-stream_loop", "-1",
                      "-i", str(original), "-t", str(scene["duration_seconds"]),
                      "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dest)])
            else:
                shutil.copyfile(original, dest)
            media_path = "media/" + dest.name
            media_kind = "image" if ext in IMAGE_EXT else "video"
        result.append({
            "id": scene["id"], "title": scene["title"], "text": scene["text"],
            "eyebrow": scene.get("eyebrow", "MONEYPRINT · ARTISYS"),
            "layout": scene["layout"], "animation": scene.get("animation", "cut"),
            "framing": scene.get("framing", "contain"),
            "startFrame": scene["start_frame"],
            "durationFrames": scene["duration_frames"],
            "media": media_path, "mediaKind": media_kind,
            "repoUrl": scene.get("repo_url") or "",
        })
    width, height = DIMENSIONS[plan["aspect"]]
    return {"fps": plan["fps"], "aspect": plan["aspect"], "width": width,
            "height": height, "totalFrames": plan["total_frames"],
            "scenes": result}


def make_render_command(remotion_dir: Path, props: Path,
                        public_dir: Path, target: Path) -> list[str]:
    """Resolve only the preinstalled binary; never use npx network auto-install."""
    binary = remotion_dir / "node_modules" / ".bin" / "remotion"
    entry = remotion_dir / "src" / "index.tsx"
    if not binary.is_file():
        raise RemotionError("Remotion opcional não instalado: execute npm install em motion/remotion")
    if not entry.is_file():
        raise RemotionError("Composição React do MoneyPrint indisponível")
    return [
        str(binary), "render", str(entry), "MoneyPrint", str(target),
        "--props", str(props), "--public-dir", str(public_dir),
        "--codec=h264", "--crf=20", "--concurrency=2",
    ]


def prepare_voice(plan: dict, output: Path, *, voice: str,
                  voice_model: Path | None) -> tuple[Path, list[dict]]:
    """Create a continuous frame-aligned WAV with local Piper or silence."""
    if voice not in {"none", "piper"}:
        raise RemotionError("Voz não suportada")
    if voice == "piper" and (voice_model is None or not voice_model.is_file()):
        raise RemotionError("Informe o modelo Piper local")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "narration.wav"
    warnings = []
    if voice == "none":
        _run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "lavfi",
              "-i", "anullsrc=r=48000:cl=mono", "-t",
              f"{plan['duration_seconds']:.6f}", "-c:a", "pcm_s16le", str(target)])
        return target, warnings
    segments = []
    for scene in plan["scenes"]:
        path = output / (scene["id"] + ".wav")
        raw = output / (scene["id"] + "-raw.wav")
        _run(["piper", "--model", str(voice_model), "--output_file", str(raw)],
             text=scene["text"])
        try:
            duration = float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(raw)],
                text=True, timeout=60).strip())
        except (ValueError, subprocess.SubprocessError) as exc:
            raise RemotionError("Narração Piper inválida") from exc
        scene_seconds = scene["duration_seconds"]
        if not 0 < duration < 300:
            raise RemotionError("Áudio Piper vazio ou longo demais")
        tempo = max(1.0, duration / max(0.1, scene_seconds - 0.15))
        if tempo > 2.0:
            raise RemotionError("Narração maior que a cena " + scene["id"])
        if tempo > 1.25:
            warnings.append({"scene": scene["id"], "type": "voice_tempo_high",
                             "tempo": round(tempo, 2)})
        _run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(raw),
              "-af", f"atempo={tempo:.6f},apad,atrim=0:{scene_seconds:.6f},aresample=48000",
              "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(path)])
        raw.unlink(missing_ok=True)
        segments.append(path)
    concat = output / "voice_list.txt"
    concat.write_text(
        "".join("file '" + str(part.resolve()).replace("'", "'\\''") + "'\n"
                for part in segments), encoding="utf-8",
    )
    _run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-f", "concat",
          "-safe", "0", "-i", str(concat), "-ar", "48000", "-ac", "1",
          "-c:a", "pcm_s16le", str(target)])
    return target, warnings


def render_project(project: dict, root: Path, output_dir: Path, *,
                   voice: str = "piper", voice_model: Path | None = None,
                   capture_github: bool = False) -> dict:
    """Render the V3 storyboard natively in Remotion, without Talkcraft."""
    plan = build_plan(project)
    if project.get("render_engine") != "remotion":
        raise RemotionError("Selecione explicitamente render_engine=remotion")
    root = root.resolve()
    output_dir = output_dir.resolve()
    public_dir = output_dir / "remotion_public"
    captures = {}
    if capture_github:
        urls = list(dict.fromkeys(s.get("repo_url") for s in plan["scenes"]
                                  if s.get("repo_url")))
        if urls:
            from scripts.repo_stills import capture_repo_stills
            found = capture_repo_stills(urls, output_dir / "github_captures")
            for url, paths in zip(urls, found):
                originals = [Path(p) for p in paths if Path(p).suffix.lower() in IMAGE_EXT]
                if originals:
                    captures[url] = originals[0]
    manifest = prepare_manifest(project, root, public_dir, captures=captures)
    narration, warnings = prepare_voice(plan, output_dir / "audio", voice=voice,
                                        voice_model=voice_model)
    shutil.copyfile(narration, public_dir / "narration.wav")
    props = output_dir / "remotion_props.json"
    props.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    credits = []
    for scene in plan["scenes"]:
        asset = plan["assets"].get(scene.get("asset_id"))
        if asset:
            credits.append({"scene": scene["id"], "file": asset["path"],
                            "license": asset["license"], "attribution": asset["attribution"]})
        elif scene.get("repo_url") in captures:
            credits.append({"scene": scene["id"], "source_url": scene["repo_url"],
                            "attribution": "Captura real do GitHub por Playwright"})
    credits_path = output_dir / "creditos.json"
    credits_path.write_text(json.dumps(credits, ensure_ascii=False), encoding="utf-8")
    cues = [cue for scene in plan["scenes"]
            for cue in word_cues(scene["text"], scene["start_frame"] / plan["fps"],
                                 scene["duration_seconds"])]
    (output_dir / "palavras.json").write_text(
        json.dumps({"method": "estimated", "cues": cues}, ensure_ascii=False),
        encoding="utf-8",
    )
    target = output_dir / "studio_final.mp4"
    command = make_render_command(root / "motion" / "remotion", props, public_dir, target)
    try:
        _run(command)
    except (subprocess.SubprocessError, OSError) as exc:
        raise RemotionError("Falha no motor Remotion; nenhum fallback foi aplicado") from exc
    streams = _probe(target).get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if not videos or not audios:
        raise RemotionError("MP4 incompleto: vídeo ou áudio ausentes")
    frames = int(videos[0].get("nb_read_frames", "0"))
    if frames != plan["total_frames"]:
        raise RemotionError(f"MP4 fora da timeline: {frames} != {plan['total_frames']}")
    result = {
        "status": "ok", "engine": "remotion", "output": str(target),
        "fps": plan["fps"], "total_frames": frames,
        "duration_seconds": plan["duration_seconds"], "voice": voice,
        "word_alignment": "estimated", "credits": str(credits_path),
        "warnings": warnings, "autopublish": False,
        "visual_style": plan["visual_style"],
    }
    (output_dir / "diagnostico.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="MoneyPrint — motor Remotion opcional")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--voice", choices=("none", "piper"), default="piper")
    parser.add_argument("--voice-model", type=Path)
    parser.add_argument("--capture-github", action="store_true")
    args = parser.parse_args()
    project = json.loads(args.input.read_text(encoding="utf-8"))
    result = render_project(project, args.root, args.output, voice=args.voice,
                            voice_model=args.voice_model,
                            capture_github=args.capture_github)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
