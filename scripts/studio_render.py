"""Render canonical MoneyPrint Studio V3 scenes without commercial dependencies.

The Studio V3 project is the sole timeline authority. Optional approved local media
is composited into original slides. No synthetic screenshot is passed off as real.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


class RenderError(ValueError):
    """Invalid canonical timeline or missing verified media."""


SAFE_MEDIA = re.compile(r"^assets/[A-Za-z0-9_.\/-]{1,200}$")
VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".gif"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
LAYOUTS = {"hero", "browser", "flow", "split", "quote", "minimal"}
REPO_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$")


def build_plan(project: dict) -> dict:
    if not isinstance(project, dict) or project.get("schema_version") != 3:
        raise RenderError("Projeto V3 inválido")
    fps = project.get("fps")
    if fps not in (24, 25, 30, 60) or project.get("aspect") not in {"16:9", "9:16", "1:1"}:
        raise RenderError("FPS/proporção inválidos")
    scenes = project.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 120:
        raise RenderError("Cenas inválidas")
    assets = project.get("assets", [])
    if not isinstance(assets, list) or len(assets) > 300:
        raise RenderError("Catálogo inválido")
    indexed = {}
    for a in assets:
        if not isinstance(a, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{1,72}", str(a.get("id", ""))):
            raise RenderError("ID de mídia inválido")
        path = a.get("path")
        if a["id"] in indexed or not isinstance(path, str) or not SAFE_MEDIA.fullmatch(path) or ".." in PurePosixPath(path).parts:
            raise RenderError("Mídia duplicada ou caminho inseguro")
        if a.get("verified") is not True or not a.get("license") or not a.get("attribution"):
            raise RenderError("Mídia precisa de licença, origem e aprovação")
        if PurePosixPath(path).suffix.lower() not in VIDEO_EXT | IMAGE_EXT | {".wav", ".mp3", ".ogg"}:
            raise RenderError("Formato de mídia não suportado")
        indexed[a["id"]] = a
    cursor = 0
    prepared = []
    ids = set()
    for raw in scenes:
        if not isinstance(raw, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{1,72}", str(raw.get("id", ""))):
            raise RenderError("Cena inválida")
        if raw["id"] in ids or raw.get("track_id") != "video":
            raise RenderError("Cena duplicada ou trilha inválida")
        ids.add(raw["id"])
        count = raw.get("duration_frames")
        if type(count) is not int or not 1 <= count <= fps * 3600 or raw.get("start_frame") != cursor:
            raise RenderError("Timeline com duração inválida, lacuna ou sobreposição")
        if not isinstance(raw.get("title"), str) or not isinstance(raw.get("text"), str) or not raw["text"].strip():
            raise RenderError("Narração/título da cena inválidos")
        if len(raw["text"]) > 2500 or len(raw["title"]) > 160:
            raise RenderError("Texto da cena excede o limite")
        asset_id = raw.get("asset_id")
        if asset_id is not None and asset_id not in indexed:
            raise RenderError("Mídia associada não está aprovada")
        if raw.get("repo_url") and (not isinstance(raw["repo_url"], str) or not REPO_URL.fullmatch(raw["repo_url"])):
            raise RenderError("Apenas URLs de repositórios públicos no GitHub são aceitas")
        layout = raw.get("layout", "hero")
        if layout not in LAYOUTS:
            raise RenderError("Layout de cena não suportado")
        if raw.get("animation", "cut") not in {"cut", "fade", "slide"}:
            raise RenderError("Animação não suportada")
        prepared.append({**raw, "layout": layout, "end_frame": cursor + count,
                         "duration_seconds": count / fps})
        cursor += count
    if cursor != project.get("total_frames") or cursor > fps * 3600:
        raise RenderError("Total de frames divergente do projeto")
    return {"fps": fps, "aspect": project["aspect"], "total_frames": cursor,
            "duration_seconds": cursor / fps, "scenes": prepared, "assets": indexed}


def word_cues(text: str, start: float, duration: float) -> list[dict]:
    """Plan visual word cues: estimates, not a claim of true forced alignment."""
    words = re.findall(r"\S+", text)
    if not words or duration <= 0:
        return []
    weights = [max(1, len(w.strip(',.!?'))) for w in words]
    denom = sum(weights)
    current = start
    result = []
    for i, (word, weight) in enumerate(zip(words, weights)):
        finish = start + duration if i == len(words) - 1 else current + duration * weight / denom
        result.append({"word": word, "start": round(current, 3), "end": round(finish, 3),
                       "method": "estimated"})
        current = finish
    return result


def _font(size: int, bold=False):
    from PIL import ImageFont
    candidates = (["/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else
                  ["/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for filename in candidates:
        if Path(filename).is_file():
            return ImageFont.truetype(filename, size)
    return ImageFont.load_default(size=size)


def _lines(draw, text, font, max_width, max_lines=6):
    out = []
    for para in text.split("\n"):
        buf = ""
        for part in para.split():
            attempt = (buf + " " + part).strip()
            if draw.textlength(attempt, font=font) > max_width and buf:
                out.append(buf)
                buf = part
            else:
                buf = attempt
        if buf:
            out.append(buf)
    return out[:max_lines]


def _slide(scene, output: Path, width: int, height: int, asset: Path | None) -> None:
    """Original editable-content slide; approved image appears inside browser mockup."""
    from PIL import Image, ImageDraw
    scale = width / 1920
    img = Image.new("RGB", (width, height), "#0B1321")
    d = ImageDraw.Draw(img)
    # Dark gradient + restrained geometric motion elements.
    for y in range(height):
        v = y / max(1, height)
        d.line((0, y, width, y), fill=(int(11 + 7*v), int(19 + 9*v), int(33 + 14*v)))
    accent = (70, 169, 208)
    pad = max(18, round(width * .065))
    d.rounded_rectangle((pad, max(12, round(height*.12)), pad+max(28,int(70*scale)), max(16,round(height*.12))+max(3,round(7*scale))), radius=3, fill=accent)
    label_font = _font(max(10,round(23*scale)),bold=True)
    title_font = _font(max(19,round((69 if scene["layout"] in {"hero", "quote"} else 54)*scale)),bold=True)
    body_font = _font(max(11,round(33*scale)))
    label = scene.get("eyebrow") or "MONEYPRINT  /  OPEN SOURCE"
    d.text((pad, round(height*.16)), label[:70].upper(), font=label_font, fill=(125, 203, 231))
    start_y = round(height*.27)
    text_width = round(width*.78) if not asset else round(width*.48)
    lines = _lines(d, scene["title"], title_font, text_width, 5)
    for line in lines:
        d.text((pad, start_y), line, font=title_font, fill=(241, 246, 252))
        start_y += round(title_font.size*1.23)
    # Use contextual, business-specific diagrams rather than generic filler cards.
    from scripts.studio_visuals import paint_layout
    paint_layout(img, scene, pad, start_y, width, height, asset is not None)
    if asset and asset.suffix.lower() in IMAGE_EXT:
        try:
            with Image.open(asset) as source:
                source = source.convert("RGB")
                bx, by = int(width*.53), int(height*.25)
                bw, bh = int(width*.41), int(height*.56)
                box = Image.new("RGB",(bw,bh),"#172536")
                cap = max(12,round(32*scale))
                thumb = source.copy()
                thumb.thumbnail((bw,bh-cap),Image.Resampling.LANCZOS)
                box.paste(thumb,((bw-thumb.width)//2,cap+(bh-cap-thumb.height)//2))
                d.rounded_rectangle((bx-6,by-6,bx+bw+6,by+bh+6),radius=max(8,round(17*scale)),fill=(63,104,135))
                img.paste(box,(bx,by))
                d = ImageDraw.Draw(img)
                for idx,col in enumerate(["#e07e81","#d8be7c","#77bfa4"]):
                    x=bx+round((17+17*idx)*scale)
                    d.ellipse((x,by+round(8*scale),x+round(9*scale),by+round(17*scale)),fill=col)
        except (OSError, ValueError) as exc:
            raise RenderError("Não foi possível ler imagem aprovada") from exc
    if scene["layout"] == "minimal":
        pass
    footer_font = _font(max(10,round(20*scale)))
    d.text((pad,height-round(height*.072)), "ARTISYS  ·  MONEYPRINT",font=footer_font,fill=(117,139,162))
    if scene.get("repo_url"):
        source=str(scene["repo_url"]).removeprefix("https://")[:65]
        label_width=d.textlength(source,font=footer_font)
        d.text((max(pad,width-pad-label_width),height-round(height*.072)),source,
               font=footer_font,fill=(160,189,207))
    output.parent.mkdir(parents=True,exist_ok=True)
    img.save(output)


def _run(command, text=None):
    try:
        subprocess.run(command, input=text.encode("utf-8") if text is not None else None, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=900)
    except subprocess.CalledProcessError as exc:
        raise RenderError((exc.stderr or b"").decode("utf-8","replace")[-1700:]) from exc


def _audio_seconds(path: Path) -> float:
    value=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
                                  "-of","default=noprint_wrappers=1:nokey=1",str(path)], text=True)
    return float(value.strip())


def render_project(project: dict, root: Path, output_dir: Path, *, voice: str="none",
                   voice_model: Path | None=None, width: int | None=None, height: int | None=None,
                   align_words: bool=False, capture_github: bool=False) -> dict:
    """Renders a frame-accurate MP4 and deterministic sidecar metadata.

    Voice 'piper' requires Piper and a local model path. No service or tokens.
    """
    plan=build_plan(project)
    root=root.resolve()
    output_dir=output_dir.resolve()
    ratio=plan["aspect"]
    default_dims={"16:9":(1920,1080),"9:16":(1080,1920),"1:1":(1080,1080)}[ratio]
    width=width or default_dims[0]
    height=height or default_dims[1]
    if width < 160 or height < 160 or width%2 or height%2:
        raise RenderError("Resolução inválida")
    if voice not in {"none","piper"}:
        raise RenderError("Narração inválida")
    if voice=="piper" and (voice_model is None or not voice_model.is_file()):
        raise RenderError("Informe um modelo Piper local válido")
    for a in plan["assets"].values():
        src=(root/a["path"]).resolve()
        if not src.is_relative_to((root/"assets").resolve()) or not src.is_file():
            raise RenderError("Mídia ausente ou fora de assets/: "+a["path"])
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch=output_dir/"studio_frames"
    scratch.mkdir(parents=True, exist_ok=True)
    github_stills = {}
    all_repos = list(dict.fromkeys(s.get("repo_url") for s in plan["scenes"] if s.get("repo_url")))
    if all_repos and capture_github:
        from scripts.repo_stills import capture_repo_stills
        try:
            captures = capture_repo_stills(all_repos, scratch/"github_captures")
            github_stills = {url: [Path(p) for p in paths] for url,paths in zip(all_repos,captures)}
        except Exception as exc:
            raise RenderError("Falha na captura real do GitHub: "+type(exc).__name__) from exc
    playlist=[]
    all_cues=[]
    warnings=[]
    credits=[]
    fps=plan["fps"]
    for index, scene in enumerate(plan["scenes"],1):
        count=scene["duration_frames"]
        duration=count/fps
        asset_meta=plan["assets"].get(scene.get("asset_id"))
        asset=(root/asset_meta["path"]).resolve() if asset_meta else None
        if asset_meta:
            credits.append({"scene":scene["id"],"file":asset_meta["path"],
                            "license":asset_meta["license"],"attribution":asset_meta["attribution"]})
        art=scratch/f"slide_{index:03d}.png"
        # Video assets are used as moving background, stills inside a browser-like card.
        image_asset=asset if asset and asset.suffix.lower() in IMAGE_EXT else None
        repo_url=scene.get("repo_url")
        if repo_url and not image_asset and github_stills.get(repo_url):
            image_asset=github_stills[repo_url][(index-1)%len(github_stills[repo_url])]
            credits.append({"scene":scene["id"],"source_url":repo_url,
                            "attribution":"Captura Playwright de repositório público", "type":"github_screenshot"})
        _slide(scene,art,width,height,image_asset)
        narration=None
        tempo=1.0
        if voice=="piper":
            narration=scratch/f"voice_{index:03d}.wav"
            _run(["piper","--model",str(voice_model),"--output_file",str(narration)], text=scene["text"])
            spoken=_audio_seconds(narration)
            tempo=max(1.0,spoken/max(0.1,duration-0.15))
            if tempo>1.25:
                warnings.append({"scene":scene["id"],"type":"voice_tempo_high","tempo":round(tempo,2)})
            if tempo>2.0:
                raise RenderError("Narração longa demais para a cena "+scene["id"]+"; aumente a duração")
        out=scratch/f"clip_{index:03d}.mp4"
        moving=asset is not None and asset.suffix.lower() in VIDEO_EXT
        if moving:
            base=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-stream_loop","-1","-i",str(asset),"-loop","1","-framerate",str(fps),"-i",str(art)]
            vf=(f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},fps={fps},format=yuv420p[video];"
                f"[1:v]format=rgba,colorchannelmixer=aa=0.22[overlay];"
                f"[video][overlay]overlay=0:0:shortest=1,format=yuv420p[v]")
        else:
            base=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-loop","1","-framerate",str(fps),"-i",str(art)]
            # Animate the composed slide very gently; avoid fake full-screen scrolling.
            vf=(f"[0:v]scale={width}:{height},"
                f"zoompan=z='min(zoom+0.0005,1.045)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={width}x{height}:fps={fps},format=yuv420p[v]")
        if narration:
            base += ["-i",str(narration)]
            audio_idx=2 if moving else 1
            af=f"[{audio_idx}:a]aresample=48000,atempo={tempo:.5f},apad,atrim=0:{duration:.6f}[a]"
        else:
            base += ["-f","lavfi","-i","anullsrc=r=48000:cl=stereo"]
            audio_idx=2 if moving else 1
            af=f"[{audio_idx}:a]atrim=0:{duration:.6f}[a]"
        _run(base+["-filter_complex",vf+";"+af,"-map","[v]","-map","[a]",
                   "-frames:v",str(count),"-t",f"{duration:.6f}","-r",str(fps),
                   "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
                   "-c:a","aac","-b:a","128k","-ar","48000","-movflags","+faststart",str(out)])
        playlist.append(out)
        all_cues.extend(word_cues(scene["text"],scene["start_frame"]/fps,duration))
    concat=scratch/"concat.txt"
    concat.write_text("".join("file '"+str(path).replace("'", "'\\''")+"'\n" for path in playlist),encoding="utf-8")
    target=output_dir/"studio_final.mp4"
    _run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-f","concat",
          "-safe","0","-i",str(concat),"-c","copy","-movflags","+faststart",str(target)])
    # Read back actual video frames, not just requested duration.
    info=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames",
        "-select_streams","v:0","-show_entries","stream=nb_read_frames",
        "-of","json",str(target)],text=True))
    actual=int(info["streams"][0]["nb_read_frames"])
    if actual!=plan["total_frames"]:
        raise RenderError(f"MP4 diverge da timeline: {actual} != {plan['total_frames']} frames")
    mode="estimated"
    if align_words and voice=="piper":
        try:
            from faster_whisper import WhisperModel
            model=WhisperModel("tiny",device="cpu",compute_type="int8")
            transcribed,_=model.transcribe(str(target),word_timestamps=True,language="pt")
            measured=[]
            for item in transcribed:
                for word in item.words or []:
                    measured.append({"word":word.word.strip(),"start":round(word.start,3),
                                     "end":round(word.end,3),"method":"whisper_word_timestamps"})
            if measured:
                all_cues=measured
                mode="whisper_word_timestamps"
        except Exception as exc:
            warnings.append({"type":"word_alignment_unavailable","reason":type(exc).__name__})
    credits_path=output_dir/"creditos.json"
    credits_path.write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
    (output_dir/"palavras.json").write_text(json.dumps({"method":mode,"cues":all_cues},ensure_ascii=False,indent=2),encoding="utf-8")
    result={"status":"ok","output":str(target),"fps":fps,"total_frames":actual,
            "duration_seconds":plan["duration_seconds"],"word_alignment":mode,
            "credits":str(credits_path),"warnings":warnings,"voice":voice,"autopublish":False}
    (output_dir/"diagnostico.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser(description="MoneyPrint Studio V3 — renderização canônica")
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--root",type=Path,default=Path.cwd())
    p.add_argument("--voice",choices=["none","piper"],default="none")
    p.add_argument("--voice-model",type=Path)
    p.add_argument("--align-words",action="store_true")
    p.add_argument("--capture-github",action="store_true")
    a=p.parse_args()
    data=json.loads(a.input.read_text(encoding="utf-8"))
    print(json.dumps(render_project(data,a.root,a.output,voice=a.voice,
            voice_model=a.voice_model,align_words=a.align_words,capture_github=a.capture_github),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()