"""Validate a *review-only* director storyboard against canonical Studio V3.

This does not render and does not change the project's current timeline.
It enforces no return-to-previous, no duplicate composition and no fake ASR times.
"""
from __future__ import annotations
import re
import unicodedata


def _norm(value: str) -> str:
    raw=unicodedata.normalize("NFKD",str(value).casefold())
    return " ".join("".join(ch for ch in raw if not unicodedata.combining(ch)).split())


def validate_board(board: dict, project: dict) -> dict:
    shots=board.get("shots",[])
    scenes=project.get("scenes",[])
    fps=project.get("fps")
    if fps!=30 or board.get("fps")!=fps:
        raise ValueError("fps divergence")
    if board.get("production_status")!="awaiting_visual_approval":
        raise ValueError("storyboard is review-only until manually approved")
    if not isinstance(shots,list) or len(shots)!=len(scenes) or len(shots)!=25:
        raise ValueError("storyboard scene count drift")
    compositions=set()
    n=0
    for i,(shot,src) in enumerate(zip(shots,scenes)):
        if shot.get("scene_id")!=src["id"]:
            raise ValueError(f"scene_id drift at {i}")
        timeline=shot.get("timeline",{})
        if timeline.get("start_frame")!=src["start_frame"] or timeline.get("start_frame")!=n:
            raise ValueError(f"frame start drift at {src['id']}")
        if timeline.get("duration_frames")!=src["duration_frames"]:
            raise ValueError(f"frame duration drift at {src['id']}")
        n+=src["duration_frames"]
        if shot.get("narration")!=src["text"]:
            raise ValueError(f"narration differs at {src['id']}")
        c=shot.get("visual",{}).get("composition_id")
        if not c or c in compositions:
            raise ValueError(f"duplicate composition: {c}")
        compositions.add(c)
        visual=shot["visual"]
        if not visual.get("intent") or not visual.get("primary_metaphor") or len(visual.get("layers",[]))<3:
            raise ValueError(f"incomplete visual direction at {src['id']}")
        exp=scenes[i+1]["id"] if i<len(scenes)-1 else None
        transition=shot.get("transition",{})
        if transition.get("to_scene")!=exp or transition.get("type") in ("return_to_previous","flashback"):
            raise ValueError(f"non-forward transition at {src['id']}")
        if not transition.get("carry_element") and i<len(scenes)-1:
            raise ValueError(f"missing visual continuity at {src['id']}")
        beats=shot.get("motion_beats",[])
        if len(beats)<3:
            raise ValueError(f"need 3 motion beats at {src['id']}")
        previous=-1
        for beat in beats:
            at=beat.get("at_s")
            if not isinstance(at,(float,int)) or not previous<=at<src["duration_frames"]/fps:
                raise ValueError(f"out of sequence motion beat at {src['id']}")
            if beat.get("timing") not in ("editorial","word_anchor_pending"):
                raise ValueError(f"fabricated timing at {src['id']}")
            if not beat.get("action") or not beat.get("layer"):
                raise ValueError(f"incomplete beat at {src['id']}")
            previous=at
        sync=shot.get("audio_sync",{})
        if sync.get("timestamps_confirmed") is not False or sync.get("mode")!="word_anchor_to_align":
            raise ValueError("unmeasured narration has no exact timestamps")
        for word in sync.get("keywords",[]):
            if _norm(word) not in _norm(src["text"]):
                raise ValueError(f"word_anchor not in narration: {word} / {src['id']}")
    if n!=project.get("total_frames") or n!=board.get("total_frames"):
        raise ValueError("frame total mismatch")
    ids=[x["id"] for x in board.get("assets",[])]
    if len(ids)!=len(set(ids)):
        raise ValueError("duplicate assets")
    kinds={"original_vector","generated_cutout","github_capture","own_broll","typography"}
    if any(x.get("kind") not in kinds or not x.get("license") for x in board.get("assets",[])):
        raise ValueError("asset license or type missing")
    assets=set(ids)
    if any(a not in assets for shot in shots for a in shot.get("asset_ids",[])):
        raise ValueError("shot references missing asset")
    return {
      "scene_count":len(shots),"total_frames":n,"seconds":n/fps,
      "unique_compositions":len(compositions),
      "pending_assets":sum(x.get("status")!="ready" for x in board["assets"]),
      "approved_to_render":False,
    }
