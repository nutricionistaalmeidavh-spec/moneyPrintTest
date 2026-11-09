"""Bridge the MoneyPrint visual graph to the canonical open-source Studio V3 engine.

No LLM or paid provider is needed to preserve known narration and repository
sources. The visual builder's duration remains exactly authoritative.
"""
from __future__ import annotations
import re


def _phrases(narration: str) -> list[str]:
    bits=[x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+",narration.strip()) if x.strip()]
    if len(bits)==1:
        words=bits[0].split()
        if len(words)>38:
            count=min(5,max(2,(len(words)+24)//25))
            size=(len(words)+count-1)//count
            bits=[" ".join(words[i:i+size]) for i in range(0,len(words),size)]
    # Reduce very long sections without cutting any narrated words.
    while len(bits)>5:
        last=bits.pop()
        bits[-1]+=" "+last
    return bits or [narration.strip()]


def _frames(weights: list[int], count: int) -> list[int]:
    if count<len(weights):
        raise ValueError("Duração insuficiente para as cenas")
    denominator=sum(weights)
    fractions=[(count-len(weights))*w/denominator for w in weights]
    allocated=[1+int(x) for x in fractions]
    left=count-sum(allocated)
    priority=sorted(range(len(weights)),key=lambda i:(-(fractions[i]-int(fractions[i])),i))
    for i in priority[:left]:allocated[i]+=1
    return allocated


def _short_heading(text: str, fallback: str) -> str:
    words=re.sub(r"\s+"," ",text.strip()).split()
    if not words:return fallback.upper()
    return " ".join(words[:7]).upper().strip(".,;:!?")[:100]


def cinematic_request_to_studio_project(req: dict) -> dict:
    if req.get("visual_mode")!="github_cinematic" or req.get("visual_style") not in {"light_motion","talkcraft_edu"}:
        raise ValueError("O adaptador exige pedido cinematográfico com estilo claro")
    sections=req.get("sections") or []
    if not sections or len(sections)!=len(req.get("repo_urls",[])):
        raise ValueError("Seções e URLs não correspondem")
    fps=30
    total=fps*int(req["duration_seconds"])
    items=[]
    for section in sections:
        repo=section["repo_url"]
        name=section["title"].strip()
        for j,phrase in enumerate(_phrases(section["narration"])):
            items.append((repo,name,j,phrase))
    if len(items)>120 or not items:
        raise ValueError("Número inválido de cenas")
    sizes=_frames([max(1,len(text.split())) for _,_,_,text in items],total)
    layouts=("hero","browser","flow","split","flow")
    scenes=[]
    cursor=0
    for i,((repo,name,j,text),nframes) in enumerate(zip(items,sizes),1):
        scene={
            "id":f"scene-{i:03d}","track_id":"video",
            "title":name.upper() if j==0 else _short_heading(text,name),
            "text":text,"kind":"text","asset_id":None,
            "start_frame":cursor,"duration_frames":nframes,
            "animation":"cut","framing":"contain",
            "layout":layouts[j%len(layouts)],
            "repo_url":repo,"eyebrow":name[:80],
        }
        cursor+=nframes
        scenes.append(scene)
    project={
       "schema_version":3,"id":"visual-flow-light-motion","revision":1,
       "topic":req["topic"],
       "script":"\n".join(s["narration"] for s in sections),
       "fps":fps,"aspect":req["aspect"],
       "visual_style":req["visual_style"],"total_frames":cursor,
       "tracks":[{"id":"video","kind":"video"},{"id":"voice","kind":"audio"},
                 {"id":"effects","kind":"audio"},{"id":"graphics","kind":"overlay"}],
       "assets":[],"scenes":scenes,
    }
    # Validate using the same source-of-truth contract as manually edited projects.
    from scripts.studio_render import build_plan
    build_plan(project)
    return project
