"""MoneyPrint layered scenes: offline, deterministic Pillow/FFmpeg compositor.

Each JSON scene owns independent ordered text, pill, footage and footer layers.
It exports frame/scene previews and MP4 files separately for incremental rerender.
This optional tool never downloads or publishes private media automatically.
"""
from __future__ import annotations
import argparse
import json
import math
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SAFE = re.compile(r'^assets/[A-Za-z0-9_.\-/]+\.mp4$')
COLORS = {'ink':'#0A0E19','white':'#F7F7FA','purple':'#A67BFB',
          'muted':'#CFD0D8','subtle':'#9395AA','edge':'#444057'}

class LayerError(ValueError):
    pass

def validate(spec:dict) -> dict:
    if not isinstance(spec,dict) or spec.get('schema_version')!=1:
        raise LayerError('Formato de cenas inválido')
    if spec.get('fps') not in (24,25,30,60) or spec.get('aspect')!='9:16':
        raise LayerError('Formato deve ser vertical e FPS suportado')
    if spec.get('width')!=1080 or spec.get('height')!=1920:
        raise LayerError('Canvas canônico deve ser 1080x1920')
    scenes=spec.get('scenes',[])
    if not 1<=len(scenes)<=120: raise LayerError('Quantidade de cenas inválida')
    seen=set(); cursor=0
    for scene in scenes:
        sid=scene.get('id')
        if not isinstance(sid,str) or not re.fullmatch(r'[a-z0-9-]{3,50}',sid) or sid in seen:
            raise LayerError('ID de cena duplicado ou inválido')
        seen.add(sid)
        if scene.get('start_frame')!=cursor or type(scene.get('duration_frames')) is not int or scene['duration_frames']<=0:
            raise LayerError('Timeline descontínua')
        cursor+=scene['duration_frames']
        layers=scene.get('layers',[])
        if not isinstance(layers,list) or not 3<=len(layers)<=40:
            raise LayerError('Cena sem camadas suficientes')
        lseen=set()
        for layer in layers:
            kind=layer.get('kind'); lid=layer.get('id')
            if kind not in ('background','text','video','pill','footer') or not isinstance(lid,str) or lid in lseen:
                raise LayerError('Camada duplicada ou desconhecida')
            lseen.add(lid)
            if layer.get('enter','rise') not in ('rise','fade','slide','type','none'):
                raise LayerError('Entrada desconhecida')
            if type(layer.get('at',0)) not in (int,float) or not 0<=layer.get('at',0)<scene['duration_frames']/spec['fps']:
                raise LayerError('Entrada fora da cena')
            if kind=='video':
                path=layer.get('path','')
                if not isinstance(path,str) or not SAFE.fullmatch(path) or '..' in PurePosixPath(path).parts:
                    raise LayerError('Caminho inseguro de vídeo')
            if kind in ('text','pill','footer') and not isinstance(layer.get('text'),str):
                raise LayerError('Camada sem texto')
            for dim in ('x','y','w','h'):
                if dim in layer and (type(layer[dim]) not in (int,float) or layer[dim]<0 or layer[dim]>2500):
                    raise LayerError('Dimensão inválida')
    if spec.get('total_frames')!=cursor: raise LayerError('Frames totais divergentes')
    return spec

