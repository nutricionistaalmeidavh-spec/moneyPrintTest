"""Frutalândia: genuine image-to-video pipeline with stable reference identity.

Preflight/prepare can run on free GitHub-hosted CPU. Actual video synthesis
requires a supported local NVIDIA GPU or an explicitly selected Colab GPU.
Never replaces generation by a fake Ken Burns/slideshow/primitive Blender clip.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"assets/frutalandia/elenco-master.webp"
REFERENCE_B64=ROOT/"assets/frutalandia/elenco-reference.webp"  # Historical name used by CI tests
MANIFEST=ROOT/"assets/frutalandia/reference-manifest.json"
STORY=ROOT/"stories/frutalandia/contador-do-butico-ep01.json"
SCENE_IDS=tuple(f"s{i:02d}" for i in range(1,7))
FPS=12
VIDEO_WIDTH=320
VIDEO_HEIGHT=576
MODEL_ID="Lightricks/LTX-Video-0.9.5"
NEGATIVE_PROMPT="cheap 3D primitives, low poly, stiff puppet, plastic spheres, flat lighting, malformed hands, deformed face, extra limbs, warped face, incorrect fruit identity, text artifacts, flicker, camera shake, blurry, out of focus, low quality"


def load_story(path: Path=STORY) -> dict:
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    ids=[s.get("id") for s in data.get("scenes",[])]
    if ids!=list(SCENE_IDS) or sum(s["seconds"] for s in data["scenes"])!=48:
        raise ValueError("Roteiro requer seis cenas ordenadas de 8 segundos cada")
    for s in data["scenes"]:
        if s["seconds"]!=8 or len(s.get("dialogue",[]))!=1:
            raise ValueError("Cada cena exige um único diálogo de oito segundos")
    if data.get("policies",{}).get("auto_publish") is not False:
        raise ValueError("Publicação automática proibida")
    return data


def read_reference(path: Path=REFERENCE):
    from PIL import Image
    metadata=json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw=Path(path).read_bytes()
    if Path(path)==REFERENCE and hashlib.sha256(raw).hexdigest()!=metadata["sha256"]:
        raise RuntimeError("Imagem de referência alterada! SHA-256 diferente do manifesto")
    im=Image.open(path)
    im.load()
    if im.width<640 or im.height<360:
        raise RuntimeError("Referência insuficiente para identidade 3D")
    return im.convert("RGB")


def lead_character(scene_id: str) -> str:
    mapping=json.loads(MANIFEST.read_text(encoding="utf-8"))["first_frame_speaker"]
    if scene_id not in SCENE_IDS:
        raise ValueError("Cena inválida: "+str(scene_id))
    return mapping[scene_id]


def get_scene_prompt(story: dict, scene_id: str) -> str:
    if scene_id not in SCENE_IDS:
        raise ValueError("Cena inválida: "+str(scene_id))
    scene=next(s for s in story["scenes"] if s["id"]==scene_id)
    char_by_id={c["id"]:c for c in story["characters"]}
    hero=lead_character(scene_id)
    character=char_by_id[hero]
    override=scene.get("counter_override",{}).get(hero,character["forehead_counter"])
    others=", ".join(c["name"] for c in story["characters"] if c["id"]!=hero)
    return (
        "Professional stylized cinematic 3D animated comedy in Nordeste, Brazil, "
        "in a sunlit colorful northeastern Brazilian street market (feira livre), "
        "terracotta buildings, cotton awnings, mandacaru cacti, warm sunlight. "
        "Use the provided first frame as the EXACT same character identity: "
        f"{character['name']}, {character['look']}. Keep the same character face, "
        "same character fruit shape, hairstyle, skin texture and costume across all shots. "
        "Acting and facial emotions must be vivid, playful and highly expressive, "
        "natural eyebrow movement, eye contact, weight shifts and lively gestures. "
        "Camera generally remains locked to maintain the reference identity. "
        "Natural 3D fabric detail, cinematic depth, premium shading. "
        f"Other cast members, when needed: {others}. "
        f"Action: {scene['action']}. "
        f"Place: {scene['place']}. Shot: {scene['shot']}. "
        f"Canonical digital forehead counter must read {override}; disregard digits present in "
        "the original art if they disagree. We will correct LED numerals in postproduction. "
        "No nudity, no explicit sexual activity, no text subtitles baked into generative frames."
    )


def _cover_counter(draw, center, counter: str, scale: float = 1.0):
    """Retype canonic counter over any wrong digits in the reference artwork."""
    from PIL import ImageFont
    x,y=center
    w,h=104,50
    # Reasonably covers original screen (it may obscure a few fruit pixels).
    draw.rounded_rectangle([x-w//2,y-h//2,x+w//2,y+h//2],radius=12,
                           fill=(18,24,28),outline=(95,83,79),width=3)
    fontsize=31 if len(counter)<=3 else 26
    try:
        font=ImageFont.truetype("DejaVuSansMono-Bold.ttf",fontsize)
    except OSError:
        font=ImageFont.load_default()
    box=draw.textbbox((0,0),counter,font=font)
    tw,th=box[2]-box[0],box[3]-box[1]
    draw.text((x-tw/2,y-th/2-box[1]),counter,font=font,fill=(255,68,48))


def prepare_reference(story: dict, output_dir: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageOps, ImageFilter
    output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    source=read_reference()
    meta=json.loads(MANIFEST.read_text(encoding="utf-8"))
    char_by_id={c["id"]:c for c in story["characters"]}
    results=[]
    details=[]
    for scene in story["scenes"]:
        sid=scene["id"]
        hero=lead_character(sid)
        x0,y0,x1,y1=meta["character_crops"][hero]
        roi=source.crop((x0,y0,x1,y1))
        character=char_by_id[hero]
        target=scene.get("counter_override",{}).get(hero,character["forehead_counter"])
        centers={"moranguete":(254,209),"uva":(605,184),
                 "mae-pera":(1050,171),"pai-caju":(1460,165)}
        coords=centers[hero]
        draw=ImageDraw.Draw(roi)
        _cover_counter(draw,(coords[0]-x0,coords[1]-y0),target)
        # Keep full costume visible, preserve native aspect and a vertical format.
        bg=Image.new("RGB",(VIDEO_WIDTH,VIDEO_HEIGHT),(221,180,159))
        portrait=ImageOps.contain(roi,(VIDEO_WIDTH-8,VIDEO_HEIGHT-8),method=Image.Resampling.LANCZOS)
        bg.paste(portrait,((VIDEO_WIDTH-portrait.width)//2,
                          (VIDEO_HEIGHT-portrait.height)//2))
        dest=output_dir/f"first-frame-{sid}.png"
        bg.save(dest)
        results.append(dest)
        details.append({"scene":sid,"character":hero,"counter":target,"image":dest.name,
                        "reference_sha256":meta["sha256"],"prompt":get_scene_prompt(story,sid)})
    (output_dir/"reference-report.json").write_text(
        json.dumps({"status":"prepared_not_rendered","reference":REFERENCE.name,
                    "frames":details,"paid_services_required":False,
                    "publication_authorized":False},ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")
    return results


def check_available_gpu(torch):
    if not torch.cuda.is_available():
        raise RuntimeError("GPU NVIDIA com CUDA não encontrada. GitHub Actions hospedado não gera vídeo.")
    gpu=torch.cuda.get_device_properties(0)
    memory_gb=gpu.total_memory/1024**3
    if memory_gb<10:
        raise RuntimeError(f"GPU NVIDIA com {memory_gb:.1f} GB insuficiente para este perfil LTX; escolha uma configuração quantizada testada")
    print(f"FRUTALANDIA_GPU_REAL={gpu.name} VRAM={memory_gb:.1f}GB",flush=True)


def validate_preview(path: Path,expected_seconds: float, require_audio=False) -> dict:
    path=Path(path)
    if not path.is_file() or path.stat().st_size<10000:
        raise RuntimeError("MP4 ausente ou incompleto")
    p=subprocess.run(["ffprobe","-v","error","-show_format","-show_streams",
                      "-of","json",str(path)],capture_output=True,text=True,
                      check=True,timeout=30)
    report=json.loads(p.stdout)
    video=next((s for s in report.get("streams",[])
                if s.get("codec_type")=="video"),None)
    audio=next((s for s in report.get("streams",[])
                if s.get("codec_type")=="audio"),None)
    if video is None:
        raise RuntimeError("MP4 não contém frames de vídeo reais")
    if video.get("width")!=VIDEO_WIDTH or video.get("height")!=VIDEO_HEIGHT:
        raise RuntimeError("Resolução incorreta")
    if require_audio and audio is None:
        raise RuntimeError("MP4 final sem faixa de áudio")
    seconds=float(report.get("format",{}).get("duration",0))
    if abs(seconds-expected_seconds)>.32:
        raise RuntimeError(f"Duração inválida: {seconds:.2f}s esperado {expected_seconds:.2f}s")
    return {"status":"video_real_validado","duration_seconds":seconds,
            "width":VIDEO_WIDTH,"height":VIDEO_HEIGHT,
            "codec":video.get("codec_name"),"has_audio":bool(audio)}


def run_model(first_frame: Path, prompt: str, output: Path,seconds: int,
              steps: int=28, seed: int=42) -> Path:
    if seconds not in (2,8):
        raise ValueError("Apenas preview de 2s ou cena de 8s")
    import torch
    from diffusers import LTXImageToVideoPipeline
    from diffusers.utils import export_to_video, load_image
    check_available_gpu(torch)
    print("FRUTALANDIA_STAGE=model_loading",MODEL_ID,flush=True)
    pipeline=LTXImageToVideoPipeline.from_pretrained(MODEL_ID,torch_dtype=torch.float16)
    pipeline.enable_model_cpu_offload()
    if hasattr(pipeline.vae,"enable_tiling"):
        pipeline.vae.enable_tiling()
    torch.cuda.empty_cache()
    print("FRUTALANDIA_STAGE=generation_start; seconds="+str(seconds),flush=True)
    video=pipeline(image=load_image(str(first_frame)),prompt=prompt,
                   negative_prompt=NEGATIVE_PROMPT,width=VIDEO_WIDTH,
                   height=VIDEO_HEIGHT,num_frames=seconds*FPS+1,
                   num_inference_steps=steps,
                   generator=torch.Generator(device="cpu").manual_seed(seed)).frames[0]
    output.parent.mkdir(parents=True,exist_ok=True)
    export_to_video(video,str(output),fps=FPS)
    print("FRUTALANDIA_STAGE=generation_done",str(output),flush=True)
    validate_preview(output,float(seconds))
    return output


def assemble_episode(story: dict, clip_dir: Path, out_dir: Path) -> Path:
    """This re-encodes verified I2V clips and adds real Piper voices.

    Export refuses missing scenes and never substitutes a silent fake result.
    """
    out_dir.mkdir(parents=True,exist_ok=True)
    for sid in SCENE_IDS:
        validate_preview(clip_dir/f"scene-{sid}.mp4",8.0)
    from scripts.frutalandia_episode_runner import voices_piper, original_soundtrack, make_subtitles
    import shutil
    if not shutil.which("ffmpeg") or not shutil.which("piper"):
        raise RuntimeError("FFmpeg e Piper TTS open source são obrigatórios para episódio final")
    from scripts.frutalandia_episode_runner import concatenate_wavs
    voices_piper(story,out_dir)
    original_soundtrack(48,out_dir/"trilha-original.wav")
    make_subtitles(story,out_dir/"captions.srt")
    listing=out_dir/"concat-list.txt"
    listing.write_text("".join(f"file '{(clip_dir/f'scene-{sid}.mp4').resolve().as_posix()}'\n" for sid in SCENE_IDS))
    concat=out_dir/"silent-48s.mp4"
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat",
                    "-safe","0","-i",str(listing),"-vf","fps=24",
                    "-c:v","libx264","-crf","20","-pix_fmt","yuv420p",
                    "-t","48",str(concat)],check=True)
    output=out_dir/"frutalandia-contador-i2v-final.mp4"
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error",
                    "-i",str(concat),"-i",str(out_dir/"dialogue.wav"),
                    "-i",str(out_dir/"trilha-original.wav"),
                    "-filter_complex","[1:a]volume=1.7[a];[2:a]volume=.09[b];[a][b]amix=inputs=2:duration=first[c]",
                    "-map","0:v:0","-map","[c]","-c:v","copy","-c:a","aac",
                    "-t","48","-movflags","+faststart",str(output)],check=True)
    meta=validate_preview(output,48.0,require_audio=True)
    (out_dir/"manifest.json").write_text(json.dumps({
        "status":"rendered","model":MODEL_ID,"reference_sha256":json.loads(MANIFEST.read_text())["sha256"],
        "video":str(output.name),"QA":meta,"auto_publish":False,
        "paid_services_required":False},ensure_ascii=False,indent=2))
    return output


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("prepare","preview","render-scene","assemble"))
    parser.add_argument("--story",type=Path,default=STORY)
    parser.add_argument("--scene",choices=SCENE_IDS,default="s01")
    parser.add_argument("--out",type=Path,default=Path("outputs/frutalandia-i2v"))
    parser.add_argument("--steps",type=int,default=28)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--approve-full",action="store_true")
    args=parser.parse_args()
    story=load_story(args.story)
    if args.mode in ("prepare","preview","render-scene"):
        frames=prepare_reference(story,args.out/"first-frames")
    if args.mode=="prepare":
        print("REFERENCES_PREPARED",args.out/"first-frames/reference-report.json")
        return
    if args.mode in ("preview","render-scene"):
        if args.mode=="render-scene" and not args.approve_full:
            raise RuntimeError("Produção de 8s requer --approve-full após aprovação do preview")
        seconds=2 if args.mode=="preview" else 8
        path=args.out/("preview-" if seconds==2 else "scene-")
        path=path.with_name(path.name+args.scene+".mp4")
        run_model(args.out/"first-frames"/f"first-frame-{args.scene}.png",
                  get_scene_prompt(story,args.scene),path,seconds,args.steps,args.seed)
        print("VIDEO_REAL_VERIFIED",path)
    if args.mode=="assemble":
        print("FINAL_REAL_VERIFIED",assemble_episode(story,args.out,args.out/"final"))

if __name__=="__main__":
    main()
