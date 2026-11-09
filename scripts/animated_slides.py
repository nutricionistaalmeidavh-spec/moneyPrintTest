"""Motion-first slide editor for MoneyPrint: graphics lead, authentic media supports.

Generates legible dark-brand slides and animated reveals. Images/GIFs, original
project screenshots and licensed b-roll appear inside a browser-style mockup;
real GitHub screen recordings are not used as the primary visual layer.
Only stdlib, Pillow and FFmpeg required; no paid dependency.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, FPS = 1920, 1080, 24
BG = (11, 15, 30)
PANEL = (21, 27, 49)
INK = (238, 239, 252)
MUTED = (165, 170, 196)
ACCENT = (163, 138, 245)
CYAN = (94, 204, 218)

# Editorial statements, not hard-coded news or performance claims.
STORIES = {
    "appwrite": ("Backend sem retrabalho", ("Aplicativo", "Autenticação", "Banco e arquivos"),
                 "Uma base para desenvolver aplicações sem recomeçar tudo."),
    "payload": ("Conteúdo sob controle", ("Editor", "Payload CMS", "Site e API"),
                "Páginas e catálogos editáveis em uma única estrutura."),
    "flowise": ("Automação visual de IA", ("Entrada", "Fluxo visual", "Resposta"),
                "Organize componentes de IA e acompanhe o caminho dos dados."),
    "docling": ("Documentos viram dados", ("Documento", "Extração", "Dados estruturados"),
                "Transforme arquivos em informação que pode ser conferida."),
    "meilisearch": ("Encontre em segundos", ("Catálogo", "Indexação", "Pesquisa"),
                    "Busca mais útil para aplicações cheias de registros."),
    "keycloak": ("Identidade organizada", ("Usuário", "Login central", "Acesso"),
                 "Gerencie autenticação e permissões entre aplicações."),
    "novu": ("Notificações em fluxo", ("Evento", "Orquestração", "Mensagem"),
             "Entregue mensagens na etapa certa da experiência."),
    "infisical": ("Segredos protegidos", ("Chave", "Cofre", "Aplicação"),
                  "Separe credenciais do código e controle seu acesso."),
}


def font(size: int, semibold=False) -> ImageFont.FreeTypeFont:
    candidates = (
        ("/usr/share/fonts/truetype/lato/Lato-Semibold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if semibold else
        ("/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    for name in candidates:
        if Path(name).exists():
            return ImageFont.truetype(name, max(9, size))
    return ImageFont.load_default()


def story_for(section: dict) -> tuple[str, tuple[str, str, str], str]:
    key = section["repo_url"].rstrip("/").split("/")[-1].casefold()
    if key in STORIES:
        return STORIES[key]
    return ("Como funciona", ("Entrada", section["title"], "Resultado"),
            "Explore a documentação e as possibilidades do projeto.")


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int,int],
          value: str, size: int, color=INK, *, weight=False,
          max_width: int | None = None, max_lines=3) -> None:
    f = font(size, weight)
    if not max_width:
        draw.text(xy, value, font=f, fill=color)
        return
    words = value.split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if draw.textbbox((0,0),trial,font=f)[2] <= max_width:
            current = trial
        else:
            if current: lines.append(current)
            current = word
        if len(lines) >= max_lines: break
    if current and len(lines) < max_lines:
        lines.append(current)
    for i, line in enumerate(lines):
        draw.text((xy[0],xy[1]+i*(size+12)),line,font=f,fill=color)


def _canvas(size: tuple[int,int]):
    # Muted indigo gradient. No fades-to-white, full-screen browser windows,
    # overexposed stock "monitor" shots or unreadable neon fonts.
    w,h=size
    im=Image.new("RGB",size,BG)
    d=ImageDraw.Draw(im)
    for y in range(h):
        v=y/max(1,h-1)
        d.line((0,y,w,y),fill=(int(11+10*v),int(15+11*v),int(30+19*v)))
    d.ellipse((int(.62*w),int(-.7*h),int(1.5*w),int(.48*h)),
              fill=(25,29,57))
    d.ellipse((int(-.48*w),int(.69*h),int(.16*w),int(1.37*h)),
              fill=(18,26,48))
    return im,d


def _round_panel(d, box, fill=PANEL, radius=24, border=None):
    d.rounded_rectangle(box, radius=radius, fill=fill,
                        outline=border or (43,47,75), width=2)


def _header(d, title, index, total, size):
    w,h=size; s=w/1920
    _text(d,(int(90*s),int(65*s)),"ARTISYS  /  OPEN SOURCE",int(25*s),ACCENT,weight=True)
    _text(d,(int(90*s),int(145*s)),title,int(67*s),INK,weight=True,
          max_width=int(1640*s),max_lines=1)
    _text(d,(int(1640*s),int(79*s)),f"{index:02d} / {total:02d}",
          int(24*s),MUTED)
    d.line((int(90*s),int(245*s),int((w-90*s)),int(245*s)),
           fill=(55,59,87),width=max(1,int(2*s)))


def _foot(d, section, size):
    w,h=size;s=w/1920
    url=section["repo_url"].replace("https://","")
    _text(d,(int(92*s),int(h-85*s)),url,int(24*s),MUTED)


def _mockup(im:Image.Image, picture:Path | None, size:tuple[int,int]) -> None:
    """Embed authentic screenshot in a browser card, never full-bleed."""
    w,h=size; s=w/1920
    x0,y0,x1,y1=[int(v*s) for v in (485,288,1810,934)]
    d=ImageDraw.Draw(im)
    _round_panel(d,(x0,y0,x1,y1),(19,24,43),int(28*s),border=(72,72,110))
    d.rounded_rectangle((x0+int(20*s),y0+int(18*s),
                         x1-int(20*s),y0+int(70*s)),
                        radius=int(12*s),fill=(32,37,61))
    for i,c in enumerate(((218,109,116),(224,183,91),(115,199,150))):
        radius=int(9*s);cx=x0+int((55+31*i)*s);cy=y0+int(44*s)
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=c)
    _text(d,(x0+int(193*s),y0+int(27*s)),"github.com  /  projeto",int(23*s),MUTED)
    area=(x0+int(24*s),y0+int(90*s),x1-int(24*s),y1-int(25*s))
    if picture and Path(picture).is_file():
        try:
            with Image.open(picture) as sample:
                sample=ImageOps.fit(sample.convert("RGB"),
                                    (area[2]-area[0],area[3]-area[1]),
                                    method=Image.Resampling.LANCZOS,
                                    centering=(.5,.17))
                im.paste(sample,(area[0],area[1]))
        except (OSError,ValueError):
            pass
    else:
        ImageDraw.Draw(im).rounded_rectangle(area, radius=int(12*s),
                                             fill=(29,36,58))


def make_slide(section:dict, index:int, total:int, kind:str, target:Path, *,
               stage=0, picture:Path|None=None, size=(W,H)):
    w,h=size;s=w/1920
    im,d=_canvas(size)
    headline,steps,summary=story_for(section)
    _header(d,section["title"],index,total,size)
    if kind=="intro":
        _text(d,(int(98*s),int(345*s)),"8 REPOSITÓRIOS",int(94*s),INK,weight=True)
        _text(d,(int(100*s),int(488*s)),"Uma ideia vira software.",int(49*s),ACCENT)
        _text(d,(int(105*s),int(590*s)),"Demonstrações reais e aplicações práticas.",
              int(36*s),MUTED)
    elif kind=="benefit":
        _text(d,(int(100*s),int(365*s)),headline,int(68*s),INK,weight=True,
              max_width=int(1650*s))
        _text(d,(int(108*s),int(500*s)),summary,int(40*s),MUTED,
              max_width=int(1480*s))
        d.rounded_rectangle((int(105*s),int(640*s),int(900*s),int(650*s)),
                            radius=int(5*s),fill=ACCENT)
    elif kind=="flow":
        _text(d,(int(102*s),int(310*s)),"COMO FUNCIONA",int(29*s),ACCENT,
              weight=True)
        card_width=int(490*s)
        gap=int(80*s)
        left=int(96*s)
        top=int(445*s)
        bottom=int(765*s)
        for n,label in enumerate(steps):
            x=left+n*(card_width+gap)
            active=n<=stage
            _round_panel(d,(x,top,x+card_width,bottom),
                         (31,39,71) if active else (18,25,45),
                         int(24*s),
                         border=(150,120,220) if active else (54,62,84))
            if active:
                _text(d,(x+int(33*s),top+int(43*s)),f"0{n+1}",
                      int(36*s),ACCENT,weight=True)
                _text(d,(x+int(33*s),top+int(150*s)),label,
                      int(37*s),INK,weight=True,max_width=card_width-int(65*s),
                      max_lines=2)
            else:
                _text(d,(x+int(33*s),top+int(43*s)),f"0{n+1}",
                      int(36*s),(82,90,121))
            if n<2:
                ax=x+card_width+int(22*s);ay=(top+bottom)//2
                d.line((ax,ay,ax+int(38*s),ay),fill=ACCENT if stage>n else
                       (72,76,105),width=max(2,int(5*s)))
                d.polygon([(ax+int(37*s),ay-int(10*s)),
                           (ax+int(37*s),ay+int(10*s)),
                           (ax+int(49*s),ay)],fill=ACCENT if stage>n else
                          (72,76,105))
    elif kind in ("mockup","demo","clip","broll"):
        _text(d,(int(100*s),int(366*s)),"NA PRÁTICA" if kind in ("mockup","demo","clip") else "USO REAL",int(29*s),ACCENT,weight=True)
        _text(d,(int(100*s),int(470*s)),headline,int(42*s),INK,weight=True,
              max_width=int(330*s),max_lines=4)
        _text(d,(int(100*s),int(720*s)),"Interface e documentação oficiais",
              int(25*s),MUTED,max_width=int(320*s))
        _mockup(im,picture,size)
    elif kind=="use":
        _text(d,(int(100*s),int(350*s)),"ONDE APLICAR",int(29*s),ACCENT,weight=True)
        _text(d,(int(100*s),int(468*s)),summary,int(53*s),INK,
              weight=True,max_width=int(1580*s),max_lines=3)
    else:
        raise ValueError("Cena inválida")
    _foot(ImageDraw.Draw(im),section,size)
    target.parent.mkdir(parents=True,exist_ok=True)
    im.save(target,compress_level=4)
    return target


def scene_plan(duration:float, have_pictures=True, first=False)->list[tuple[str,int,float]]:
    """Sequential revealed diagrams; the visual cadence follows narration length."""
    if duration<5:raise ValueError("Narração curta demais")
    scenes=[("benefit",0,1.3),("flow",0,1.0),("flow",1,1.0),
            ("flow",2,1.1),("mockup",0,1.8 if have_pictures else 1.0),
            ("use",0,1.0),("mockup",1,1.2 if have_pictures else .8)]
    if first:
        scenes.insert(0,("intro",0,.6))
    factor=duration/sum(x[2] for x in scenes)
    return [(kind,stage,weight*factor) for kind,stage,weight in scenes]


def _render_animated_video(
        slides:list[tuple[Path,float,Path|None]], audio:Path,
        target:Path, *,size=(W,H),fps=FPS):
    """Concatenate dark motion slides and optional real media in an inset mockup.

    There are no crossfades through white or fullscreen stock monitor footage.
    """
    if not slides: raise ValueError("Nenhuma cena")
    inputs=[]
    filters=[]
    width,height=size
    input_count=0
    for i,(asset,seconds,clip) in enumerate(slides):
        root=input_count
        inputs+=["-loop","1","-framerate",str(fps),"-i",str(asset)]
        input_count+=1
        filters.append(
            f"[{root}:v]scale={int(width*1.035)}:{int(height*1.035)}:flags=lanczos,"
            f"crop={width}:{height}:"
            "x='(in_w-out_w)/2+9*sin(t*0.9)':"
            "y='(in_h-out_h)/2+7*cos(t*0.65)',"
            f"fps={fps},trim=duration={seconds:.5f},"
            f"setpts=PTS-STARTPTS,format=yuv420p[base{i}]")
        if clip and clip.is_file():
            source=input_count
            inputs+=["-stream_loop","-1","-i",str(clip)]
            input_count+=1
            # The browser/film mockup spans x=485..1810, y=288..934.
            # Place the moving image inside its viewport, never full-bleed.
            inset_w=int(width*(1325-48)/1920)
            inset_h=int(width*(646-116)/1920)
            pos_x=int(width*(485+24)/1920)
            pos_y=int(width*(288+90)/1920)
            filters.append(
                f"[{source}:v]fps={fps},"
                f"scale={inset_w}:{inset_h}:force_original_aspect_ratio=decrease,"
                f"pad={inset_w}:{inset_h}:(ow-iw)/2:(oh-ih)/2:color=0x11192f,"
                f"trim=duration={seconds:.5f},setpts=PTS-STARTPTS[real{i}]")
            filters.append(f"[base{i}][real{i}]overlay={pos_x}:{pos_y}:"
                           f"shortest=1:format=auto,format=yuv420p[v{i}]")
        else:
            filters.append(f"[base{i}]null[v{i}]")
    audio_index=input_count
    inputs+=["-i",str(audio)]
    filters.append("".join(f"[v{i}]" for i in range(len(slides)))+
                   f"concat=n={len(slides)}:v=1:a=0[video]")
    total=sum(t for _,t,_ in slides)
    target.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        *inputs,"-filter_complex",";".join(filters),"-map","[video]",
        "-map",f"{audio_index}:a:0","-t",f"{total:.3f}",
        "-c:v","libx264","-preset","veryfast","-crf","23",
        "-pix_fmt","yuv420p","-threads","2",
        "-c:a","aac","-b:a","144k",
        "-movflags","+faststart",str(target)
    ],check=True,timeout=1800)
    if target.stat().st_size<10000:
        raise RuntimeError("Vídeo de slides inválido")



def render_animated_section(section:dict,index:int,total:int,audio:Path,
                            duration:float,folder:Path,*,screenshots:list[str]|None=None,
                            media:list[dict]|None=None,size=(W,H)) -> dict:
    """Full animated chapter, with real images and optional GIF/video footage."""
    images=[Path(x) for x in screenshots or [] if Path(x).is_file()]
    video_assets=[x for x in (media or []) if
                  Path(x.get("path","")).is_file()
                  and Path(x["path"]).suffix.lower() in (".mp4",".webm",".mov")]
    plan=scene_plan(duration,have_pictures=bool(images),first=index==1)
    if video_assets:
        # A supporting 4-second video/gif only after the explanatory diagram.
        insertion=min(5,len(plan))
        plan.insert(insertion,("clip",0,0.0))
        # Allocate some of the adjacent static-slide duration to that video.
        allotted=min(5.0, max(2.0,duration*0.12))
        factor=(duration-allotted)/(sum(x[2] for x in plan))
        plan=[(k,st,(allotted if k=="clip" else weight*factor))
              for k,st,weight in plan]
    slides=[]
    records=[]
    for j,(kind,stage,seconds) in enumerate(plan):
        pic=(images[stage%len(images)] if images and kind=="mockup" else None)
        clip=(Path(video_assets[0]["path"]) if kind=="clip" and video_assets else None)
        file=folder/f"slide_{j:02d}.png"
        make_slide(section,index,total,kind,file,stage=stage,picture=pic,size=size)
        slides.append((file,seconds,clip))
        records.append({"kind":kind,"stage":stage,"duration":round(seconds,3),
                        "screenshot":str(pic) if pic else None,
                        "video":str(clip) if clip else None})
    movie=folder/"chapter.mp4"
    _render_animated_video(slides,audio,movie,size=size)
    manifest={"chapter":index,"duration":duration,"shots":records,
              "render_style":"motion_slides","video":str(movie)}
    (folder/"slides.json").write_text(json.dumps(manifest,ensure_ascii=False,
                                                 indent=2),encoding="utf-8")
    return manifest
