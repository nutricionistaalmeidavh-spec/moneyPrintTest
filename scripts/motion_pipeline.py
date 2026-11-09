"""Opt-in P0-P2 bridge for existing github_cinematic requests."""
from __future__ import annotations

import json
from pathlib import Path


def render_motion_first(request: dict, dest: Path, runtime: Path, env: dict) -> dict:
    """Keep legacy cinematic inputs and licenses; edit only when requested."""
    from scripts.cinematic_render import render_cinematic
    from scripts.video_stack import normalize_motion_options, render_stack

    opts = normalize_motion_options(request.get("motion", {}))
    report = render_cinematic(request, dest, runtime, env)
    active = (
        opts["hook_asset"] is not None or opts["universe_seconds"] > 0
        or opts["auto_cut"] or opts["scene_index"]
        or opts["openscreen_project"] or opts["hyperframes_project"]
        or opts["motion_canvas_clip"] is not None
    )
    if not active:
        return report
    source = Path(report["output"])
    if not source.is_file():
        raise RuntimeError("Renderizador cinematográfico não produziu MP4")
    target = dest / "video_1_motion.mp4"
    result = render_stack(source, target, options=opts, assets=Path.cwd() / "assets")
    merged = dict(report)
    merged["original_output"] = str(source)
    merged["output"] = result["output"]
    merged["duration_seconds"] = result["duration_seconds"]
    merged["motion_stack"] = result
    if opts["auto_cut"]:
        merged["subtitle_note"] = (
            "Auto-Editor alterou o tempo: reexecute alinhamento SRT antes de publicar."
        )
    (dest / "resultado.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged
