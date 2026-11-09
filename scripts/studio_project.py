"""MoneyPrint Studio V3: canonical, deterministic storyboard and media decisions.

No paid SDK, LLM, network access or renderer is required by this module.
Existing render_request inputs remain a separate backward-compatible contract.
"""
from __future__ import annotations

import copy
import math
import re
import unicodedata
from pathlib import PurePosixPath

class StudioProjectError(ValueError):
    pass

_ASPECTS = {"9:16", "16:9", "1:1"}
_TRACKS = (
    {"id": "video", "kind": "video"},
    {"id": "voice", "kind": "audio"},
    {"id": "effects", "kind": "audio"},
    {"id": "graphics", "kind": "overlay"},
)
_SAFE_PATH = re.compile(r"^assets/[A-Za-z0-9_.\/-]{1,200}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,72}$")
_WORDS = re.compile(r"[a-z0-9]{3,}", re.I)


def _tokens(value: str) -> set[str]:
    norm = unicodedata.normalize("NFKD", value.casefold())
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    return set(_WORDS.findall(norm))


def _media_path_valid(path: str) -> bool:
    return bool(_SAFE_PATH.fullmatch(path) and ".." not in PurePosixPath(path).parts)


def rank_assets(text: str, assets: list[dict]) -> list[dict]:
    """Rank only locally approved, attributed assets. No invented B-roll."""
    if not isinstance(assets, list):
        return []
    tokens = _tokens(text)
    scored = []
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("verified") is not True:
            continue
        if not asset.get("license") or not asset.get("attribution"):
            continue
        if not _media_path_valid(str(asset.get("path", ""))):
            continue
        labels = " ".join([str(asset.get("title", "")), str(asset.get("description", ""))] +
                          [str(v) for v in asset.get("tags", []) if isinstance(v, str)])
        overlap = tokens.intersection(_tokens(labels))
        if overlap:
            scored.append({"asset": asset, "score": len(overlap),
                           "matched_tokens": sorted(overlap)})
    return sorted(scored, key=lambda item: (-item["score"], str(item["asset"]["id"])))


