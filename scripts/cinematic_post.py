"""Cinematic post-production for MoneyPrint, with licensed contextual B-roll.

Standalone mode also remasters an existing recording without changing its voice.
Uses only Python stdlib + FFmpeg/libass and system open-source fonts; no paid API.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

# Professional editorial typography with distro font fallbacks.
FONT_FAMILY = "Inter"
FONT_FALLBACK = "DejaVu Sans"
BACKEND_LABELS = {
    "appwrite": ("Appwrite", "Backend completo", "backend"),
    "payload": ("Payload CMS", "Conteúdo e APIs", "cms"),
    "flowise": ("Flowise", "Agentes e fluxos de IA", "ai"),
    "docling": ("Docling", "Documentos estruturados", "documents"),
    "meilisearch": ("Meilisearch", "Busca inteligente", "search"),
    "keycloak": ("Keycloak", "Identidade e acesso", "security"),
    "novu": ("Novu", "Notificações multicanal", "notifications"),
    "infisical": ("Infisical", "Segredos protegidos", "secrets"),
}
BROLL_TERMS = {
    "backend": ["software development typing", "computer work"],
    "cms": ["editing documents computer", "typing laptop"],
    "ai": ["computer automation", "software engineering"],
    "documents": ["paper scanner", "document scanner"],
    "search": ["computer search typing", "search engine"],
    "security": ["data center servers", "computer security"],
    "notifications": ["mobile phone notification", "phone applications"],
    "secrets": ["computer server room", "encryption computer"],
    "general": ["programming computer", "technology workspace"],
}

class CinematicError(ValueError):
    pass


def check_chapters(timeline: object, count: int, duration: float) -> list[float]:
    """Explicit synchronization map for an existing narratively edited video."""
    if timeline is None:
        start, end = min(10, duration * .06), duration - min(7, duration * .07)
        step = (end - start) / count
        return [start + i * step for i in range(count)] + [end]
    if not isinstance(timeline, list) or len(timeline) != count + 1:
        raise CinematicError("chapter_starts: esperado um início por repo mais o início do encerramento")
    if any(type(t) not in (int, float) for t in timeline):
        raise CinematicError("Tempos devem ser números")
    values = [float(t) for t in timeline]
    if values[0] < 0 or values[-1] >= duration or any(b <= a for a,b in zip(values, values[1:])):
        raise CinematicError("Tempos de capítulos fora de ordem ou da duração")
    return values


def sanitize_label(text: str, limit: int = 100) -> str:
    if not isinstance(text, str):
        raise CinematicError("Rótulo inválido")
    result = re.sub(r"[\u0000-\u001f\u007f]", " ", text).strip()
    if not result or len(result) > limit:
        raise CinematicError("Texto do cartão inválido")
    return result


def metadata_for_repo(url: str) -> dict:
    split = urlsplit(url)
    if split.scheme != "https" or split.netloc != "github.com":
        raise CinematicError("URL de repositório não permitida")
    parts = split.path.strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise CinematicError("Use somente a página raiz do repositório")
    slug = parts[-1].lower()
    label = BACKEND_LABELS.get(slug, (parts[-1], "Projeto open source", "general"))
    return {"title": sanitize_label(label[0], 45),
            "subtitle": sanitize_label(label[1], 90), "category": label[2],
            "url": url}


def cinematic_plan(urls: list[str], duration: float,
                   chapter_starts: list[float] | None = None) -> list[dict]:
    if not isinstance(urls, list) or not 1 <= len(urls) <= 12:
        raise CinematicError("Informe de 1 a 12 repositórios")
    chapters = check_chapters(chapter_starts, len(urls), duration)
    plan = []
    for i,url in enumerate(urls):
        record = metadata_for_repo(url)
        start, end = chapters[i:i+2]
        record.update(index=i+1, start=start, end=end,
                      broll_start=start+min(4.0, (end-start)*.15),
                      broll_seconds=min(4.5, max(0.0, end-start-7.0)))
        plan.append(record)
    return plan


def probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)],
        capture_output=True,text=True,check=True,timeout=30)
    value = float(result.stdout.strip())
    if not 3 <= value <= 3600:
        raise CinematicError("Vídeo fonte de duração inválida")
    return value


def ass_timestamp(seconds: float) -> str:
    cs = int(max(0, seconds) * 100)
    return f"{cs // 360000}:{(cs // 6000)%60:02d}:{(cs // 100)%60:02d}.{cs%100:02d}"


def ass_safe(value: str) -> str:
    """Escape user-supplied labels so ASS drawing or animation can't be injected."""
    return (sanitize_label(value).replace("\\", "＼").replace("{", "（")
            .replace("}", "）").replace(",", "，"))