def _font(size:int,bold:bool=True):
    paths=(['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'] if bold else
           ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'])
    for path in paths:
        if Path(path).is_file():return ImageFont.truetype(path,max(9,size))
    return ImageFont.load_default()

def _scaled(n,scale): return int(round(n*scale))

def _wrap(txt,font,max_width):
    tmp=ImageDraw.Draw(Image.new('RGBA',(2,2)))
    lines=[]
    for paragraph in txt.split('\n'):
        if not paragraph.strip():lines.append('');continue
        buffer=''
        for word in paragraph.split():
            proposal=f'{buffer} {word}'.strip()
            if buffer and tmp.textlength(proposal,font=font)>max_width:
                lines.append(buffer);buffer=word
            else:buffer=proposal
        if buffer:lines.append(buffer)
    return lines

def _text_image(layer,scale):
    size=_scaled(layer.get('size',40),scale)
    font=_font(size,layer.get('bold',True))
    width=_scaled(layer.get('w',910),scale)
    pad=max(3,_scaled(6,scale)); lineheight=round(size*layer.get('line_height',1.17))
    lines=_wrap(layer['text'],font,width-pad*2)
    height=max(lineheight*len(lines)+pad*2,4)
    img=Image.new('RGBA',(width,height),(0,0,0,0)); d=ImageDraw.Draw(img)
    for i,t in enumerate(lines):d.text((pad,pad+i*lineheight),t,font=font,fill=layer.get('color',COLORS['white']))
    return img

def _pill_image(layer,scale):
    w=_scaled(layer.get('w',300),scale);h=_scaled(layer.get('h',78),scale)
    img=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(img)
    d.rounded_rectangle((2,2,w-3,h-3),radius=max(8,_scaled(28,scale)),fill=(12,18,35,225),outline=layer.get('outline',COLORS['purple']),width=max(1,_scaled(2,scale)))
    font=_font(_scaled(layer.get('size',28),scale),bold=True)
    label=layer['text'];bbox=d.textbbox((0,0),label,font=font)
    d.text(((w-(bbox[2]-bbox[0]))/2,(h-(bbox[3]-bbox[1]))/2-bbox[1]),label,font=font,fill=layer.get('color',COLORS['white']))
    return img

def background(w,h,seed=0):
    base=Image.new('RGB',(w,h));d=ImageDraw.Draw(base)
    for y in range(h):
        t=y/max(1,h-1);d.line((0,y,w,y),fill=(int(8+10*t),int(11+9*t),int(23+11*t)))
    bokeh=Image.new('RGBA',(w,h),(0,0,0,0));bd=ImageDraw.Draw(bokeh)
    for k in range(16):
        xpos=int(w*(0.04+(0.91*((k*37+seed*11)%97)/97)))
        ypos=int(h*(0.22+(0.65*((k*23+seed*5)%89)/89)))
        rad=max(4,int(w*(.012+.025*((k*13)%11)/11)))
        color=(247,151,66,65) if k%3 else (75,89,220,65)
        bd.ellipse((xpos-rad,ypos-rad,xpos+rad,ypos+rad),fill=color)
    bokeh=bokeh.filter(ImageFilter.GaussianBlur(max(8,round(w*.025))))
    return Image.alpha_composite(base.convert('RGBA'),bokeh)

def _enter(layer,t):
    start=layer.get('at',0); d=max(.01,layer.get('enter_seconds',.48));
    if t<start:return 0.0,0,0,0.0
    p=min(1.0,(t-start)/d);ease=1-(1-p)**3
    kind=layer.get('enter','rise')
    if kind=='none':return 1.,0,0,1.
    if kind=='fade':return ease,0,0,1.
    if kind=='slide':return ease,int(-60*(1-ease)),0,1.
    if kind=='type':return 1.,0,0,ease
    return ease,0,int(55*(1-ease)),1.

def _overlay(canvas,overlay,x,y,alpha=1.0,reveal=1.0):
    if alpha<=0:return
    if reveal<1:
        limit=max(1,int(overlay.width*reveal)); overlay=overlay.crop((0,0,limit,overlay.height))
    if alpha<1:
        overlay=overlay.copy();overlay.putalpha(overlay.getchannel('A').point(lambda a:round(a*alpha)))
    canvas.alpha_composite(overlay,(int(x),int(y)))

def _media_box(frame,layer,scale):
    x=_scaled(layer['x'],scale);y=_scaled(layer['y'],scale)
    w=_scaled(layer['w'],scale);h=_scaled(layer['h'],scale)
    shadow=Image.new('RGBA',frame.size,(0,0,0,0));d=ImageDraw.Draw(shadow)
    outer=max(6,_scaled(12,scale));r=max(6,_scaled(24,scale));
    d.rounded_rectangle((x-outer+4,y-outer+12,x+w+outer+4,y+h+outer+12),radius=r,fill=(0,0,0,85))
    shadow=shadow.filter(ImageFilter.GaussianBlur(max(3,_scaled(12,scale))))
    frame.alpha_composite(shadow)
    d=ImageDraw.Draw(frame)
    d.rounded_rectangle((x-outer,y-outer,x+w+outer,y+h+outer),radius=r,
                        fill=(14,16,27,255),outline=(150,133,204,240),width=max(2,_scaled(3,scale)))

def _start_video(layer,root,scale,fps):
    file=(root/layer['path']).resolve();root_path=root.resolve()
    if not file.is_relative_to(root_path) or not file.is_file():
        raise LayerError(f'Vídeo local ausente: {layer["path"]}')
    w=_scaled(layer['w'],scale);h=_scaled(layer['h'],scale)
    if not shutil.which('ffmpeg'):raise LayerError('FFmpeg não encontrado')
    vf=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x101727,fps={fps},format=rgb24'
    args=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(layer.get('clip_start',0)),
          '-i',str(file),'-vf',vf,'-an','-f','rawvideo','-pix_fmt','rgb24','-']
    return subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE),w,h

