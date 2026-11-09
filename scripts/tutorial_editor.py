"""MoneyPrint: edicao segura de tutoriais gravados, com FFmpeg e Pillow.
Uso: python scripts/tutorial_editor.py --source gravacao.mp4 --recipe tutorials/github_primeiro_repositorio.json --output final.mp4
A gravacao original NAO eh enviada a servicos ou anexada ao repositorio.
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path

class RecipeError(ValueError):
    pass

SIZE = (720, 1280)
FPS = 24
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def clean_text(s, max_len=110):
    if not isinstance(s, str) or not 1 <= len(s.strip()) <= max_len or any(ord(c) < 32 for c in s):
        raise RecipeError("Texto invalido na receita")
    return s.strip()

def validate_recipe(recipe, *, duration, resolution):
    if not isinstance(recipe, dict) or recipe.get("format") != "9:16":
        raise RecipeError("Receita precisa ser 9:16")
    if recipe.get("source_resolution") != list(resolution):
        raise RecipeError("Resolucao alterada: revise as mascaras da gravacao")
    clean_text(recipe.get("title"), 180)
    for kind in ("hook", "outro"):
        lines = recipe.get(kind)
        if not isinstance(lines, list) or not 1 <= len(lines) <= 4:
            raise RecipeError(kind + " deve ter 1-4 frases")
        for line in lines:
            clean_text(line, 75)
    masks = recipe.get("privacy_masks")
    if not isinstance(masks, list) or not masks:
        raise RecipeError("privacy_masks obrigatorio para revisar dados sensiveis")
    for mask in masks:
        fields = ("start", "end", "x", "y", "width", "height")
        if not isinstance(mask, dict) or any(type(mask.get(f)) not in (int, float) for f in fields):
            raise RecipeError("Mascara invalida")
        if (not 0 <= mask["start"] < mask["end"] <= duration + 0.25
            or min(mask["x"], mask["y"]) < 0 or min(mask["width"], mask["height"]) <= 0
            or mask["x"] + mask["width"] > resolution[0]
            or mask["y"] + mask["height"] > resolution[1]):
            raise RecipeError("Mascara fora do video")
    clips = recipe.get("clips")
    if not isinstance(clips, list) or not 1 <= len(clips) <= 20:
        raise RecipeError("Receita deve conter 1-20 takes")
    prior = -1
    for c in clips:
        if not isinstance(c, dict) or any(type(c.get(k)) not in (int, float) for k in ("start", "end", "speed")):
            raise RecipeError("Take invalido")
        if not 0 <= c["start"] < c["end"] <= duration or not 1 <= c["speed"] <= 3.5 or c["start"] < prior:
            raise RecipeError("Cortes sobrepostos ou fora de intervalo")
        prior = c["end"]
        if "caption" in c:
            clean_text(c["caption"], 48)  # validate, never render text
        for m in masks:
            if c["start"] < m["end"] and c["end"] > m["start"]:
                if not (m["start"] <= c["start"] and m["end"] >= c["end"]):
                    raise RecipeError("mascara parcial em um take: cubra todo o take")
    return recipe

def masks_for_clip(recipe, clip):
    return [m for m in recipe["privacy_masks"] if clip["start"] < m["end"] and clip["end"] > m["start"]]

def probe(path):
    data = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)], text=True))
    s = data["streams"][0]
    return float(data["format"]["duration"]), (s["width"], s["height"])

def call(argv):
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL)

def face(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT, size)

def fitting(draw, txt, available, size=60):
    while size > 21:
        f = face(size)
        if draw.textbbox((0, 0), txt, font=f)[2] <= available:
            return f
        size -= 2
    return face(22)

def title_image(path, lines):
    from PIL import Image, ImageDraw
    w, h = SIZE
    img = Image.new("RGB", SIZE)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        p = y / h
        draw.line((0, y, w, y), fill=(int(16+44*(1-p)), int(12+65*p), int(47+95*p)))
    draw.rounded_rectangle((45, 80, 675, 168), radius=25, fill=(18, 22, 53), outline=(73, 242, 221), width=3)
    draw.text((w//2, 124), "ARTISYS  /  MONEYPRINT", font=face(25), anchor="mm", fill=(125, 255, 232))
    base_y = 450 if len(lines) <= 3 else 400
    for i, word in enumerate(lines):
        txt = clean_text(word, 75)
        highlight = "GITHUB" in txt.upper() or txt.upper() == "PRONTO!"
        draw.text((w//2, base_y + i*108), txt,
                  font=fitting(draw,txt,w-65), anchor="mm",
                  fill=(68,245,218) if highlight else (250,252,255),
                  stroke_width=2, stroke_fill=(9,15,42))
    draw.rounded_rectangle((270, 970, 450, 978), radius=4, fill=(84,243,219))
    draw.text((w//2, 1050), "TUTORIAL RAPIDO  /  9:16",
              font=face(22), anchor="mm", fill=(204,220,233))
    img.save(path)

def caption_image(path, label, i, total):
    from PIL import Image, ImageDraw
    w,h=SIZE
    im=Image.new("RGBA", SIZE, (0,0,0,0))
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((25,68,w-25,152), radius=24, fill=(6,11,27,230), outline=(77,240,218,155), width=2)
    d.text((54,110),f"PASSO {i:02d}/{total:02d}",font=face(29),anchor="lm",fill=(116,253,226,255))
    d.rounded_rectangle((20,1104,w-20,1200),radius=22,fill=(4,8,22,245),outline=(102,94,205,160),width=2)
    d.text((w//2,1152),label,font=fitting(d,label,w-70,39),anchor="mm",fill=(255,255,255,255))
    im.save(path)

def still(image, seconds, target):
    call(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-loop","1","-framerate",str(FPS),"-i",str(image),"-t",str(seconds),
          "-vf",f"fade=t=in:st=0:d=0.12,fade=t=out:st={seconds-0.2}:d=0.2,format=yuv420p",
          "-an","-r",str(FPS),"-c:v","libx264","-preset","veryfast",
          "-crf","24","-pix_fmt","yuv420p",str(target)])

def scene(source, clip, masks, target):
    """No top step counter and no bottom action subtitles."""
    duration = float(clip["end"] - clip["start"])
    filters = []
    for m in masks:
        filters.append("drawbox=x={x}:y={y}:w={width}:h={height}:color=0x12121d:t=fill".format(
            **{k: int(m[k]) for k in ("x", "y", "width", "height")}))
    filters += [
        f"setpts=(PTS-STARTPTS)/{clip['speed']}",
        f"fps={FPS}",
        "scale=720:1280:force_original_aspect_ratio=decrease:flags=lanczos",
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=0x080d1d",
        "setsar=1", "format=yuv420p"
    ]
    call(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
          "-ss", str(clip["start"]), "-t", str(duration), "-i", str(source),
          "-vf", ",".join(filters),
          "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
          "-crf", "22", "-pix_fmt", "yuv420p",
          "-t", str(duration / clip["speed"]), str(target)])


def original_audio(path, seconds):
    # Original pulse, not the reference video's potentially copyrighted music.
    rate=22050
    pcm=array("h")
    notes=(164.81,196.0,246.94,220.0)
    for k in range(int(seconds*rate)):
        t=k/rate
        phase=t%0.48
        beat=math.exp(-phase*25)*math.sin(2*math.pi*72*t)
        music=math.sin(2*math.pi*notes[int(t//0.96)%4]*t)*(0.2+0.8*math.exp(-phase*2.5))
        volume=max(0,min(1,(seconds-t)/0.5)) if t>seconds-0.5 else 1
        pcm.append(int(32767*volume*(0.13*beat+0.009*music)))
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())

def hook_timing(start, end, total=3):
    """Keep the nearly-accident motorcycle footage at original 1x speed."""
    if any(type(v) not in (int,float) for v in (start,end,total)):
        raise RecipeError("Tempos do gancho invalidos")
    motor = end-start
    if not 0 <= start < end or not .4 <= motor <= 1.2 or total != 3:
        raise RecipeError("Moto de .4 a 1.2 s sem camera lenta; abertura total 3 s")
    return round(motor, 4), round(total-motor, 4)


def validate_hook(recipe, duration, resolution):
    if recipe.get("opening_style") != "universe_gif":
        raise RecipeError("Abertura deve ser universe_gif")
    if recipe.get("hook_source_resolution") != list(resolution):
        raise RecipeError("Resolucao do video da moto mudou")
    crop=recipe.get("hook_crop")
    if not isinstance(crop,list) or len(crop)!=4 or any(type(v)!=int for v in crop):
        raise RecipeError("Recorte de gancho invalido")
    x,y,w,h=crop
    if x<0 or y<0 or w<160 or h<240 or x+w>resolution[0] or y+h>resolution[1]:
        raise RecipeError("Recorte do gancho fora da gravacao")
    start=recipe.get("hook_source_start")
    end=recipe.get("hook_source_end")
    motor,space=hook_timing(start,end,recipe.get("hook_duration_seconds"))
    if end>duration or abs(recipe.get("universe_seconds",0)-space)>.1:
        raise RecipeError("Gancho e universo precisam somar 3 s sem esticar moto")
    return motor,space


def motorcycle_video(source, recipe, seconds, target):
    x,y,w,h=recipe["hook_crop"]
    start=recipe["hook_source_start"]
    call(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-ss",str(start),"-t",str(seconds),"-i",str(source),
          "-vf",f"crop={w}:{h}:{x}:{y},fps={FPS},scale=720:1280:flags=lanczos,setsar=1,format=yuv420p",
          "-an","-c:v","libx264","-preset","veryfast","-crf","23",
          "-pix_fmt","yuv420p","-r",str(FPS),str(target)])


def universe_video(gif_source, lines, seconds, target, text_file):
    """Use externally supplied universe GIF; local file, not a paid service."""
    from PIL import Image, ImageDraw
    overlay=Image.new("RGBA",SIZE,(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    for n,line in enumerate(lines[:3]):
        txt=clean_text(line,75)
        f=fitting(d,txt,SIZE[0]-60,50)
        y=500+n*82
        d.text((SIZE[0]//2+2,y+3),txt,font=f,anchor="mm",
               fill=(0,0,0,255),stroke_width=5,stroke_fill=(0,0,0,235))
        d.text((SIZE[0]//2,y),txt,font=f,anchor="mm",fill=(255,255,255,255))
    overlay.save(text_file)
    call(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
          "-stream_loop","-1","-i",str(gif_source),"-loop","1","-i",str(text_file),
          "-filter_complex","[0:v]fps=24,scale=720:1280:force_original_aspect_ratio=increase,"
                            "crop=720:1280,setsar=1[space];"
                            "[space][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
          "-map","[v]","-an","-t",str(seconds),"-r",str(FPS),
          "-c:v","libx264","-preset","veryfast","-crf","24",
          "-pix_fmt","yuv420p",str(target)])


def render(source, recipe_path, output, hook_source=None, universe_gif=None):
    if not source.is_file() or not hook_source or not hook_source.is_file():
        raise RecipeError("Forneca gravacao da tela e clipe de gancho")
    if not universe_gif or not universe_gif.is_file():
        raise RecipeError("Forneca GIF de universo, arquivo privado local")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RecipeError("Instale FFmpeg")
    duration,res=probe(source)
    recipe=validate_recipe(json.loads(recipe_path.read_text(encoding="utf-8")),
                           duration=duration,resolution=res)
    hd,hr=probe(hook_source)
    motor,space=validate_hook(recipe,hd,hr)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moneyprint-tutorial-") as tmp:
        t=Path(tmp)
        parts=[]
        motorcycle_video(hook_source,recipe,motor,t/"000-moto.mp4")
        parts.append(t/"000-moto.mp4")
        universe_video(universe_gif,recipe["hook"],space,t/"001-universe.mp4",t/"title.png")
        parts.append(t/"001-universe.mp4")
        for i,c in enumerate(recipe["clips"],1):
            mp4=t/f"{i:03d}-take.mp4"
            scene(source,c,masks_for_clip(recipe,c),mp4)
            parts.append(mp4)
        playlist=t/"videos.txt"
        playlist.write_text("".join(f"file '{p}'\n" for p in parts),encoding="utf-8")
        joined=t/"silent.mp4"
        call(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
              "-f","concat","-safe","0","-i",str(playlist),"-c","copy",str(joined)])
        secs,_=probe(joined)
        original_audio(t/"audio.wav",secs)
        call(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
              "-i",str(joined),"-i",str(t/"audio.wav"),
              "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-shortest",
              "-map_metadata","-1","-movflags","+faststart",str(output)])
    return {"output":str(output),"seconds":round(secs,2),"takes":len(recipe["clips"]),
            "layout":"no_top_or_bottom_overlays","hook_playback":"original_speed",
            "privacy":"opaque_masks","publication":"manual_review_only"}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--hook-source",required=True,type=Path)
    p.add_argument("--universe-gif",required=True,type=Path)
    p.add_argument("--recipe",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    print(json.dumps(render(args.source,args.recipe,args.output,args.hook_source,args.universe_gif),
                     ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