def build_ass(plan: list[dict], duration: float, size=(1920,1080)) -> str:
    w,h=size
    sc=w/1920
    title_size=int(52*sc)
    sub_size=int(27*sc)
    tag_size=int(22*sc)
    x=int(95*sc)
    y=int(h-262*sc)
    events=[]
    def event(a,b,style,body):
        events.append(f"Dialogue: 0,{ass_timestamp(a)},{ass_timestamp(b)},{style},,0,0,0,,{body}")
    event(.2,min(duration,5.2),"Title",
          r"{\an7\pos("+str(x)+","+str(y)+r")\fad(250,250)}"
          +ass_safe("8 PROJETOS. MUITAS POSSIBILIDADES."))
    for item in plan:
        start,end=item["start"],item["end"]
        length=end-start
        stop=min(end-.2,start+min(8.8,length*.36))
        if stop <= start:continue
        # Built-in ASS alpha masks provide a translucent, subtle editorial card.
        bx=int(73*sc);by=int(h-295*sc);bw=int(960*sc);bh=int(235*sc)
        event(start,stop,"Shape",
              "{\\an7\\pos("+str(bx)+","+str(by)+")\\fad(220,300)\\p1\\1c&H21121E&\\1a&H27&}"
              +f"m 0 0 l {bw} 0 l {bw} {bh} l 0 {bh} ")
        event(start+.10,stop,"Tag",
              "{\\an7\\pos("+str(x)+","+str(y)+")\\fad(220,250)}"
              +ass_safe(f"REPOSITÓRIO  {item['index']:02d} / {len(plan):02d}"))
        event(start+.22,stop,"Title",
              "{\\an7\\pos("+str(x)+","+str(y+45*sc)+")\\fad(240,250)}"
              +ass_safe(item["title"]))
        event(start+.35,stop,"Subtitle",
              "{\\an7\\pos("+str(x)+","+str(y+112*sc)+")\\fad(250,250)}"
              +ass_safe(item["subtitle"]))
    tail=max(0,duration-6)
    event(tail,duration-.15,"Title",
          "{\\an7\\pos("+str(x)+","+str(y)+")\\fad(260,350)}"
          +ass_safe("DESCUBRA. TESTE. CONSTRUA."))
    styles=[
        f"Style: Title,{FONT_FAMILY},{title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,7,10,10,10,1",
        f"Style: Subtitle,{FONT_FAMILY},{sub_size},&H00DDDAFA,&H00DDDAFA,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,10,10,10,1",
        f"Style: Tag,{FONT_FAMILY},{tag_size},&H00EEB8C8,&H00EEB8C8,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,10,10,10,1",
        "Style: Shape,Arial,16,&H00381D20,&H00381D20,&H00381D20,&H00381D20,0,0,0,0,100,100,0,0,1,0,0,7,10,10,10,1"
    ]
    return ("\n".join(["[Script Info]","ScriptType: v4.00+",
             f"PlayResX: {w}",f"PlayResY: {h}","ScaledBorderAndShadow: yes",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"]
             +styles+["[Events]",
              "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
             +events)+"\n")


def render_cinematic(source: Path, target: Path, repo_urls: list[str], *,
                     broll_paths: dict[int, Path] | None = None,
                     chapter_starts: list[float] | None = None,
                     size=(1920,1080), quality="veryfast") -> dict:
    source,target=Path(source),Path(target)
    if not source.is_file():
        raise CinematicError("Vídeo original ausente")
    if len(size)!=2 or size[0] < 640 or size[1] < 360:
        raise CinematicError("Resolução inválida")
    duration=probe_duration(source)
    plan=cinematic_plan(repo_urls,duration,chapter_starts)
    target.parent.mkdir(parents=True,exist_ok=True)
    ass=target.parent/"cinematic_titles.ass"
    ass.write_text(build_ass(plan,duration,size),encoding="utf-8")
    width,height=size
    filters=[f"[0:v]scale={width}:{height}:flags=lanczos,setsar=1,format=yuv420p[base]"]
    current="base"
    inputs=["-i",str(source)]
    broll_paths=broll_paths or {}
    used=[]
    for item in plan:
        candidate=broll_paths.get(item["index"])
        if not candidate or item["broll_seconds"] < 1.5:continue
        candidate=Path(candidate)
        if not candidate.is_file():continue
        idx=len(inputs)//2
        inputs+=["-i",str(candidate)]
        name=f"br{idx}"
        offset=item["broll_start"]
        seconds=item["broll_seconds"]
        filters.append(f"[{idx}:v]trim=duration={seconds:.3f},setpts=PTS-STARTPTS+{offset:.3f}/TB,"
                       f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                       f"crop={width}:{height},setsar=1,format=yuv420p[{name}]")
        new=f"comp{idx}"
        filters.append(f"[{current}][{name}]overlay=0:0:enable='between(t,{offset:.3f},{offset+seconds:.3f})':eof_action=pass[{new}]")
        current=new
        used.append({"index":item["index"],"file":str(candidate),"start":offset,
                     "seconds":seconds})
    # ASS is added last so animated title stays legible on top of B-roll.
    escaped=str(ass.resolve()).replace("\\","\\\\").replace(":","\\:")
    filters.append(f"[{current}]ass=filename='{escaped}',format=yuv420p[out]")
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",*inputs,
         "-filter_complex",";".join(filters),"-map","[out]","-map","0:a?",
         "-t",f"{duration:.3f}","-c:v","libx264","-preset",quality,"-crf","22",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","160k",
         "-movflags","+faststart",str(target)]
    try:
        subprocess.run(cmd,check=True,timeout=2400)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
        target.unlink(missing_ok=True)
        raise
    if not target.is_file() or target.stat().st_size < 4000:
        raise RuntimeError("Render cinematográfico não produziu MP4 válido")
    result={"source":str(source),"output":str(target),"duration":duration,
            "resolution":list(size),"repos":plan,"broll_used":used}
    (target.parent/"cinematic_manifest.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--repos-json",type=Path,required=True)
    parser.add_argument("--chapters-json",type=Path)
    parser.add_argument("--broll-json",type=Path)
    args=parser.parse_args()
    repo_urls=json.loads(args.repos_json.read_text(encoding="utf-8"))
    chapter_starts=(json.loads(args.chapters_json.read_text(encoding="utf-8"))
                    if args.chapters_json else None)
    broll=(json.loads(args.broll_json.read_text(encoding="utf-8"))
           if args.broll_json else {})
    render_cinematic(args.source,args.output,repo_urls,
                     broll_paths={int(k):Path(v) for k,v in broll.items()},
                     chapter_starts=chapter_starts)


if __name__=="__main__":
    main()
