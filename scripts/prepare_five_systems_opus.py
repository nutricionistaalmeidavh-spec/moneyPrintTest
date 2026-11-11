"""Prepare the five-systems film for the ORIGINAL Opus Motion Library direct renderer.

Never substitute Python redraws for Opus motions.
Only collects authentic public site/repository screenshots; no fake software UI.
Remotion is an isolated, user-requested optional producer, not MoneyPrint core.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

PROJECT="projects/5-sistemas-talkcraft-educacional.json"
BOARD="video-requests/five-systems-original-opus-2026.json"
NAME="five-systems-original-opus-2026"
REQUIRED_MEDIA={4:"erpnext",8:"twenty",12:"chatwoot",16:"plane",20:"paperless"}
MOTION_SOURCES={
    "erpnext":"https://github.com/frappe/erpnext",
    "twenty":"https://github.com/twentyhq/twenty",
    "chatwoot":"https://github.com/chatwoot/chatwoot",
    "plane":"https://github.com/makeplane/plane",
    "paperless":"https://github.com/paperless-ngx/paperless-ngx",
}
OFFICIAL_APP_DOCS={
    "chatwoot":"https://app.chatwoot.com/hc/user-guide/articles/1677231493-lesson-2-dashboard-basics",
    "plane":"https://plane.so/open-source",
}
EXPECTED_MOTIONS=22

def run(*cmd,input=None):
    return subprocess.run([str(v) for v in cmd],input=input,text=input is not None,
                          capture_output=input is not None,check=True)

def duration(path):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],
        text=True).strip())

def validate_board(board,project):
    scenes=board.get("scenes",[])
    original=project.get("scenes",[])
    if board.get("name")!=NAME or board.get("fps")!=30:
        raise ValueError("Storyboard Opus incorreto")
    if len(scenes)!=25 or len(original)!=25 or sum(s.get("min",0) for s in scenes)!=9000:
        raise ValueError("Storyboard deve ter 25 cenas / 9000 frames / 300 segundos")
    counts=Counter(x.get("motion") for x in scenes)
    if len(counts)<EXPECTED_MOTIONS or max(counts.values())>2:
        raise ValueError("Diversidade insuficiente ou motion repetido demais")
    for i,(scene,canon) in enumerate(zip(scenes,original),1):
        if scene.get("min")!=canon["duration_frames"] or scene.get("say")!=canon["text"]:
            raise ValueError(f"Roteiro canônico divergente na cena {i}")
        if scene.get("layers") or scene.get("transition",{}).get("type")!="cut":
            raise ValueError(f"Camadas externas/proibições de transição na cena {i}")
        if not isinstance(scene.get("props"),dict):
            raise ValueError(f"Props incorretas {i}")
    for i,tool in REQUIRED_MEDIA.items():
        if "software/"+tool+"/verified.png" not in str(scenes[i-1]["props"]):
            raise ValueError(f"Sem captura original vinculada à cena {i}")
    return {"scenes":len(scenes),"frames":9000,
            "distinct_motions":len(counts),"max_repetition":max(counts.values()),
            "motions":list(counts)}

def validate_upstream_catalog(board,opus):
    catalog=json.loads((opus/"catalog.json").read_text(encoding="utf-8"))
    available={s["id"] for s in catalog}
    missing={x["motion"] for x in board["scenes"]}-available
    if missing: raise RuntimeError(f"Motions inexistentes no Opus original: {sorted(missing)}")
    return True

def _capture_official_doc(tool,output):
    """Capture only an actual published screenshot element from official docs."""
    from playwright.sync_api import sync_playwright
    url=OFFICIAL_APP_DOCS[tool]
    official=urlsplit(url).hostname
    if official not in {"app.chatwoot.com","plane.so"}:
        raise ValueError("Domínio não autorizado")
    output.parent.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={"width":1600,"height":950},
                device_scale_factor=1,service_workers="block")
            response=page.goto(url,wait_until="domcontentloaded",timeout=45000)
            if not response or response.status>=400 or urlsplit(page.url).hostname!=official:
                raise RuntimeError("Página oficial indisponível")
            page.wait_for_timeout(1900)
            items=page.locator("img").evaluate_all("""images=>images.map((im,i)=>({
               i,alt:im.alt||'',src:im.currentSrc||im.src,
               w:im.naturalWidth,h:im.naturalHeight
            }))""")
            acceptable=[]
            for item in items:
                src=str(item["src"])
                if item["w"]<620 or item["h"]<330 or src.startswith("data:"):
                    continue
                # Visual proof must come from an actual official screenshot.
                keywords=(item["alt"]+" "+src).lower()
                score=sum(4 for key in ("screenshot","dashboard","kanban","inbox",
                                         "conversation","interface","app","workspace")
                          if key in keywords)
                if "logo" in keywords or "hero-art" in keywords:score-=10
                acceptable.append((score,item))
            if not acceptable: raise RuntimeError("Imagem de interface não encontrada")
            _,best=max(acceptable,key=lambda x:(x[0],x[1]["w"]*x[1]["h"]))
            img=page.locator("img").nth(best["i"])
            img.scroll_into_view_if_needed(timeout=9000)
            img.screenshot(path=str(output),timeout=18000,animations="disabled")
            return {"type":"official_documentation_real_image","url":url,
                    "image_source":best["src"],"description":best["alt"]}
        finally:
            browser.close()

def _capture_repos(opus):
    """Keep both real GitHub and original app imagery, with audit provenance."""
    from PIL import Image
    from scripts.repo_stills import capture_repo_stills
    sources={}
    public=opus/"public"/"software"
    public.mkdir(parents=True,exist_ok=True)
    errors=[]
    for tool,url in MOTION_SOURCES.items():
        out=public/tool
        out.mkdir(parents=True,exist_ok=True)
        image=out/"verified.png"
        report={"github":url}
        try:
            captures=capture_repo_stills([url],out/"github")
            records=[Path(v) for v in captures[0]]
            pics={p.name:p for p in records}
            image_source=pics.get("app_real.png") or pics.get("readme_1.png") or pics.get("top.png")
            if not image_source: raise RuntimeError("Nenhuma imagem real do repositório")
            report["source_type"]="github_readme_app_image" if image_source.name=="app_real.png" else "github_page_real"
            report["source_path"]=str(image_source)
            # Official product docs preferred only when the repository lacks UI.
            if image_source.name!="app_real.png" and tool in OFFICIAL_APP_DOCS:
                try:
                    official=out/"official_app_image.png"
                    note=_capture_official_doc(tool,official)
                    if official.is_file() and official.stat().st_size>10000:
                        image_source=official
                        report.update(note)
                except Exception as exc:
                    report["official_doc_error"]=str(exc)[:300]
            shutil.copyfile(image_source,image)
            with Image.open(image) as actual:
                if actual.width<600 or actual.height<300:
                    raise RuntimeError("Captura pequena demais para interface")
            report["verified"]="software/"+tool+"/verified.png"
        except Exception as exc:
            report["error"]=str(exc)[:500]
            errors.append(tool)
        sources[tool]=report
    (opus/"moneyprint-sources.json").write_text(
        json.dumps(sources,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    if errors:
        raise RuntimeError("Captura real ausente (sem fabricar interface): "+", ".join(errors))
    return sources

def prepare_audio(board,opus,model):
    """One Piper WAV per original motion; time fits exactly in canonical scene."""
    if not model.is_file():raise FileNotFoundError(model)
    out=opus/"public"/"voice"/NAME
    out.mkdir(parents=True,exist_ok=True)
    manifest={}
    for i,scene in enumerate(board["scenes"],1):
        wav=out/f"s{i:03d}.wav"
        run("piper","--model",model,"--output_file",wav,input=scene["say"])
        if not wav.is_file() or wav.stat().st_size<1000:
            raise RuntimeError(f"Voz ausente na cena {i}")
        target=(scene["min"]-scene.get("lead",5)-scene.get("pad",10)-2)/30
        spoken=duration(wav)
        if spoken>target:
            rate=spoken/target
            if rate>2.1:raise RuntimeError(f"Narração longa na cena {i}: fator {rate:.2f}")
            other=wav.with_suffix(".faster.wav")
            run("ffmpeg","-hide_banner","-loglevel","error","-y",
                "-i",wav,"-af",f"atempo={rate:.6f}","-ar","22050",other)
            other.replace(wav)
        manifest[f"s{i:03d}"]=scene["say"]
        print(f"Narração original {i:02d}/25 pronta",flush=True)
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    return out

def main():
    if len(sys.argv)!=4:
        raise SystemExit("Uso: python -m scripts.prepare_five_systems_opus BOARD OPUS_DIR MODEL")
    file,opus,model=(Path(p).resolve() for p in sys.argv[1:])
    board=json.loads(file.read_text(encoding="utf-8"))
    project=json.loads(Path(PROJECT).read_text(encoding="utf-8"))
    print("Verificação do roteiro:",validate_board(board,project),flush=True)
    validate_upstream_catalog(board,opus)
    _capture_repos(opus)
    prepare_audio(board,opus,model)
    (opus/"storyboards").mkdir(exist_ok=True,parents=True)
    destination=opus/"storyboards"/(NAME+".json")
    destination.write_text(json.dumps(board,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("25 motions originais preparados (sem adaptar ou reprogramar os componentes)",flush=True)

if __name__=="__main__":main()
