"""Builds a single private Kaggle kernel script containing the episode and renderer.

Kaggle's push API accepts a code_file. Bundling prevents missing relative imports.
No credentials are packed; only the public script and original story.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")


def make_kernel(story_file: Path, blender_file: Path, renderer_file: Path,
                target: Path, username: str, slug: str = "frutalandia-ep01",
                scene_id: str | None = None) -> Path:
    from scripts.novelinha_frutas import validate_story
    if not SLUG.fullmatch(username) or not SLUG.fullmatch(slug):
        raise ValueError("Usuário ou slug do Kaggle inválido")
    story = validate_story(json.loads(story_file.read_text(encoding="utf-8")))
    if scene_id is not None:
        from scripts.frutalandia_scenes import get_scene
        get_scene(story, scene_id)
    pieces = {
        "story.json": json.dumps(story, ensure_ascii=False).encode("utf-8"),
        "blender_frutas.py": blender_file.read_bytes(),
        "render_episode.py": renderer_file.read_bytes(),
    }
    target.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({name: base64.b64encode(data).decode("ascii") for name, data in pieces.items()})
    script = (
        "import base64, json, os, pathlib, subprocess, sys, shutil\n"
        "from pathlib import Path\n"
        "work = Path('/kaggle/working')\n"
        "work.mkdir(exist_ok=True)\n"
        "files = json.loads(" + repr(payload) + ")\n"
        "for name, data in files.items():\n"
        "    (work / name).write_bytes(base64.b64decode(data))\n"
        "os.chdir(work)\n"
        "print('FRUTALANDIA_PREFLIGHT=begin', flush=True)\n"
        "if shutil.which('blender') is None:\n"
        "    raise RuntimeError('Blender ausente, Kaggle sem DNS apt; usar GitHub Actions CPU')\n"
        "if shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None:\n"
        "    raise RuntimeError('FFmpeg/FFprobe ausentes; abortar sem instalar')\n"
        "if shutil.which('nvidia-smi') is None:\n"
        "    raise RuntimeError('Accelerator None: NVIDIA GPU não alocada')\n"
        "gpu=subprocess.run(['nvidia-smi','-L'],capture_output=True,text=True,timeout=10)\n"
        "if gpu.returncode or 'GPU' not in gpu.stdout:\n"
        "    raise RuntimeError('GPU NVIDIA indisponível; não fazer render sem aceleração')\n"
        "print('FRUTALANDIA_PREFLIGHT=ok', gpu.stdout[:200],flush=True)\n"
        "cmd = [sys.executable, 'render_episode.py', '--story', 'story.json', "
        "'--output', str(work)]\n"
        + "cmd += " + repr(['--scene-id', scene_id] if scene_id else []) + "\n"
        + "rc = subprocess.call(cmd)\n"
        "if rc != 0:\n"
        "    raise RuntimeError('Render da novelinha falhou; consulte o log do Kaggle')\n"
    )
    (target / "run.py").write_text(script, encoding="utf-8")
    metadata = {
        "id": f"{username}/{slug}",
        "title": slug.replace("-", " ").title(),
        "code_file": "run.py",
        "language": "python", "kernel_type": "script",
        "is_private": True, "enable_gpu": True,
        "enable_internet": True, "machine_shape": "NvidiaTeslaT4",
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
        "model_sources": [],
    }
    (target / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return target / "run.py"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", type=Path, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--slug", default="frutalandia-ep01")
    parser.add_argument("--scene-id", default=None)
    parser.add_argument("--out", type=Path, default=Path(".kaggle-frutalandia"))
    args = parser.parse_args()
    make_kernel(args.story, Path("scripts/frutalandia_blender.py"),
                Path("scripts/frutalandia_episode_runner.py"), args.out,
                args.username.lower(), slug=args.slug, scene_id=args.scene_id)
    print("Kernel privado preparado sem credenciais no código")


if __name__ == "__main__":
    main()
