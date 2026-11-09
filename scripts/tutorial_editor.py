"""Editor vertical de tutoriais capturados: FFmpeg + Pillow, sem serviço pago.

As máscaras são retângulos opacos aplicados antes de escala e efeitos.
Não envia vídeo para terceiros, exclui áudio e metadados da captura original.
Importante: revisão humana das máscaras é obrigatória antes da publicação.
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

class RecipeError(ValueError):
    pass

W,H,FPS=720,1280,24
FONT_PATHS=[
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")
]

def text_line(value, limit=100):
    if (not isinstance(value,str) or not 1 <= len(value.strip()) <= limit
        or any(ord(c)<32 for c in value)):
        raise RecipeError("Texto inválido")
    return value.strip()

def validate_recipe(raw, *, duration, resolution):
    if not isinstance(raw,dict) or raw.get("format")!="9:16":
        raise RecipeError("Receita deve ser objeto JSON em formato 9:16")
    if raw.get("source_resolution")!=list(resolution):
        raise RecipeError("Resolução original mudou: recalibre as máscaras")
    text_line(raw.get("title"),180)
    for key in ("hook","outro"):
        phrases=raw.get(key)
        if not isinstance(phrases,list) or not 1<=len(phrases)<=4:
            raise RecipeError(key+" precisa de 1 a 4 frases")
        for phrase in phrases: text_line(phrase,70)
    masks=raw.get("privacy_masks")
    if not isinstance(masks,list) or not masks:
        raise RecipeError("privacy_masks obrigatório: revise privacidade primeiro")
    sw,sh=resolution
    for mask in masks:
        if not isinstance(mask,dict) or any(type(mask.get(k)) not in (int,float)
            for k in ("start","end","x","y","width","height")):
            raise RecipeError("Máscara de privacidade inválida")
        x,y,mw,mh=(mask[k] for k in ("x","y","width","height"))
        if (not 0<=mask["start"]<mask["end"]<=duration+.25 or
            x<0 or y<0 or mw<=0 or mh<=0 or x+mw>sw or y+mh>sh):
            raise RecipeError("Máscara fora da duração ou da imagem")
    clips=raw.get("clips")
    if not isinstance(clips,list) or not 1<=len(clips)<=20:
        raise RecipeError("clips precisa de 1 a 20 takes")
    previous=-1
    for clip in clips:
        if not isinstance(clip,dict) or any(type(clip.get(k)) not in (int,float)
            for k in ("start","end","speed")):
            raise RecipeError("Take inválido")
        if (not 0<=clip["start"]<clip["end"]<=duration or
            not 1<=clip["speed"]<=3.5 or clip["start"]<previous):
            raise RecipeError("Tempo ou aceleração de take inválido")
        previous=clip["end"]
        text_line(clip.get("caption"),48)
        zoom=clip.get("zoom",1.0)
        if type(zoom) not in (int,float) or not 1.0<=zoom<=1.18:
            raise RecipeError("Zoom inválido")
        for mask in masks:
            if clip["start"]<mask["end"] and mask["start"]<clip["end"]:
                if mask["start"]>clip["start"] or mask["end"]<clip["end"]:
                    raise RecipeError("Take com máscara parcial; cubra o take completo")
    return raw

def masks_for_clip(recipe,clip):
    return [m for m in recipe["privacy_masks"]
            if clip["start"]<m["end"] and clip["end"]>m["start"]]

def probe(path):
    payload=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height:format=duration",
        "-of","json",str(path)],text=True))
    video=payload["streams"][0]
    return float(payload["format"]["duration"]),(video["width"],video["height"])

def font(size):
    from PIL import ImageFont
    for path in FONT_PATHS:
        if path.exists(): return ImageFont.truetype(str(path),size)
    raise RecipeError("Instale fonts-dejavu-core")

def fit(draw,label,width,size=60):
    while size>20:
        face=font(size)
        bb=draw.textbbox((0,0),label,font=face)
        if bb[2]-bb[0]<=width: return face
        size-=2
    return font(20)

def hook_card(path,lines):
    from PIL import Image,ImageDraw,ImageFilter
    small=Image.new("RGB",(180,320))
    pixels=small.load()
    for y in range(320):
        for x in range(180):
            a=math.exp(-(((x-42)/110)**2+((y-88)/125)**2))
            b=math.exp(-(((x-145)/87)**2+((y-220)/100)**2))
            pixels[x,y]=(int(8+75*a+5*b),int(11+11*a+78*b),int(30+115*a+100*b))
    image=small.resize((W,H),Image.Resampling.BICUBIC)
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    painter=ImageDraw.Draw(glow)
    painter.ellipse((-120,90,400,620),fill=(167,53,237,85))
    painter.ellipse((340,640,850,1150),fill=(20,240,224,75))
    image=Image.alpha_composite(image.convert("RGBA"),glow.filter(ImageFilter.GaussianBlur(88)))
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((58,90,W-58,166),radius=28,fill=(21,29,59,215),outline=(57,218,213,145),width=2)
    d.text((W//2,128),"ARTISYS / MONEYPRINT",anchor="mm",font=font(24),fill=(135,243,232,255))
    for i,line in enumerate(lines):
        face=fit(d,line,W-75,62)
        accent="GITHUB" in line.upper() or (i==0 and len(lines)>2)
        d.text((W//2,480+i*108),line,anchor="mm",font=face,
               fill=(82,255,223,255) if accent else (250,251,255,255),
               stroke_width=2,stroke_fill=(12,12,30,255))
    d.rounded_rectangle((W//2-100,965,W//2+100,973),radius=4,fill=(83,230,213,255))
    d.text((W//2,1040),"TUTORIAL RÁPIDO • 9:16",font=font(22),anchor="mm",fill=(189,214,235,255))
    image.convert("RGB").save(path,quality=94)

def caption_card(path,label,i,count):
    from PIL import Image,ImageDraw
    image=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((32,72,W-32,156),radius=26,fill=(7,12,29,230),outline=(40,240,214,130),width=2)
    d.text((62,111),f"PASSO {i:02d}/{count:02d}",font=font(28),anchor="lm",fill=(94,252,219,255))
    d.rounded_rectangle((23,1110,W-23,1204),radius=28,fill=(5,9,25,239),
                        outline=(127,111,232,90),width=2)
    d.text((W//2,1157),label,font=fit(d,label,W-72,38),anchor="mm",fill=(250,251,255,255))
    image.save(path)

def execute(args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL)

def card_video(image,output,seconds):
    execute(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
             "-loop","1","-framerate",str(FPS),"-i",str(image),"-t",str(seconds),
             "-vf",f"fade=t=in:st=0:d=0.15,fade=t=out:st={seconds-.2}:d=0.2,format=yuv420p",
             "-an","-c:v","libx264","-crf","24","-preset","veryfast",
             "-pix_fmt","yuv420p","-r",str(FPS),str(output)])

def recorded_scene(source,clip,masks,overlay,output):
    duration=clip["end"]-clip["start"]
    speed=clip["speed"]
    filters=[]
    for mask in masks:
        x,y,w,h=[int(mask[k]) for k in ("x","y","width","height")]
        # Opaque BEFORE motion/transforms: avoids revealing original pixels.
        filters.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x12121d:t=fill")
    filters += [
        f"setpts=(PTS-STARTPTS)/{speed}",f"fps={FPS}",
        "scale=720:1280:force_original_aspect_ratio=decrease:flags=lanczos",
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=0x080c19","setsar=1"]
    zoom=clip.get("zoom",1.0)
    if zoom>1:
        w=round(W*zoom/2)*2; h=round(H*zoom/2)*2
        filters.extend([f"scale={w}:{h}:flags=lanczos",
                        f"crop={W}:{H}:(in_w-out_w)/2:(in_h-out_h)/2"])
    execute(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
             "-ss",str(clip["start"]),"-t",str(duration),"-i",str(source),
             "-loop","1","-i",str(overlay),"-filter_complex",
             "[0:v]"+",".join(filters)+"[v0];[v0][1:v]overlay=shortest=1:format=auto,format=yuv420p[v]",
             "-map","[v]","-an","-r",str(FPS),"-c:v","libx264",
             "-preset","veryfast","-crf","25","-pix_fmt","yuv420p",
             "-t",str(duration/speed),str(output)])

def backing_audio(path,seconds):
    """Original non-copyright pulse, not captured microphone nor outside music."""
    from array import array
    rate=22050
    samples=array("h")
    for index in range(int(seconds*rate)):
        t=index/rate
        phase=t%0.48
        beat=math.exp(-phase*25)*math.sin(2*math.pi*72*t)
        note=(164.81,196,246.94,220)[int(t//.96)%4]
        sound=.13*beat+.009*math.sin(2*math.pi*note*t)
        if t>seconds-.5: sound*=max(0,(seconds-t)/.5)
        samples.append(int(max(-1,min(1,sound))*32767))
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        out.writeframes(samples.tobytes())

def render(source,recipe_file,output):
    from PIL import Image  # noqa: F401
    if not source.is_file(): raise RecipeError("Gravação de origem inexistente")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RecipeError("FFmpeg/ffprobe não instalados")
    duration,resolution=probe(source)
    recipe=validate_recipe(json.loads(recipe_file.read_text(encoding="utf-8")),
                           duration=duration,resolution=resolution)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="moneyprint-tutorial-") as work:
        tmp=Path(work); segments=[]
        intro_image=tmp/"intro.jpg"; hook_card(intro_image,recipe["hook"])
        intro=tmp/"000-intro.mp4";card_video(intro_image,intro,2.2);segments.append(intro)
        for i,clip in enumerate(recipe["clips"],1):
            label=tmp/f"caption-{i:02}.png"
            caption_card(label,clip["caption"],i,len(recipe["clips"]))
            section=tmp/f"{i:03}-take.mp4"
            recorded_scene(source,clip,masks_for_clip(recipe,clip),label,section)
            segments.append(section)
        outro_image=tmp/"outro.jpg";hook_card(outro_image,recipe["outro"])
        outro=tmp/"999-outro.mp4";card_video(outro_image,outro,2);segments.append(outro)
        playlist=tmp/"concat.txt"
        playlist.write_text("".join("file '"+str(p)+"'\n" for p in segments))
        joined=tmp/"joined.mp4"
        execute(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                 "-f","concat","-safe","0","-i",str(playlist),"-c","copy",str(joined)])
        length,_=probe(joined)
        song=tmp/"original.wav";backing_audio(song,length)
        execute(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                 "-i",str(joined),"-i",str(song),"-map","0:v:0","-map","1:a:0",
                 "-c:v","copy","-c:a","aac","-b:a","128k","-shortest",
                 "-map_metadata","-1","-metadata","title="+recipe["title"],
                 "-movflags","+faststart",str(output)])
    return {"output":str(output.resolve()),"seconds":round(length,2),
            "takes":len(recipe["clips"]),"privacy_masks":len(recipe["privacy_masks"]),
            "source_audio":"excluded","publish":"human_review_required"}

def main():
    cli=argparse.ArgumentParser(description="MoneyPrint: criar tutorial gravado vertical")
    cli.add_argument("--source",required=True,type=Path)
    cli.add_argument("--recipe",required=True,type=Path)
    cli.add_argument("--output",required=True,type=Path)
    args=cli.parse_args()
    print(json.dumps(render(args.source,args.recipe,args.output),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
