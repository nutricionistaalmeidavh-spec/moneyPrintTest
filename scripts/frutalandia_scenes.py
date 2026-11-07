"""Independent scene selection, strict final assembly and media verification.

Only real, validated scene MP4s are accepted; there is no synthetic 'success'
artifact or stock-video fallback.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

SCENE_ID = re.compile(r"^s\d{2}$")
DEFAULT_STORY = "stories/frutalandia/contador-do-butico-ep01.json"


def scene_ids(story: dict) -> list[str]:
    scenes = story.get("scenes", [])
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 12:
        raise ValueError("Lista de cenas inválida")
    ids = [item.get("id") for item in scenes]
    if any(not isinstance(sid, str) or not SCENE_ID.fullmatch(sid) for sid in ids):
        raise ValueError("IDs de cena inválidos")
    if len(set(ids)) != len(ids):
        raise ValueError("Cenas duplicadas")
    for item in scenes:
        if type(item.get("seconds")) is not int or item["seconds"] <= 0:
            raise ValueError("Duração inválida")
    return ids


def expected_duration(story: dict) -> int:
    scene_ids(story)
    return sum(scene["seconds"] for scene in story["scenes"])


def get_scene(story: dict, sid: str) -> dict:
    if not isinstance(sid, str) or not SCENE_ID.fullmatch(sid):
        raise ValueError("ID de cena inválido")
    for scene in story["scenes"]:
        if scene["id"] == sid:
            return scene
    raise ValueError(f"Cena não encontrada: {sid}")


def make_scene_story(story: dict, sid: str) -> dict:
    result = copy.deepcopy(story)
    scene = copy.deepcopy(get_scene(result, sid))
    result["scenes"] = [scene]
    result["format"]["target_seconds"] = scene["seconds"]
    return result


def clip_path(directory: Path, sid: str) -> Path:
    if not SCENE_ID.fullmatch(sid):
        raise ValueError("ID de cena inválido")
    return directory / f"scene-{sid}.mp4"


def write_concat_list(story: dict, directory: Path) -> Path:
    ids = scene_ids(story)
    for sid in ids:
        clip = clip_path(directory, sid)
        if not clip.is_file() or clip.stat().st_size == 0:
            raise FileNotFoundError(f"Cena ausente: {clip.name}")
    directory.mkdir(parents=True, exist_ok=True)
    listing = directory / "concat-list.txt"
    # Filenames originate only from validated ^s[0-9]{2}$ IDs.
    listing.write_text("".join(f"file 'scene-{sid}.mp4'\n" for sid in ids), encoding="utf-8")
    return listing


def probe_mp4(path: Path, seconds: int, require_audio: bool = True) -> dict:
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    probe = subprocess.run(cmd, check=True, capture_output=True, text=True)
    report = json.loads(probe.stdout)
    streams = report.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None or (video.get("width"), video.get("height")) != (720, 1280):
        raise RuntimeError(f"Vídeo inválido: {path.name}")
    if video.get("codec_name") != "h264":
        raise RuntimeError(f"Codec diferente de H.264: {path.name}")
    if require_audio and (audio is None or audio.get("codec_name") != "aac"):
        raise RuntimeError(f"Faixa AAC ausente: {path.name}")
    duration = float(report.get("format", {}).get("duration", 0))
    if abs(duration - seconds) > 1:
        raise RuntimeError(f"Duração divergente: {path.name} {duration:.2f}/{seconds}s")
    return {"duration": duration, "codec": video["codec_name"],
            "has_audio": bool(audio), "width": 720, "height": 1280}


def assemble(story: dict, directory: Path, output: Path) -> Path:
    ids = scene_ids(story)
    listing = write_concat_list(story, directory)
    for sid in ids:
        scene = get_scene(story, sid)
        probe_mp4(clip_path(directory, sid), scene["seconds"])
    output.mkdir(parents=True, exist_ok=True)
    final = output / "frutalandia-contador-ep01.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", "-movflags", "+faststart", str(final)], check=True)
    qa = probe_mp4(final, expected_duration(story))
    if final.stat().st_size < 100_000:
        raise RuntimeError("Arquivo final inesperadamente pequeno")
    sources = []
    for sid in ids:
        p = clip_path(directory, sid)
        sources.append({"id": sid, "file": p.name,
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                        "bytes": p.stat().st_size})
    manifest = {
        "status": "rendered", "story_id": story["id"],
        "video_file": final.name, "scenes": sources,
        "total_seconds": qa["duration"], "resolution": [720, 1280],
        "video_codec": "h264", "audio_codec": "aac",
        "paid_providers": False, "auto_publish": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", "00:00:04", "-i", str(final), "-frames:v", "1",
                    str(output / "capa.png")], check=True)
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="Frutalândia: validação de cenas e montagem")
    parser.add_argument("command", choices=["validate", "assemble"])
    parser.add_argument("--story", type=Path, default=Path(DEFAULT_STORY))
    parser.add_argument("--input-dir", type=Path, default=Path("outputs/frutalandia-clips"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/frutalandia-final"))
    parser.add_argument("--scene", default="all")
    args = parser.parse_args()
    story = json.loads(args.story.read_text(encoding="utf-8"))
    from scripts.novelinha_frutas import validate_story
    validate_story(story)
    if args.command == "validate":
        ids = scene_ids(story)
        if args.scene != "all":
            get_scene(story, args.scene)
        print(json.dumps({"story": story["id"], "scenes": ids, "seconds": expected_duration(story)}))
    else:
        print("Final:", assemble(story, args.input_dir, args.output_dir))


if __name__ == "__main__":
    main()