def render_scene(spec,scene,root:Path,out:Path,width:int=1080,preview_only:bool=False,preview_at:float|None=None):
    scale=width/spec['width'];h=_scaled(spec['height'],scale);fps=spec['fps'];duration=scene['duration_frames']/fps
    if width%2 or h%2:raise LayerError('Resolução deve ser par')
    out.mkdir(parents=True,exist_ok=True)
    bg=background(width,h,int(scene['id'].split('-')[-1]))
    cache={}
    for layer in scene['layers']:
        if layer['kind']=='text' or layer['kind']=='footer':cache[layer['id']]=_text_image(layer,scale)
        elif layer['kind']=='pill':cache[layer['id']]=_pill_image(layer,scale)
    media={}
    if not preview_only:
        for l in scene['layers']:
            if l['kind']=='video':media[l['id']]=_start_video(l,root,scale,fps)
    writer=None
    path=out/(scene['id']+'.mp4')
    if not preview_only:
        writer=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo',
            '-pixel_format','rgb24','-video_size',f'{width}x{h}','-framerate',str(fps),'-i','-',
            '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(path)],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    total=1 if preview_only else scene['duration_frames']
    for i in range(total):
        t=duration*.58 if preview_at is None and preview_only else (preview_at if preview_only else i/fps)
        frame=bg.copy()
        for layer in scene['layers']:
            if layer['kind']=='background':continue
            alpha,dx,dy,reveal=_enter(layer,t)
            if alpha<=0:continue
            x=_scaled(layer.get('x',0),scale)+_scaled(dx,scale)
            y=_scaled(layer.get('y',0),scale)+_scaled(dy,scale)
            if layer['kind']=='video':
                _media_box(frame,layer,scale)
                w=_scaled(layer['w'],scale);hh=_scaled(layer['h'],scale)
                if preview_only:
                    # Preview a real source frame: no invented synthetic UI.
                    proc,w,hh=_start_video({**layer,'clip_start':layer.get('clip_start',0)+t},root,scale,fps)
                    raw=proc.stdout.read(w*hh*3);proc.stdout.close();proc.kill();proc.wait()
                else:
                    proc,w,hh=media[layer['id']]
                    raw=proc.stdout.read(w*hh*3)
                if len(raw)!=w*hh*3:raise LayerError(f'Vídeo muito curto: {layer["path"]}')
                shot=Image.frombytes('RGB',(w,hh),raw).convert('RGBA')
                _overlay(frame,shot,x,y,alpha,1.)
            else:_overlay(frame,cache[layer['id']],x,y,alpha,reveal)
        if preview_only:
            dest=out/(scene['id']+'.png');frame.convert('RGB').save(dest,optimize=True)
        else:
            writer.stdin.write(frame.convert('RGB').tobytes())
    for proc,w,h2 in media.values():
        proc.stdout.close();proc.kill();proc.wait()
    if writer:
        writer.stdin.close();err=writer.stderr.read().decode('utf-8','replace');ret=writer.wait()
        if ret:raise LayerError(f'FFmpeg não conseguiu exportar MP4: {err[-900:]}')
    return out/(scene['id']+('.png' if preview_only else '.mp4'))

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--root',default='.')
    p.add_argument('--output',default='outputs/pdv-artisys');p.add_argument('--scene',default='all')
    p.add_argument('--width',type=int,default=1080);p.add_argument('--preview',action='store_true')
    a=p.parse_args(argv);root=Path(a.root).resolve()
    spec=validate(json.loads(Path(a.input).read_text(encoding='utf8')))
    scenes=spec['scenes'] if a.scene=='all' else [s for s in spec['scenes'] if s['id']==a.scene]
    if not scenes:raise SystemExit('Cena inexistente')
    output=Path(a.output)
    reports=[]
    for scene in scenes:
        path=render_scene(spec,scene,root,output,width=a.width,preview_only=a.preview)
        reports.append({'scene':scene['id'],'path':str(path),'duration_s':scene['duration_frames']/spec['fps'],
                        'layers':[x['id'] for x in scene['layers']]})
        print(path)
    (output/'layer_manifest.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf8')
    return reports

if __name__=='__main__':main()