def _split_script(script: str) -> list[str]:
    paragraphs = re.split(r"\n+|(?<=[.!?])\s+", script.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _allocate_frames(sentences: list[str], total: int) -> list[int]:
    weights = [max(1, len(_tokens(s))) for s in sentences]
    if total < len(weights):
        raise StudioProjectError("Duração menor que o número de cenas")
    remaining = total - len(weights)
    weighted = [remaining * w / sum(weights) for w in weights]
    frames = [1 + math.floor(n) for n in weighted]
    fractional = sorted(range(len(frames)),
                        key=lambda i: (-(weighted[i] - math.floor(weighted[i])), i))
    for i in fractional[:total - sum(frames)]:
        frames[i] += 1
    return frames


def create_project(*, topic: str, script: str, duration_seconds: int,
                   fps: int = 30, aspect: str = "9:16",
                   assets: list[dict] | None = None) -> dict:
    if not isinstance(topic, str) or not 1 <= len(topic.strip()) <= 180:
        raise StudioProjectError("Título inválido")
    if not isinstance(script, str) or not 1 <= len(script.strip()) <= 12000:
        raise StudioProjectError("Roteiro inválido")
    if type(duration_seconds) is not int or not 1 <= duration_seconds <= 3600:
        raise StudioProjectError("Duração inválida")
    if fps not in (24, 25, 30, 60) or aspect not in _ASPECTS:
        raise StudioProjectError("Formato ou FPS inválidos")
    if assets is not None and (not isinstance(assets, list) or len(assets) > 300):
        raise StudioProjectError("Catálogo de mídia inválido")
    sentences = _split_script(script)
    if len(sentences) > 120:
        raise StudioProjectError("Excesso de cenas")
    total = fps * duration_seconds
    durations = _allocate_frames(sentences, total)
    media = copy.deepcopy(assets or [])
    scenes = []
    cursor = 0
    for index, (sentence, frames) in enumerate(zip(sentences, durations), 1):
        ranked = rank_assets(sentence, media)
        asset_id = ranked[0]["asset"]["id"] if ranked else None
        scenes.append({"id": f"scene-{index:03d}", "track_id": "video",
                       "title": sentence[:90], "text": sentence,
                       "kind": "media" if asset_id else "text",
                       "asset_id": asset_id, "start_frame": cursor,
                       "duration_frames": frames,
                       "animation": "cut", "framing": "contain"})
        cursor += frames
    return {"schema_version": 3, "id": "draft", "revision": 1,
            "topic": topic.strip(), "script": script.strip(), "fps": fps,
            "aspect": aspect, "total_frames": cursor,
            "tracks": copy.deepcopy(list(_TRACKS)), "assets": media, "scenes": scenes}


def validate_project(project: dict) -> dict:
    """Fail closed on unsafe asset paths, gaps, overlaps or invalid revisions."""
    if not isinstance(project, dict) or project.get("schema_version") != 3:
        raise StudioProjectError("Versão de projeto inválida")
    fps, aspect = project.get("fps"), project.get("aspect")
    if fps not in (24, 25, 30, 60) or aspect not in _ASPECTS:
        raise StudioProjectError("FPS ou proporção inválidos")
    if type(project.get("revision")) is not int or project["revision"] < 1:
        raise StudioProjectError("Revisão inválida")
    assets = project.get("assets", [])
    if not isinstance(assets, list) or len(assets) > 300:
        raise StudioProjectError("Catálogo inválido")
    seen_assets = set()
    for asset in assets:
        if not isinstance(asset, dict) or not _SAFE_ID.fullmatch(str(asset.get("id", ""))):
            raise StudioProjectError("Identidade de asset inválida")
        if asset["id"] in seen_assets:
            raise StudioProjectError("Asset duplicado")
        seen_assets.add(asset["id"])
        if not _media_path_valid(str(asset.get("path", ""))):
            raise StudioProjectError("Caminho de mídia inseguro")
        if asset.get("verified") is True and (not asset.get("license") or
                                               not asset.get("attribution")):
            raise StudioProjectError("Mídia aprovada sem origem ou licença")
    scenes = project.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 120:
        raise StudioProjectError("Cenas inválidas")
    cursor = 0
    seen = set()
    for scene in scenes:
        if not isinstance(scene, dict):
            raise StudioProjectError("Cena inválida")
        sid = scene.get("id")
        if not isinstance(sid, str) or not _SAFE_ID.fullmatch(sid) or sid in seen:
            raise StudioProjectError("ID de cena inválido ou duplicado")
        seen.add(sid)
        if scene.get("track_id") != "video":
            raise StudioProjectError("Trilha de vídeo inválida")
        if type(scene.get("start_frame")) is not int or scene["start_frame"] != cursor:
            raise StudioProjectError("Sobreposição ou lacuna na timeline")
        dur = scene.get("duration_frames")
        if type(dur) is not int or not 1 <= dur <= 108000:
            raise StudioProjectError("Duração de cena inválida")
        if not isinstance(scene.get("text"), str) or len(scene["text"]) > 2500:
            raise StudioProjectError("Texto de cena inválido")
        asset_id = scene.get("asset_id")
        if asset_id is not None and asset_id not in seen_assets:
            raise StudioProjectError("Cena usa asset inexistente")
        cursor += dur
    if type(project.get("total_frames")) is not int or project["total_frames"] != cursor:
        raise StudioProjectError("Duração total não corresponde às cenas")
    if cursor > 3600 * fps:
        raise StudioProjectError("Vídeo excede o limite do projeto")
    return project


def update_scene(project: dict, scene_id: str, patch: dict,
                 *, expected_revision: int) -> dict:
    if expected_revision != project.get("revision"):
        raise StudioProjectError("Conflito de revisão")
    if not isinstance(patch, dict) or set(patch) - {"duration_frames", "text", "title",
                                                     "asset_id", "animation", "framing"}:
        raise StudioProjectError("Edição inválida")
    updated = copy.deepcopy(project)
    target = next((s for s in updated["scenes"] if s["id"] == scene_id), None)
    if target is None:
        raise StudioProjectError("Cena inexistente")
    target.update(patch)
    cursor = 0
    for scene in updated["scenes"]:
        scene["start_frame"] = cursor
        if type(scene.get("duration_frames")) is not int:
            raise StudioProjectError("Duração inválida")
        cursor += scene["duration_frames"]
    updated["total_frames"] = cursor
    updated["revision"] += 1
    validate_project(updated)
    return updated


def to_render_request(project: dict) -> dict:
    """Legacy-compatible fallback; does not promise frame-exact rendering."""
    validate_project(project)
    duration = math.ceil(project["total_frames"] / project["fps"])
    if duration > 90:
        raise StudioProjectError("Renderizador legado automático suporta até 90 segundos")
    return {"topic": project["topic"], "script": project["script"],
            "duration_seconds": max(15, duration), "aspect": project["aspect"],
            "visual_mode": "auto"}
