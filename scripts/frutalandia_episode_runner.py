"""Renders a complete 3D episode in the Kaggle worker.

No paid API. Actual Blender frames + Piper/VoiceStudio audio + FFmpeg QC.
A missing MP4, failed renderer or missing voice is a hard error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

MODEL_NAME = "pt_BR-faber-medium"
MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/"
MODEL_SHA = "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7"
PITCH = {"moranguete":1.13, "uva":1.04, "mae-pera":.93, "pai-caju":.84}


def run(args, **kwargs):
    print("EXEC:", " ".join(str(a) for a in args[:4]),flush=True)
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def duration(path):
    proc=run(["ffprobe","-v","error","-show_entries","format=duration",
              "-of","default=nokey=1:noprint_wrappers=1",str(path)],
             capture_output=True,text=True)
    return float(proc.stdout.strip())


def fetch_piper(folder):
    folder.mkdir(parents=True, exist_ok=True)
    model=folder/(MODEL_NAME+".onnx")
    conf=folder/(MODEL_NAME+".onnx.json")
    if not model.is_file() or hashlib.sha256(model.read_bytes()).hexdigest()!=MODEL_SHA:
        temp=model.with_suffix(".download")
        digest=hashlib.sha256()
        with urllib.request.urlopen(MODEL_URL+model.name, timeout=120) as response, temp.open("wb") as out:
            while block:=response.read(1<<20):
                out.write(block)
                digest.update(block)
        if digest.hexdigest()!=MODEL_SHA:
            temp.unlink(missing_ok=True)
            raise RuntimeError("Modelo Piper falhou no SHA256")
        temp.replace(model)
    if not conf.is_file():
        with urllib.request.urlopen(MODEL_URL+conf.name, timeout=60) as response:
            conf.write_bytes(response.read(100_000))
    return model


def voices_piper(story, output):
    if shutil.which("piper") is None:
        run([sys.executable,"-m","pip","install","-q","piper-tts==1.8.0"])
    model=fetch_piper(Path("/tmp/frutalandia-piper-model"))
    voice_dir=output/"audio"
    voice_dir.mkdir(exist_ok=True)
    segments=[]
    for i,scene in enumerate(story["scenes"]):
        scene_len=int(scene["seconds"])
        lines=scene["dialogue"]
        if len(lines)!=1:
            raise RuntimeError("O render atual requer uma fala por cena")
        line=lines[0]
        inp=voice_dir/("%02d-original.wav"%i)
        piper=shutil.which("piper")
        if not piper:
            raise RuntimeError("Piper TTS não instalado")
        run([piper,"--model",str(model),"--output_file",str(inp)],
            input=line["text"],text=True,stdout=subprocess.DEVNULL)
        if not inp.is_file() or inp.stat().st_size<1000:
            raise RuntimeError("Piper não sintetizou "+scene["id"])
        target=voice_dir/("%02d.wav"%i)
        seconds=duration(inp)
        rate=PITCH[line["speaker"]]
        acceleration=max(1.0,seconds/(scene_len-.6))
        # Distinções de timbre e idade leves, sem clonagem de vozes reais.
        filt=(f"asetrate=22050*{rate:.4f},aresample=22050,"
              f"atempo={1/rate:.4f},atempo={acceleration:.4f},"
              f"apad=pad_dur={scene_len},atrim=duration={scene_len},"
              "asetpts=PTS-STARTPTS")
        run(["ffmpeg","-y","-loglevel","error","-i",str(inp),"-af",filt,
             "-ac","1","-ar","22050",str(target)])
        segments.append(target)
    concatenate_wavs(segments,output/"dialogue.wav")
    return "Piper TTS offline (perfis por timbre, não clonagem)"


def voice_studio_optional(story, output, url):
    """Uses an already running local VoiceStudio. Never assumes preset IDs exist."""
    from urllib.parse import urlparse
    parsed=urlparse(url)
    if parsed.scheme!="http" or parsed.hostname not in ("localhost","127.0.0.1"):
        raise RuntimeError("VoiceStudio: URL não local; uso remoto bloqueado")
    with urllib.request.urlopen(url.rstrip("/")+"/v1/audio/voices",timeout=20) as r:
        data=json.load(r)
    available={x.get("id") for x in data.get("data",[]) if isinstance(x,dict)}
    missing={s["dialogue"][0]["speaker"] for s in story["scenes"]}-available
    if missing:
        raise RuntimeError("VoiceStudio sem vozes cadastradas: "+", ".join(sorted(missing)))
    voice_dir=output/"audio"
    voice_dir.mkdir(exist_ok=True)
    clips=[]
    for i,scene in enumerate(story["scenes"]):
        line=scene["dialogue"][0]
        req=urllib.request.Request(url.rstrip("/")+"/v1/audio/speech",data=json.dumps({
            "model":"tts-1","voice":line["speaker"],
            "input":line["text"],"response_format":"wav"
        }).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=180) as r:
            pcm=r.read(20_000_000)
        if pcm[:4]!=b"RIFF":
            raise RuntimeError("VoiceStudio retornou áudio inválido em "+scene["id"])
        raw=voice_dir/("%02d-voice-studio.wav"%i)
        raw.write_bytes(pcm)
        target=voice_dir/("%02d.wav"%i)
        segment_duration=scene["seconds"]
        factor=max(1,duration(raw)/(segment_duration-.6))
        run(["ffmpeg","-y","-loglevel","error","-i",str(raw),
             "-af",f"atempo={factor:.4f},apad=pad_dur={segment_duration},atrim=duration={segment_duration}",
             "-ac","1","-ar","22050",str(target)])
        clips.append(target)
    concatenate_wavs(clips,output/"dialogue.wav")
    return "VoiceStudio API local, perfis originais"


def concatenate_wavs(paths, target):
    listing=target.with_suffix(".txt")
    listing.write_text("".join("file '%s'\n"%p.as_posix() for p in paths))
    run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0",
         "-i",str(listing),"-c:a","pcm_s16le",str(target)])


def original_soundtrack(seconds, output):
    # Trilha original minimalista: sintetização aditiva própria, sem sample.
    sample_rate=12000
    notes=(110.0,138.59,164.81)
    n=seconds*sample_rate
    with wave.open(str(output),"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate)
        buffer=bytearray()
        for k in range(n):
            t=k/sample_rate
            harmony=sum(math.sin(2*math.pi*f*t)*.17 for f in notes)
            pulse=math.sin(2*math.pi*55*t)*(.13 if (t%8)>6.7 else .04)
            swell=min(1.0,t/3,max(0,(seconds-t)/2))
            amp=(harmony+pulse)*swell
            buffer.extend(struct.pack("<h",int(amp*12000)))
        w.writeframes(buffer)


def srt_timestamp(t):
    ms=round(t*1000)
    return f"{ms//3600000:02d}:{(ms//60000)%60:02d}:{(ms//1000)%60:02d},{ms%1000:03d}"


def make_subtitles(story, output):
    clips=[]
    current=0
    for i,scene in enumerate(story["scenes"],1):
        text=" ".join(x["text"] for x in scene["dialogue"])
        # Remove HTML-like markup; source is original and under our control.
        text=text.replace("<","").replace(">","")
        clips.append(f"{i}\n{srt_timestamp(current+.3)} --> {srt_timestamp(current+scene['seconds']-.3)}\n{text}\n")
        current+=scene["seconds"]
    output.write_text("\n".join(clips),encoding="utf-8")


def ensure_blender():
    """A rede do Kaggle pode bloquear DNS; não tentar apt-get no notebook."""
    blender=shutil.which("blender")
    if blender:
        print("FRUTALANDIA_PREFLIGHT=blender_found",flush=True)
        return blender
    raise RuntimeError(
        "Blender ausente/indisponível no Kaggle; não usar apt-get. "
        "Use GitHub Actions CPU ou runtime open-source previamente anexado."
    )


def assemble(story, output, silent, voice_engine):
    total=sum(x["seconds"] for x in story["scenes"])
    sound=output/"soundtrack-original.wav"
    original_soundtrack(total,sound)
    subs=output/"captions.srt"
    make_subtitles(story,subs)
    final=output/"frutalandia-ep01.mp4"
    # ffmpeg subtitles requires libass; a missing filter is a hard failure.
    vf=(f"fps=24,scale=720:1280:flags=lanczos,"
        f"subtitles='{subs.as_posix()}':force_style='Fontname=DejaVu Sans,"
        f"Fontsize=17,Outline=2,Shadow=1,PrimaryColour=&H00FFFFFF&,Alignment=2,MarginV=72'")
    run(["ffmpeg","-y","-loglevel","error",
         "-i",str(silent),"-i",str(output/"dialogue.wav"),"-i",str(sound),
         "-filter_complex","[1:a]volume=1.8[a1];[2:a]volume=0.10[a2];[a1][a2]amix=inputs=2:duration=longest:dropout_transition=0[a]",
         "-map","0:v:0","-map","[a]","-vf",vf,"-c:v","libx264","-preset","veryfast",
         "-crf","21","-pix_fmt","yuv420p","-r","24","-c:a","aac",
         "-b:a","128k","-t",str(total),"-movflags","+faststart",str(final)])
    if not final.is_file() or final.stat().st_size<150000:
        raise RuntimeError("MP4 ausente ou pequeno demais")
    inspect=json.loads(run(["ffprobe","-v","error","-show_format","-show_streams",
                            "-of","json",str(final)],capture_output=True,text=True).stdout)
    streams=inspect["streams"]
    if not any(x["codec_type"]=="audio" for x in streams):
        raise RuntimeError("MP4 sem áudio")
    vid=next((x for x in streams if x["codec_type"]=="video"),None)
    if not vid or (vid["width"],vid["height"])!=(720,1280):
        raise RuntimeError("MP4 com resolução incorreta")
    measured=float(inspect["format"]["duration"])
    if abs(total-measured)>1.0:
        raise RuntimeError(f"Duração incorreta: {measured:.1f} s esperados {total} s")
    run(["ffmpeg","-y","-loglevel","error","-ss","00:00:04",
         "-i",str(final),"-frames:v","1",str(output/"capa.png")])
    manifest={
        "status":"rendered","title":story["title"],"render_engine":"Blender Cycles",
        "audio_engine":voice_engine,"compositor":"FFmpeg, OpenMontage-compatible edit plan",
        "openmontage_runtime_used":False, "kaggle_gpu_required":False,
        "video_path":final.name,"seconds":measured,"dimensions":[720,1280],
        "scenes":len(story["scenes"]),"auto_publish":False,
        "output_is_cgi_3d":True,"native_render_resolution":[360,640],
        "reference_images_used":False,
        "note":"Estilo CGI 3D procedural, não é geração Wan por difusão.",
    }
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print("FRUTALANDIA_MP4_VERIFIED",str(final),measured,flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--story",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--scene-id",default="")
    args=p.parse_args()
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    story=json.loads(args.story.read_text(encoding="utf-8"))
    status=output/"render-status.json"
    try:
        if not story.get("scenes") or sum(s["seconds"] for s in story["scenes"])!=story["format"]["target_seconds"]:
            raise RuntimeError("Storyboard inválido")
        render_story=story
        if args.scene_id:
            matching=[s for s in story["scenes"] if s.get("id")==args.scene_id]
            if len(matching)!=1 or not args.scene_id.startswith("s"):
                raise RuntimeError("ID de cena inválido: "+args.scene_id)
            render_story=dict(story)
            render_story["format"]=dict(story["format"])
            render_story["scenes"]=matching
            render_story["format"]["target_seconds"]=matching[0]["seconds"]
            os.environ["FRUTALANDIA_SCENE_ID"]=args.scene_id
        print("FRUTALANDIA_STAGE=preflight",flush=True)
        engine=ensure_blender()
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("FFmpeg/FFprobe ausentes; não instalar via Kaggle DNS")
        print("FRUTALANDIA_STAGE=render_ready",flush=True)
        silent_candidates=list(output.glob("silent*.mp4"))
        if not silent_candidates:
            renderer=Path(__file__).with_name("blender_frutas.py")
            if not renderer.is_file():
                renderer=Path(__file__).with_name("frutalandia_blender.py")
            if not renderer.is_file():
                raise RuntimeError("Script Blender da Frutalândia ausente")
            print("FRUTALANDIA_STAGE=blender_render_start",args.scene_id or "all",flush=True)
            run([engine,"-b","-t","4","--python",str(renderer),
                 "--",str(args.story.resolve()),str(output)])
            silent_candidates=list(output.glob("silent*.mp4"))
        if not silent_candidates:
            raise RuntimeError("Blender não gerou clipe 3D")
        silent=max(silent_candidates,key=lambda x:x.stat().st_size)
        print("FRUTALANDIA_STAGE=blender_render_done",args.scene_id or "all",flush=True)
        studio=os.environ.get("VOICE_STUDIO_URL","").strip()
        if studio:
            voice_engine=voice_studio_optional(render_story,output,studio)
        else:
            voice_engine=voices_piper(render_story,output)
        assemble(render_story,output,silent,voice_engine)
        if args.scene_id:
            rendered=output/"frutalandia-ep01.mp4"
            target=output/("scene-"+args.scene_id+".mp4")
            rendered.replace(target)
            manifest_path=output/"manifest.json"
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["video_path"]=target.name
            manifest["scene_id"]=args.scene_id
            manifest["story_id"]=story.get("id")
            manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        status.write_text(json.dumps({"status":"success"}))
    except Exception as exc:
        status.write_text(json.dumps({"status":"failed","error":type(exc).__name__+": "+str(exc)},
                                     ensure_ascii=False,indent=2))
        raise


if __name__=="__main__":
    main()
