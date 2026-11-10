"""Run ORIGINAL video-talkcraft in an isolated, optional education-only renderer.

The upstream is checked out to the pinned commit by CI. MoneyPrint contributes
only editable scene data and wrappers; all camera and motion recipe code is the
real upstream React/Remotion source. No paid service and no automatic fallback.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from scripts.studio_render import build_plan
from scripts.talkcraft_bridge import UPSTREAM_SHA, prepare_talkcraft_data


def run(cmd: list[str], **kwargs) -> None:
    subprocess.run([str(x) for x in cmd],check=True,**kwargs)


def duration(path: Path) -> float:
    s=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                               "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True)
    return float(s.strip())


def assert_original(upstream: Path):
    git=upstream/".git"
    if not git.exists():
        raise ValueError("Diretório não é checkout do Video Talkcraft original")
    sha=subprocess.check_output(["git","-C",str(upstream),"rev-parse","HEAD"],text=True).strip()
    if sha!=UPSTREAM_SHA:
        raise ValueError("Versão Talkcraft não foi validada (SHA diferente do pin)")


def prepare_audio(project: dict, output: Path, voice_model: Path) -> Path:
    """Create one continuous sample-aligned narration; NEVER concatenate AAC clips."""
    if not voice_model.is_file(): raise FileNotFoundError("Voz Piper local indisponível")
    plan=build_plan(project)
    output.mkdir(parents=True,exist_ok=True)
    tracks=[]
    for i,scene in enumerate(plan["scenes"],1):
        raw=output/f"raw_{i:03}.wav"
        run(["piper","--model",str(voice_model),"--output_file",str(raw)],
            input=scene["text"],text=True,capture_output=True)
        actual=duration(raw)
        target=scene["duration_frames"]/plan["fps"]
        if not 0<actual<240:raise ValueError("Narração vazia ou inválida")
        rate=actual/max(.1,target-.12)
        if rate>2.0:
            raise ValueError(f"Voz extensa para a cena {scene['id']}; aumente a duração")
        # FFmpeg supports atempo 0.5..100, but avoid grossly stretching short speech.
        rate=max(.8,rate)
        track=output/f"voice_{i:03}.wav"
        run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
             "-i",str(raw),"-af",f"atempo={rate:.6f},apad,atrim=0:{target:.9f},aresample=48000",
             "-ar","48000","-ac","1","-c:a","pcm_s16le",str(track)])
        tracks.append(track)
    playlist=output/"voice_list.txt"
    playlist.write_text("".join("file '"+str(f.resolve()).replace("'","'\\''")+"'\n" for f in tracks))
    target=output/"narration.wav"
    run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-f","concat","-safe","0","-i",str(playlist),"-ar","48000",
         "-ac","1","-c:a","pcm_s16le",str(target)])
    if abs(duration(target)-plan["duration_seconds"])>.1:
        raise ValueError("Faixa contínua não corresponde à timeline")
    return target


def align_portuguese(audio: Path, model_name="small") -> list[dict]:
    """Portuguese-specific adapter: upstream timestamps_cpu.py hardcodes 'zh'."""
    from faster_whisper import WhisperModel
    model=WhisperModel(model_name,device="cpu",compute_type="int8")
    pieces,_=model.transcribe(str(audio),language="pt",word_timestamps=True,
                              vad_filter=False,beam_size=5)
    words=[]
    for segment in pieces:
        for word in segment.words or []:
            if word.start is None or word.end is None:continue
            words.append({"word":word.word.strip(),"start":round(word.start,3),
                          "end":round(word.end,3)})
    if not words:raise ValueError("Faster-whisper não identificou a narração em pt-BR")
    return words


def capture_stills(project: dict, output: Path) -> dict[str,Path]:
    """Authentic GitHub stills. No fabricated software UI."""
    from scripts.repo_stills import capture_repo_stills
    repos=list(dict.fromkeys(s.get("repo_url") for s in project["scenes"] if s.get("repo_url")))
    if not repos:return {}
    records=capture_repo_stills(repos,output)
    lookup={repo:list(map(Path,images)) for repo,images in zip(repos,records)}
    serial={repo:0 for repo in repos}
    found={}
    for scene in project["scenes"]:
        repo=scene.get("repo_url")
        images=lookup.get(repo) or []
        if not images:continue
        repo_still=images[serial[repo]%min(3,len(images))]
        app=next((path for path in images if path.name=="app_real.png"),None)
        # Independent, honest capture provenance: one GitHub screenshot
        # plus a REAL published application preview when available.
        found[scene["id"]]={"repo":repo_still,"interface":app}
        serial[repo]+=1
    return found


def write_document_assets(folder: Path) -> None:
    """Original, self-contained SVG document drawings for native Talkcraft cards.

    No third-party stock image, API, or paid asset dependency.
    """
    folder.mkdir(parents=True, exist_ok=True)
    labels=("CONTRATO", "NOTA FISCAL", "PROPOSTA", "RECIBO", "RELATÓRIO")
    colors=("#6c57d5", "#3d93c7", "#2da49a", "#cc8c55", "#9c72b7")
    from html import escape
    for i,(label,color) in enumerate(zip(labels,colors),1):
        bars="\n".join(
            f'<rect x="50" y="{112+j*28}" width="{300-(j%3)*65}" height="10" rx="5" fill="#b9c5d9" opacity=".72"/>'
            for j in range(5))
        svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="300" viewBox="0 0 420 300">'
             f'<rect width="420" height="300" fill="#eef1f8"/>'
             f'<rect x="22" y="15" width="376" height="274" rx="8" fill="white" stroke="#d9e0ed" stroke-width="2"/>'
             f'<rect x="22" y="15" width="376" height="16" fill="{color}"/>'
             f'<text x="50" y="79" font-family="Arial, sans-serif" font-size="26" font-weight="bold" fill="#223250">{escape(label)}</text>'
             f'<rect x="50" y="91" width="118" height="4" fill="{color}"/>'
             f'{bars}'
             f'<circle cx="347" cy="244" r="25" fill="none" stroke="{color}" stroke-width="5" opacity=".65"/>'
             f'<path d="M333 244 l11 9 l19 -23" fill="none" stroke="{color}" stroke-width="5" stroke-linecap="round"/>'
             '</svg>')
        (folder/f"paper_{i}.svg").write_text(svg,encoding="utf-8")


def write_remotion(project: dict, upstream: Path, out: Path, words: list[dict],
                   narration: Path, screenshots: dict[str,Path]|None=None)->Path:
    assert_original(upstream)
    wb=upstream/"workbench"
    src=wb/"src"/"remotion"
    public=wb/"public"/"moneyprint"
    src.mkdir(parents=True,exist_ok=True)
    public.mkdir(parents=True,exist_ok=True)
    write_document_assets(public)
    images={}
    for scene_id,bundle in (screenshots or {}).items():
        if not re.fullmatch(r"scene-[0-9]{3}",scene_id):
            raise ValueError("ID da imagem inválido")
        if not isinstance(bundle,dict):bundle={"repo":bundle}
        record={}
        for media_key,suffix in (("repo","repo"),("interface","app")):
            path=bundle.get(media_key)
            if path is None:continue
            if not path.is_file():
                raise FileNotFoundError("Captura de "+media_key+" não disponível")
            dest=public/f"{scene_id}_{suffix}.png"
            shutil.copyfile(path,dest)
            record[media_key]="moneyprint/"+dest.name
        images[scene_id]=record
    shutil.copyfile(narration,public/"narration.wav")
    source=Path(__file__).resolve().parents[1]/"motion"/"talkcraft"/"MoneyPrint.tsx"
    shutil.copyfile(source,src/"MoneyPrint.tsx")
    manifest=prepare_talkcraft_data(project,words,src/"MoneyPrintData.json",images)
    copy=out/"talkcraft_manifest.json"
    copy.parent.mkdir(parents=True,exist_ok=True)
    copy.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return src/"MoneyPrint.tsx"


def remotion_render(upstream:Path,target:Path,*,frames:str|None=None):
    assert_original(upstream)
    target.parent.mkdir(parents=True,exist_ok=True)
    wb=upstream/"workbench"
    cli=upstream/"runtime"/"node_modules"/".bin"/"remotion"
    if not cli.is_file():
        raise FileNotFoundError("Runtime original ausente: execute check-runtime.sh")
    args=[str(cli),"render","src/remotion/MoneyPrint.tsx","MoneyPrintEdu",
          str(target.resolve()),"--concurrency=1","--codec=h264","--crf=20"]
    if frames:args.append("--frames="+frames)
    run(args,cwd=wb)


def qa(path:Path,frames:int):
    payload=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-count_frames","-show_streams","-of","json",str(path)],text=True))
    video=next((s for s in payload["streams"] if s["codec_type"]=="video"),None)
    audio=next((s for s in payload["streams"] if s["codec_type"]=="audio"),None)
    if not video or not audio:
        raise ValueError("Vídeo Talkcraft sem áudio ou imagem")
    if int(video.get("nb_read_frames","0"))!=frames:
        raise ValueError("Timeline final diverge da quantidade de frames")
    return {"frames":frames,"video_codec":video.get("codec_name"),"audio_codec":audio.get("codec_name")}


def main():
    parser=argparse.ArgumentParser(description="Video Talkcraft ORIGINAL — integração educacional MoneyPrint")
    parser.add_argument("--project",type=Path,required=True)
    parser.add_argument("--upstream",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--voice-model",type=Path)
    parser.add_argument("--whisper-model",default="small")
    parser.add_argument("--capture-github",action="store_true")
    parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args()
    project=json.loads(args.project.read_text(encoding="utf-8"))
    plan=build_plan(project)
    if plan["visual_style"]!="talkcraft_edu":
        raise SystemExit("Use explicitamente visual_style=talkcraft_edu")
    upstream=args.upstream.resolve()
    assert_original(upstream)
    output=args.output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    if args.smoke:
        from wave import open as wave_open
        wave_file=output/"silence.wav"
        with wave_open(str(wave_file),"wb") as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(48000)
            wav.writeframes(b"\0\0"*(48000*max(1,int(plan["duration_seconds"]))))
        # Smoke tests use no fabricated cues; production requires measured ASR.
        audio=wave_file;words=[]
    else:
        if not args.voice_model:raise SystemExit("Informe --voice-model")
        audio=prepare_audio(project,output/"voice",args.voice_model)
        words=align_portuguese(audio,args.whisper_model)
    screenshots=capture_stills(project,output/"capture") if args.capture_github else {}
    write_remotion(project,upstream,output,words,audio,screenshots)
    if args.smoke:
        # Fixture only; never presented as measured timing or used in production.
        internal=upstream/"workbench"/"src"/"remotion"/"MoneyPrintData.json"
        report=output/"talkcraft_manifest.json"
        payload=json.loads(internal.read_text(encoding="utf-8"))
        # QA fixture explicitly marked; never silently used for real narration.
        payload["cues"]=[
          {"id":"qa-scribble","scene_id":plan["scenes"][0]["id"],
           "word":"caos","effect":"scribble_chaos","recipe":"pencil-draw",
           "at":.55,"duration":2.0,"method":"qa_fixture_not_asr"},
          {"id":"qa-crm","scene_id":plan["scenes"][1]["id"],
           "word":"crm","effect":"crm_orbit","recipe":"orbit-drift",
           "at":3.5,"duration":2.0,"method":"qa_fixture_not_asr"},
          {"id":"qa-paper","scene_id":plan["scenes"][2]["id"],
           "word":"contratos","effect":"paper_overload","recipe":"stack-fan-out",
           "at":6.5,"duration":2.0,"method":"qa_fixture_not_asr"}
        ]
        for filename in (internal,report):
            filename.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    mp4=output/"talkcraft_final.mp4"
    remotion_render(upstream,mp4,frames=("0-"+str(min(269,plan["total_frames"]-1))) if args.smoke else None)
    expected=min(270,plan["total_frames"]) if args.smoke else plan["total_frames"]
    report=qa(mp4,expected)
    manifest=json.loads((output/"talkcraft_manifest.json").read_text(encoding="utf-8"))
    report["illustration_audit"]=manifest.get("illustration_audit",{})
    report.update({"engine":"original_video_talkcraft","upstream_sha":UPSTREAM_SHA,
                   "license":"PolyForm Noncommercial 1.0.0","educational_only":True,
                   "alignment":"none_smoke" if args.smoke else manifest.get("alignment","unknown"),
                   "output":str(mp4),"autopublish":False})
    (output/"diagnostico.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
