"""Non-blocking visual QA for MoneyPrint: 4 real frames per scene, 100 in a 25-scene film.

Uses local FFmpeg + Pillow, no API, key, cloud service or fabricated visuals.
This is evidence for *human* review, not an automatic design approval.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps

PAPER=(246,238,219)
FRACTIONS=(0.18,0.41,0.64,0.86)
LICENSE_NOTICE="Talkcraft: PolyForm Não Comercial. Não publicar ou monetizar sem licença compatível."

def sample_indices(scenes: list[dict]) -> list[dict]:
    points=[]
    for scene in scenes:
        start=int(scene["start_frame"])
        total=int(scene["duration_frames"])
        if total<8:
            raise ValueError("Cena curta demais para quatro inspeções visuais")
        for fraction in FRACTIONS:
            offset=max(1,min(total-2,int(round(total*fraction))))
            points.append({"scene_id":scene["id"],"frame":start+offset,"at_fraction":fraction})
    return points

def frame_observation(img: Image.Image) -> dict:
    small=img.convert("RGB").resize((96,54),Image.Resampling.BILINEAR)
    pixels=list(small.getdata())
    # Ignore minor paper texture and smooth gradients (< 40 per channel).
    significant=sum(
        1 for r,g,b in pixels
        if (abs(r-PAPER[0])+abs(g-PAPER[1])+abs(b-PAPER[2]))>125
        and min(r,g,b)<190
    )
    frac=round(significant/len(pixels),5)
    return {"foreground_fraction":frac,"visually_blank":frac<0.012}

def aggregate_observations(samples: list[dict]) -> dict:
    scenes={}
    for sample in samples:
        scenes.setdefault(sample["scene_id"],[]).append(sample)
    review=[]
    for sid,items in scenes.items():
        if any(x.get("visually_blank") for x in items):
            review.append(sid)
    return {
        "sample_count":len(samples),
        "scene_count":len(scenes),
        "samples_per_scene":4,
        "review_scenes":review,
        "automatically_approved":False,
        "license_notice":LICENSE_NOTICE,
        "interpretation":"Amostras são indicadores; imagens reais devem ser revisadas antes de publicar."
    }

def _extract_one(video:Path,frame:int,fps:int) -> Image.Image:
    timestamp=frame/fps
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin",
         "-ss",f"{timestamp:.4f}","-i",str(video),"-frames:v","1",
         "-vf","scale=480:-2:flags=bicubic","-f","image2pipe","-vcodec","mjpeg","-"]
    raw=subprocess.check_output(cmd,timeout=45)
    with Image.open(BytesIO(raw)) as img:
        return img.convert("RGB").copy()

def generate_visual_review(video:Path,scenes:list[dict],fps:int,destination:Path) -> dict:
    """Create 10x10 JPEG proofboard, machine-readable QA and sample timings."""
    points=sample_indices(scenes)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=2) as executor:
        images=list(executor.map(lambda p:_extract_one(video,p["frame"],fps),points))
    sheet=Image.new("RGB",(4800,3000),("#f6eedb"))
    painter=ImageDraw.Draw(sheet)
    samples=[]
    for i,(point,img) in enumerate(zip(points,images)):
        col,row=i%10,i//10
        sheet.paste(img,(col*480,row*300))
        obs=frame_observation(img)
        sample=dict(point,**obs)
        samples.append(sample)
        painter.text((col*480+11,row*300+274),
                     f'{point["scene_id"]} | {point["frame"]/fps:.1f}s',
                     fill=("#8f3a3a" if obs["visually_blank"] else "#374150"))
    report=aggregate_observations(samples)
    report["samples"]=samples
    report["contact_sheet"]="qa_100_cenas.jpg"
    sheet.save(destination/"qa_100_cenas.jpg",format="JPEG",quality=86,optimize=True)
    (destination/"qa_visual.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report
