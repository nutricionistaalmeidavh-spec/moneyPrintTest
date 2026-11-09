"""MoneyPrint ↔ official video-talkcraft bridge (noncommercial educational only).

Upstream code is NOT vendored. The pinned original upstream is installed in the
isolated rendering job and its React recipe components are imported at runtime.
This module only validates storyboard and maps measured Portuguese word timings.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from scripts.studio_render import build_plan

UPSTREAM = "https://github.com/Vincentwei1021/video-talkcraft"
UPSTREAM_SHA = "501708856fbfdf596e27dba3200e12cf95da57be"
LICENSE_NOTICE = "PolyForm Noncommercial 1.0.0 — personal/educational/research only"
TRIGGERS = (
    (("caos", "bagunca", "desorganizacao", "planilha"), "scribble_chaos", "pencil-draw"),
    (("crm", "twenty", "relacionamento"), "crm_orbit", "orbit-drift"),
    (("atendimento", "chatwoot", "mensagens"), "support_chat", "chat-message-flow"),
    (("vendas", "venda", "comercial"), "sales_flow", "numbered-step-stack"),
    (("estoque", "financeiro", "gestao", "processos"), "business_flow", "numbered-step-stack"),
    (("contrato", "contratos", "nota", "notas", "anexos", "papeis", "papel"), "paper_overload", "stack-fan-out"),
    (("documento", "documentos", "paperless", "pdf"), "document_flow", "numbered-step-stack"),
)

def normal(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in ascii_ if not unicodedata.combining(c)))

def select_recipe(keyword: str) -> str:
    term = normal(keyword)
    for phrases, _, card in TRIGGERS:
        if term in phrases:
            return card
    return "numbered-step-stack"

def clip_aligned_cues(project: dict, measured_words: list[dict]) -> list[dict]:
    """Never fabricate word starts; anchor only measured Whisper-pt timestamps."""
    plan = build_plan(project)
    fps = plan["fps"]
    words = []
    for w in measured_words:
        if not isinstance(w, dict) or not isinstance(w.get("word"), str):
            continue
        try:
            start, end = float(w["start"]), float(w["end"])
        except (TypeError, ValueError, KeyError):
            continue
        if not (0 <= start < end <= plan["duration_seconds"] + 0.15):
            continue
        words.append({"word": normal(w["word"]), "start": start, "end": end})
    words.sort(key=lambda w: w["start"])
    cues = []
    used = set()
    for w in words:
        for phrases, effect, card in TRIGGERS:
            if w["word"] not in phrases:
                continue
            at = round(w["start"], 3)
            scene = next((s for s in plan["scenes"]
                if s["start_frame"]/fps <= at < s["end_frame"]/fps), None)
            if scene is None:
                break
            if effect == "document_flow" and "espalhad" in normal(scene["text"]):
                effect, card = "paper_overload", "stack-fan-out"
            key = (scene["id"], effect)
            if key in used:
                break
            # Timestamp only comes from the audio, never the script's estimated word rate.
            cues.append({"id":f"{scene['id']}-{effect}", "scene_id":scene["id"],
                         "word":w["word"], "effect":effect, "recipe":card,
                         "at":at, "duration":min(3.0, max(1.4, (scene["end_frame"]/fps)-at)),
                         "method":"measured_whisper_pt"})
            used.add(key)
            break
    return cues

def audit_illustrations(project: dict, cues: list[dict]) -> dict:
    """Observable QA only. Never block rendering because a word is missing.

    Reports the effects the SCRIPT requires and which were actually aligned to
    measured voice. The renderer must not quietly claim a missing effect exists.
    """
    plan = build_plan(project)
    required = []
    for scene in plan["scenes"]:
        tokens = {normal(token) for token in re.findall(r"[\\wÀ-ÿ]+", scene["text"])}
        for phrases, effect, _card in TRIGGERS:
            if any(phrase in tokens for phrase in phrases):
                name = ("paper_overload" if effect == "document_flow"
                        and "espalhad" in normal(scene["text"]) else effect)
                if name not in required:
                    required.append(name)
    present = list(dict.fromkeys(cue["effect"] for cue in cues))
    return {"required": required,
            "present": present,
            "missing": [effect for effect in required if effect not in present],
            "cue_count": len(cues),
            "timing_source": "measured_whisper_pt" if cues else "no_measured_cues"}


def prepare_talkcraft_data(project: dict, aligned_words: list[dict],
                           destination: Path, shots: dict | None = None) -> dict:
    plan = build_plan(project)
    if plan["visual_style"] != "talkcraft_edu":
        raise ValueError("Talkcraft só pode executar quando explicitamente selecionado")
    fps = plan["fps"]
    media = shots or {}
    scenes = []
    for scene in plan["scenes"]:
        # Internal file keys, never untrusted absolute paths or URLs for Remotion.
        img = media.get(scene["id"])
        if img is not None and not re.fullmatch(r"moneyprint/[a-zA-Z0-9_.-]+[.]png", img):
            raise ValueError("Mídia deve usar caminho interno seguro")
        scenes.append({
            "id":scene["id"], "title":scene["title"], "text":scene["text"],
            "eyebrow":scene.get("eyebrow") or "", "layout":scene["layout"],
            "startFrame":scene["start_frame"], "durationFrames":scene["duration_frames"],
            "repoUrl":scene.get("repo_url") or "", "image":img or "",
        })
    cues=clip_aligned_cues(project, aligned_words)
    result = {
      "schema":"moneyprint-talkcraft-v1", "upstream":UPSTREAM,
      "upstreamSha":UPSTREAM_SHA, "license_notice":LICENSE_NOTICE,
      "style":"pastel-light","fps":fps, "aspect":plan["aspect"],
      "totalFrames":plan["total_frames"], "scenes":scenes,
      "cues":cues,"illustration_audit":audit_illustrations(project,cues),
      "alignment":"measured_whisper_pt" if aligned_words else "none",
      "autopublish":False, "commercial_use":False,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result
