"""MoneyPrint Studio: animated, light slides using Pillow + FFmpeg (100% OSS).

Each scene has independently moving cards, typography and real GitHub imagery.
No paid provider, fake interface presented as factual, or legacy render changes.
"""
from __future__ import annotations
import math
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

BG=(247,249,255)
INK=(22,30,58)
MUTED=(94,107,137)
PURPLE=(111,88,230)
BLUE=(47,138,241)
TEAL=(36,166,181)

def font(px, bold=False):
    candidates=[
        '/usr/share/fonts/truetype/lato/Lato-Bold.ttf' if bold else '/usr/share/fonts/truetype/lato/Lato-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        if Path(path).exists(): return ImageFont.truetype(path,max(10,int(px)))
    return ImageFont.load_default()

def fitted(draw,s,maxw,px,bold=False,minpx=14):
    px=int(px)
    while px>minpx and draw.textlength(str(s),font=font(px,bold))>maxw: px-=2
    return font(px,bold)

def wrap(draw,text,width,px,maxlines=2,bold=False):
    words=str(text).split(); lines=[]; cur=''; f=font(px,bold)
    for word in words:
        proposed=(cur+' '+word).strip()
        if draw.textlength(proposed,font=f)<=width: cur=proposed
        else:
            if cur: lines.append(cur)
            cur=word
        if len(lines)>=maxlines: break
    if cur and len(lines)<maxlines: lines.append(cur)
    return lines

def round_rect(d,xy,fill,stroke=None,r=28,sw=2):
    d.rounded_rectangle(tuple(int(n) for n in xy),radius=max(2,int(r)),fill=fill,outline=stroke,width=max(1,int(sw)))

def background(w,h,dest):
    im=Image.new('RGB',(w,h),BG); d=ImageDraw.Draw(im)
    for y in range(h):
        a=y/max(1,h-1)
        d.line((0,y,w,y),fill=(int(249-5*a),int(250-2*a),255))
    glow=Image.new('RGBA',(w,h));g=ImageDraw.Draw(glow)
    g.ellipse((int(w*.51),int(-h*.45),int(w*1.38),int(h*.61)),fill=(151,126,246,58))
    g.ellipse((int(-w*.3),int(h*.48),int(w*.38),int(h*1.37)),fill=(76,180,249,44))
    g.ellipse((int(w*.56),int(h*.71),int(w*1.10),int(h*1.35)),fill=(69,220,213,25))
    glow=glow.filter(ImageFilter.GaussianBlur(max(18,int(w*.045))))
    im=Image.alpha_composite(im.convert('RGBA'),glow).convert('RGB')
    d=ImageDraw.Draw(im);step=max(20,int(w*.028))
    for x in range(step//2,w,step):
        for y in range(step//2,h,step):d.ellipse((x,y,x+1,y+1),fill=(217,226,245))
    s=w/1920
    d.ellipse((int(115*s),int(79*s),int(138*s),int(102*s)),fill=PURPLE)
    d.text((int(155*s),int(75*s)),"ARTISYS  /  MONEYPRINT",font=font(23*s,True),fill=(81,91,120))
    d.line((int(115*s),int(116*s),w-int(115*s),int(116*s)),fill=(222,228,243),width=max(1,int(2*s)))
    im.save(dest)

def layer_canvas(w,h):return Image.new('RGBA',(w,h),(0,0,0,0))

def shadow_rect(im,xy,fill='#FFFFFF',stroke='#E5EAF6',radius=24,shadow=13):
    x0,y0,x1,y1=(int(x) for x in xy)
    shade=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shade)
    sd.rounded_rectangle((x0+2,y0+11,x1+2,y1+11),radius=radius,fill=(39,61,111,42))
    shade=shade.filter(ImageFilter.GaussianBlur(shadow))
    im.alpha_composite(shade)
    d=ImageDraw.Draw(im)
    d.rounded_rectangle((x0,y0,x1,y1),radius=radius,fill=fill,outline=stroke,width=2)
    return d

def text_layer(w,h,kind,scene):
    s=w/1920; im=layer_canvas(w,h);d=ImageDraw.Draw(im)
    if kind=='eyebrow':
        eyebrow=(scene.get('eyebrow') or 'OPEN SOURCE  /  NEGÓCIOS').upper()[:52]
        x=int(116*s);y=int(158*s); f=font(24*s,True)
        tw=d.textlength(eyebrow,font=f);round_rect(d,(x,y,x+tw+int(50*s),y+int(55*s)),(237,231,255,255),r=int(24*s))
        d.text((x+int(25*s),y+int(11*s)),eyebrow,font=f,fill=PURPLE)
    if kind=='title':
        title=(scene.get('title') or 'SISTEMAS OPEN SOURCE').upper().strip()
        size=70*s if len(title)<=32 else 58*s
        for i,line in enumerate(wrap(d,title,int(1490*s),int(size),2,True)):
            d.text((int(118*s),int((232+i*83)*s)),line,font=font(size,True),fill=INK)
    if kind=='description':
        caption=scene.get('caption') or scene.get('text') or ''
        caption=re.sub(r'\s+',' ',caption).strip();words=caption.split()
        caption=' '.join(words[:19])+('…' if len(words)>19 else '')
        for i,line in enumerate(wrap(d,caption,int(1470*s),int(29*s),2)):
            d.text((int(123*s),int((386+i*39)*s)),line,font=font(29*s),fill=MUTED)
    return im

def icon(d,cx,cy,r,color,kind=0):
    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=color);white=(255,255,255,255)
    if kind%3==0:
        d.rounded_rectangle((cx-int(r*.43),cy-int(r*.42),cx+int(r*.43),cy+int(r*.42)),radius=max(2,int(r*.18)),outline=white,width=max(2,int(r*.14)))
    elif kind%3==1:
        for k in (-1,0,1):
            d.rounded_rectangle((cx-int(r*.36),cy+int(k*r*.2)-2,cx+int(r*.36),cy+int(k*r*.2)+2),radius=2,fill=white)
    else:
        d.line((cx-int(r*.32),cy,cx,cy+int(r*.28),cx+int(r*.36),cy-int(r*.31)),fill=white,width=max(2,int(r*.15)),joint='curve')

DIAGRAMS={
    'erpnext':(('VENDA','ESTOQUE','FINANCEIRO'),('Planilhas isoladas','Gestão integrada')),
    'twenty':(('CONTATO','PROPOSTA','VENDA'),('Leads esquecidos','Funil acompanhado')),
    'chatwoot':(('MENSAGEM','ATENDENTE','RESOLUÇÃO'),('Caixas separadas','Atendimento central')),
    'plane':(('A FAZER','EM ANDAMENTO','CONCLUÍDO'),('Tarefas dispersas','Progresso visível')),
    'paperless':(('DOCUMENTO','INDEXAÇÃO','BUSCA'),('Pastas e anexos','Arquivos pesquisáveis')),
}
def business_diagram(scene):
    context=' '.join(str(scene.get(k,'')) for k in ('title','eyebrow','repo_url')).lower()
    for key,pair in DIAGRAMS.items():
        if key in context:return pair
    for keyword,key in (('crm','twenty'),('estoque','erpnext'),('financeiro','erpnext'),('atendimento','chatwoot'),('kanban','plane'),('projeto','plane'),('documento','paperless')):
        if keyword in context:return DIAGRAMS[key]
    return (('ENTRADA','ORGANIZAÇÃO','RESULTADO'),('Processos manuais','Fluxo integrado'))

def card_layer(w,h,scene,k):
    s=w/1920;im=layer_canvas(w,h);d=ImageDraw.Draw(im)
    labels,pair=business_diagram(scene)
    given=scene.get('flow_steps') or scene.get('bullets')
    if isinstance(given,list) and given:
        labels=tuple(str(x).strip()[:40] for x in given[:3])
        labels=labels+tuple('RESULTADO' for _ in range(3-len(labels)))
    layout=scene.get('layout','flow')
    if layout=='browser':
        x0=int(120*s);top=int(525*s);gap=int(22*s);width=int(710*s);hei=int(117*s)
        y=top+k*(hei+gap)
        d=shadow_rect(im,(x0,y,x0+width,y+hei),radius=max(8,int(21*s)),shadow=max(3,int(12*s)))
        col=(PURPLE,BLUE,TEAL)[k]
        icon(d,x0+int(75*s),y+hei//2,int(31*s),col,k)
        d.text((x0+int(130*s),y+int(35*s)),str(labels[k]),font=fitted(d,str(labels[k]),int(520*s),32*s,True),fill=INK)
    elif layout=='split':
        if k>=2:return im
        label=('ANTES','COM OPEN SOURCE')[k];name=pair[k] if len(pair)>k else labels[k]
        x0=int((120 if k==0 else 992)*s);y=int(525*s);cw=int(820*s);ch=int(355*s)
        d=shadow_rect(im,(x0,y,x0+cw,y+ch),radius=max(12,int(31*s)),shadow=max(4,int(18*s)))
        col=(MUTED,PURPLE)[k]
        round_rect(d,(x0+int(45*s),y+int(40*s),x0+int(265*s),y+int(95*s)),(236,241,250) if k==0 else (238,232,255),r=20)
        d.text((x0+int(60*s),y+int(52*s)),label,font=fitted(d,label,int(220*s),22*s,True),fill=col)
        for i,line in enumerate(wrap(d,name,int(710*s),int(52*s),2,True)):
            d.text((x0+int(48*s),y+int((137+i*65)*s)),line,font=font(50*s,True),fill=INK)
        d.rounded_rectangle((x0+int(50*s),y+int(278*s),x0+int((220 if k==0 else 590)*s),y+int(294*s)),radius=8,fill=(205,215,228) if k==0 else PURPLE)
    elif layout in ('quote','minimal'):
        names=['ERPNext','Twenty CRM','Chatwoot','Plane','Paperless-ngx']
        name=names[k] if k<len(names) else labels[k%3]
        x0=int((120+350*k)*s);y=int(550*s);cw=int(315*s);ch=int(245*s)
        d=shadow_rect(im,(x0,y,x0+cw,y+ch),radius=max(12,int(25*s)))
        icon(d,x0+int(72*s),y+int(71*s),int(33*s),(PURPLE,BLUE,TEAL)[k%3],k)
        d.text((x0+int(32*s),y+int(149*s)),name,font=fitted(d,name,int(275*s),28*s,True),fill=INK)
    else:
        x0=int((120+580*k)*s);y=int(555*s);cw=int(520*s);ch=int(275*s)
        d=shadow_rect(im,(x0,y,x0+cw,y+ch),radius=max(10,int(27*s)),shadow=max(3,int(14*s)))
        icon(d,x0+int(77*s),y+int(76*s),int(35*s),(PURPLE,BLUE,TEAL)[k],k)
        label=str(labels[k])
        d.text((x0+int(37*s),y+int(139*s)),label,font=fitted(d,label,int(440*s),37*s,True),fill=INK)
        d.rounded_rectangle((x0+int(39*s),y+int(226*s),x0+int((180+80*k)*s),y+int(236*s)),radius=5,fill=(PURPLE,BLUE,TEAL)[k])
    return im

def browser_layer(w,h,scene,screenshot):
    s=w/1920;im=layer_canvas(w,h)
    x0=int(930*s);y0=int(517*s);x1=int(1795*s);y1=int(885*s)
    d=shadow_rect(im,(x0,y0,x1,y1),radius=max(12,int(28*s)),shadow=max(4,int(15*s)))
    d.rounded_rectangle((x0+int(8*s),y0+int(8*s),x1-int(8*s),y0+int(62*s)),radius=max(6,int(18*s)),fill=(246,247,252))
    for i,c in enumerate(((255,111,126),(255,188,98),(76,209,157))):
        cx=x0+int((44+i*28)*s);cy=y0+int(36*s);rr=max(3,int(9*s))
        d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=c)
    d.text((x0+int(180*s),y0+int(24*s)),"GITHUB  /  CAPTURA REAL" if screenshot else "DEMONSTRAÇÃO DO FLUXO",font=font(17*s,True),fill=MUTED)
    inner=(x0+int(19*s),y0+int(77*s),x1-int(19*s),y1-int(18*s))
    if screenshot and Path(screenshot).is_file():
        with Image.open(screenshot) as source:
            picture=ImageOps.fit(source.convert('RGB'),(inner[2]-inner[0],inner[3]-inner[1]),centering=(.5,.18))
            im.paste(picture,inner[:2])
    else:
        d=ImageDraw.Draw(im)
        d.rounded_rectangle(inner,radius=max(4,int(8*s)),fill=(242,245,253))
        for k in range(4):
            y=inner[1]+int((43+56*k)*s)
            d.rounded_rectangle((inner[0]+int(34*s),y,inner[2]-int(220*s),y+int(17*s)),radius=8,fill=(206,218,239))
            d.rounded_rectangle((inner[2]-int(160*s),y,inner[2]-int(36*s),y+int(17*s)),radius=8,fill=(225,214,249))
    return im

def save_crop(im,path):
    bb=im.getbbox()
    if not bb:return None
    pad=8
    bb=(max(0,bb[0]-pad),max(0,bb[1]-pad),min(im.width,bb[2]+pad),min(im.height,bb[3]+pad))
    im.crop(bb).save(path)
    return (str(path),bb[0],bb[1])

def make_layers(scene,output,width,height,screenshot=None):
    output.mkdir(parents=True,exist_ok=True)
    bg=output/'background.png';background(width,height,bg)
    layout=scene.get('layout','flow')
    layers=[]
    for label,t,dy in [('eyebrow',.0,-44),('title',.14,90),('description',.42,52)]:
        path=output/f'{label}.png';result=save_crop(text_layer(width,height,label,scene),path)
        if result:layers.append((*result,t,dy))
    count=2 if layout=='split' else 5 if layout in ('minimal','quote') else 3
    for k in range(count):
        path=output/f'card{k}.png';result=save_crop(card_layer(width,height,scene,k),path)
        if result:layers.append((*result,.7+k*.56,155 if k%2==0 else -125))
    if layout=='browser':
        path=output/'browser.png';result=save_crop(browser_layer(width,height,scene,screenshot),path)
        if result:layers.append((*result,.88,260))
    return bg,layers

def render_light_scene(scene,dest,scratch,index,fps,frames,width,height,
                       screenshot=None,narration=None,tempo=1.0):
    """Compose independent moving layers at each frame; FFmpeg encodes once."""
    duration=frames/fps;folder=scratch/f'light_motion_{index:03d}'
    bg,descriptors=make_layers(scene,folder,width,height,screenshot)
    background_image=Image.open(bg).convert('RGBA')
    layers=[(Image.open(path).convert('RGBA'),x,y,start,delta)
            for path,x,y,start,delta in descriptors]
    command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}',
             '-r',str(fps),'-i','pipe:0']
    if narration:command+=['-i',str(narration)]
    else:command+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
    command+=['-filter_complex',f'[1:a]aresample=48000,atempo={tempo:.5f},apad,atrim=0:{duration:.6f}[a]',
              '-map','0:v','-map','[a]','-frames:v',str(frames),
              '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
              '-c:a','aac','-b:a','128k','-movflags','+faststart',str(dest)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for frame_index in range(frames):
            t=frame_index/fps; canvas=background_image.copy()
            for i,(im,x,y,start,delta) in enumerate(layers):
                if t<start:continue
                progress=max(0.,min(1.,(t-start)/.66))
                ease=1-(1-progress)**3
                alpha=min(1.,(t-start)/.42)
                if alpha<=0:continue
                px=round(x+delta*(1-ease)+5*math.sin(t*.83+i*1.4))
                py=round(y+24*(1-ease)+4*math.sin(t*1.13+i*1.7))
                if alpha<.99:
                    a=im.copy()
                    mask=im.getchannel('A').point(lambda n:int(n*alpha))
                    a.putalpha(mask)
                else:a=im
                canvas.alpha_composite(a,(px,py))
            process.stdin.write(canvas.convert('RGB').tobytes())
        process.stdin.close()
        error=process.stderr.read().decode('utf-8','replace')
        code=process.wait(timeout=900)
        if code:raise RuntimeError('Light motion FFmpeg: '+error[-2000:])
    except (Exception,KeyboardInterrupt):
        process.kill();process.wait()
        raise
    return {'layers':len(layers),'animated':len(layers),'duration':duration}
