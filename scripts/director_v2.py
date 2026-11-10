"""Strict storyboard V2 → Remotion contract.

No inference from narration is allowed to replace the approved composition.
"""
from __future__ import annotations


def validate_v2(board: dict, project: dict) -> dict:
    shots=board.get("shots",[])
    scenes=project.get("scenes",[])
    if board.get("schema")!="moneyprint-director-storyboard-v2":
        raise ValueError("V2 board schema required")
    if project.get("director_board")!="storyboards/5-sistemas-director-v2.json":
        raise ValueError("Explicit V2 director board reference required")
    if len(shots)!=25 or len(scenes)!=25 or board.get("total_frames")!=9000:
        raise ValueError("Expected original 25 scenes and 9000 frames")
    if board.get("visual_grammar",{}).get("background")!="#F6EEDB":
        raise ValueError("Warm-paper palette required")
    if board.get("render",{}).get("narration")!="piper_pt_BR":
        raise ValueError("Piper voice is required")
    if board.get("production_status")!="render_requested":
        raise ValueError("V2 video must be requested explicitly")
    if board.get("render",{}).get("publish") is not False:
        raise ValueError("Publishing requires separate authorization")
    catalog=board.get("portrait_catalog") or {}
    if len(catalog)<5:
        raise ValueError("Need 5 unique editorial character identities")
    ids=set()
    unique_chars=set()
    hybrids=0
    cursor=0
    for i,(shot,scene) in enumerate(zip(shots,scenes)):
        if shot["scene_id"]!=scene["id"]:
            raise ValueError("Scene identity drift")
        if shot["narration"]!=scene["text"]:
            raise ValueError("Narration drift")
        t=shot["timeline"]
        if t["start_frame"]!=cursor or t["duration_frames"]!=scene["duration_frames"]:
            raise ValueError("Frame continuity drift")
        cursor+=scene["duration_frames"]
        info=shot["visual_v2"]
        if info["composition"] in ids:
            raise ValueError("Repeated composition")
        ids.add(info["composition"])
        if info["palette"]!="warm_paper":
            raise ValueError("warm_paper needed")
        if not (info.get("protected_typography") and info.get("connectors_avoid_labels")):
            raise ValueError("Connectors may not cross typography")
        if info.get("narration")!=scene["text"]:
            raise ValueError("Timing source narration mismatch")
        if info["media_mode"] not in ("illustration","repo_only","repo_and_interface"):
            raise ValueError("Invalid media mode")
        if info["media_mode"]=="repo_and_interface":
            if not scene.get("repo_url"):
                raise ValueError("Repo app mockup missing source")
            hybrids+=1
        portrait=info.get("portrait")
        if portrait:
            if portrait not in catalog or catalog[portrait]["role"]!=info.get("role"):
                raise ValueError("portrait role mismatch")
            unique_chars.add(portrait)
        dest=shots[i+1]["scene_id"] if i<len(shots)-1 else None
        if shot["transition"]["to_scene"]!=dest:
            raise ValueError("Backward or broken transitions")
    if cursor!=9000 or cursor!=project["total_frames"]:
        raise ValueError("Frame count mismatch")
    return {"frames":cursor,"shots":len(shots),"visual_character_count":len(unique_chars),
            "hybrid_scenes":hybrids}
