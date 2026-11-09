"""Frame-staged editorial art for the self-hosted MoneyPrint Studio V3.

Each frame is original Pillow artwork. External screenshots, if shown, must be
real local files selected by the canonical scene renderer (not AI replicas).
The renderer switches artwork at three beats without slow white transitions.
"""
from __future__ import annotations
from pathlib import Path
import math
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

BG=(9,16,31)
WHITE=(238,245,255)
MUTED=(153,176,205)
ACCENT=(72,203,233)
PANEL=(18,32,57)
PANEL_2=(25,44,72)
OUTLINE=(66,96,132)


def _font(size:int,bold:bool=False):
    candidates = (["/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
                   "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else
                  ["/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for file in candidates:
        if Path(file).is_file():return ImageFont.truetype(file,size)
    return ImageFont.load_default(size=size)


def _wrap(draw,text,font,maxw,max_lines=4):
    lines=[]
    for paragraph in str(text).split('\n'):
        current=''
        for word in paragraph.split():
            attempt=(current+' '+word).strip()
            if current and draw.textlength(attempt,font=font)>maxw:
                lines.append(current);current=word
            else:current=attempt
        if current:lines.append(current)
    return lines[:max_lines]


def _text(draw,xy,text,font,color=WHITE,width=0,lines=4,leading=1.22):
    if not width:
        draw.text(xy,str(text),font=font,fill=color)
        return
    y=xy[1]
    for line in _wrap(draw,text,font,width,lines):
        draw.text((xy[0],int(y)),line,font=font,fill=color)
        y+=font.size*leading


def _panel(draw,bbox,fill=PANEL,outline=OUTLINE,radius=24,width=2):
    draw.rounded_rectangle(tuple(map(int,bbox)),radius=radius,fill=fill,outline=outline,width=width)


def _background(w,h,stage,scene):
    # Rich but restrained original design: no white flashes and no commercial images.
    im=Image.new('RGB',(w,h),BG)
    d=ImageDraw.Draw(im)
    for y in range(h):
        p=y/max(1,h-1)
        d.line((0,y,w,y),fill=(int(9+7*p),int(16+12*p),int(31+21*p)))
    S=w/1920
    d.ellipse((int(w*.59),int(-h*.69),int(w*1.31),int(h*.39)),fill=(16+stage*2,40,68))
    d.ellipse((int(-w*.36),int(h*.59),int(w*.12),int(h*1.4)),fill=(12,34,53))
    # Delicate dot-matrix depth avoids huge blank background areas.
    for r in range(8):
        for c in range(15):
            x=int(w*.42+c*w*.038+(r%2)*w*.012)
            y=int(h*.12+r*h*.075)
            d.ellipse((x,y,x+max(1,int(2*S)),y+max(1,int(2*S))),fill=(30,61,88))
    # Left editorial rail.
    rail=max(2,int(6*S))
    d.rounded_rectangle((int(w*.055),int(h*.102),int(w*.055)+int(95*S),int(h*.102)+rail),radius=rail//2,fill=ACCENT)
    label=scene.get('eyebrow') or 'OPEN SOURCE  /  MONEYPRINT'
    d.text((int(w*.055),int(h*.142)),label[:75].upper(),font=_font(max(12,int(23*S)),True),fill=ACCENT)
    d.text((int(w*.055),int(h*.948)), 'ARTISYS  /  MONEYPRINT',font=_font(max(10,int(19*S))),fill=(110,139,172))
    return im,d


def _title(draw,scene,w,h,size=64,left=.055,top=.235,maxwidth=.80,lines=3):
    f=_font(max(19,int(size*w/1920)),True)
    _text(draw,(int(w*left),int(h*top)),scene['title'],f,WHITE,int(w*maxwidth),lines,1.18)


def _bullet_cards(draw,scene,stage,w,h,*,left=.55,top=.31,card_w=.39):
    S=w/1920
    bullets=scene.get('bullets') or ["Mais organização", "Menos retrabalho", "Controle de processos"]
    for i,label in enumerate(bullets[:3]):
        x,y=int(w*left),int(h*(top+i*.16))
        cw,ch=int(w*card_w),int(h*.125)
        lit=i<=stage
        _panel(draw,(x,y,x+cw,y+ch),fill=PANEL_2 if lit else (16,27,46),outline=ACCENT if lit else OUTLINE,radius=max(10,int(18*S)),width=max(2,int(2*S)))
        b=int(24*S)
        draw.rounded_rectangle((x+b,y+int(ch*.35),x+b+int(54*S),y+int(ch*.35)+int(33*S)),radius=8,fill=ACCENT if lit else OUTLINE)
        draw.text((x+b+int(17*S),y+int(ch*.35)+int(4*S)),str(i+1),font=_font(max(13,int(17*S)),True),fill=(8,25,43))
        _text(draw,(x+int(100*S),y+int(ch*.3)),label,_font(max(17,int(30*S)),True),WHITE if lit else MUTED,int(cw*.74),2,1.2)


def _flow(draw,scene,stage,w,h):
    S=w/1920
    _title(draw,scene,w,h,size=73,top=.23,maxwidth=.86,lines=2)
    steps=scene.get('flow_steps') or ["ENTRADA", "PROCESSAMENTO", "RESULTADO"]
    start_x=w*.075
    gap=w*.05
    cw=(w*.85-2*gap)/3
    y0=int(h*.52)
    cy=int(h*.69)
    for i,step in enumerate(steps):
        x=int(start_x+i*(cw+gap))
        x2=int(x+cw)
        active=i<=stage
        _panel(draw,(x,y0,x2,int(h*.84)),fill=(24,57,82) if active else (18,32,53),outline=ACCENT if active else OUTLINE,radius=max(11,int(21*S)),width=max(2,int(2*S)))
        tagfont=_font(max(15,int(24*S)),True)
        draw.rounded_rectangle((x+int(26*S),y0+int(32*S),x+int(92*S),y0+int(72*S)),radius=int(14*S),fill=ACCENT if active else (41,73,96))
        _text(draw,(x+int(45*S),y0+int(37*S)),f'{i+1:02d}',tagfont,(8,31,49) if active else MUTED)
        _text(draw,(x+int(25*S),y0+int(118*S)),step,_font(max(19,int(38*S)),True),WHITE if active else MUTED,cw-int(45*S),2)
        if i<2:
            start=int(x2+10*S);end=int(x2+gap-15*S)
            active_line=stage>i
            draw.line((start,cy,end,cy),fill=ACCENT if active_line else OUTLINE,width=max(2,int(5*S)))
            draw.polygon([(end,cy),(end-int(13*S),cy-int(11*S)),(end-int(13*S),cy+int(11*S))],fill=ACCENT if active_line else OUTLINE)
    tip=(scene.get('caption') or '').strip()
    if tip:
        _text(draw,(int(w*.075),int(h*.885)),tip,_font(max(13,int(23*S))),MUTED,int(w*.82),1)


def _browser(image,draw,scene,stage,w,h,asset):
    S=w/1920
    _title(draw,scene,w,h,size=62,top=.27,maxwidth=.39,lines=3)
    bullets=scene.get('bullets') or ["Código público", "Comunidade ativa", "Instalação própria"]
    for i,label in enumerate(bullets[:3]):
        y=int(h*(.53+i*.087))
        _panel(draw,(int(w*.055),y,int(w*.415),y+int(h*.066)),fill=PANEL_2 if i<=stage else PANEL,outline=ACCENT if i==stage else OUTLINE,radius=max(7,int(13*S)),width=2)
        _text(draw,(int(w*.078),y+int(14*S)),label,_font(max(17,int(25*S)),True),WHITE if i<=stage else MUTED,int(w*.31),1)
    bx,by,bw,bh=int(w*.465),int(h*.23),int(w*.485),int(h*.595)
    _panel(draw,(bx-7,by-7,bx+bw+7,by+bh+7),fill=(30,53,77),outline=(71,137,172),radius=max(12,int(22*S)),width=max(2,int(2*S)))
    draw.rounded_rectangle((bx,by,bx+bw,by+int(54*S)),radius=max(8,int(17*S)),fill=(26,40,62))
    for i,c in enumerate(((220,114,115),(223,183,92),(112,193,148))):
        px=bx+int((25+i*28)*S);py=by+int(18*S)
        draw.ellipse((px,py,px+int(12*S),py+int(12*S)),fill=c)
    rep=scene.get('repo_url') or 'github.com'
    _text(draw,(bx+int(145*S),by+int(16*S)),rep.replace('https://','')[:49],_font(max(13,int(20*S))),MUTED,int(bw*.8),1)
    inset=(bx+int(15*S),by+int(61*S),bx+bw-int(15*S),by+bh-int(17*S))
    if asset and Path(asset).is_file():
        with Image.open(asset) as source:
            sample=ImageOps.fit(source.convert('RGB'),(inset[2]-inset[0],inset[3]-inset[1]),Image.Resampling.LANCZOS,centering=(.5,.22))
            image.paste(sample,(inset[0],inset[1]))
    else:
        draw.rounded_rectangle(inset,radius=11,fill=(20,34,56))
        _text(draw,(inset[0]+int(45*S),inset[1]+int(160*S)),"Captura do GitHub indisponível",_font(max(19,int(32*S))),MUTED,int(bw*.85),2)
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((bx-int(10*S),by+bh+int(28*S),bx+int(bw*.75),by+bh+int(37*S)),radius=4,fill=ACCENT)


def _hero(draw,scene,stage,w,h):
    S=w/1920
    f=_font(max(26,int(110*S)),True)
    title=scene['title']
    top=int(h*.28)
    for line in _wrap(draw,title,f,int(w*.9),3):
        draw.text((int(w*.055),top),line,font=f,fill=WHITE)
        top+=int(f.size*1.19)
    chips=scene.get('bullets') or ['5 SISTEMAS', 'CÓDIGO ABERTO', 'SELF-HOSTED']
    width_used=0
    y=int(h*.74)
    for i,text in enumerate(chips[:3]):
        chipfont=_font(max(13,int(26*S)),True)
        tw=draw.textlength(text,font=chipfont)
        boxw=int(tw+70*S)
        x=int(w*.057+width_used)
        _panel(draw,(x,y,x+boxw,y+int(80*S)),fill=PANEL_2 if i<=stage else PANEL,outline=ACCENT if i<=stage else OUTLINE,radius=max(10,int(25*S)),width=2)
        _text(draw,(x+int(32*S),y+int(22*S)),text,chipfont,WHITE if i<=stage else MUTED)
        width_used+=boxw+int(26*S)


def _split(draw,scene,stage,w,h):
    _title(draw,scene,w,h,size=66,top=.29,maxwidth=.44,lines=4)
    _bullet_cards(draw,scene,stage,w,h,left=.55,top=.29,card_w=.39)
    tip=scene.get('caption')
    if tip:
        S=w/1920
        _text(draw,(int(w*.055),int(h*.77)),tip,_font(max(15,int(25*S))),MUTED,int(w*.43),3)


def draw_slide(scene:dict,output:Path,width:int,height:int,asset:Path|None=None,*,stage:int=2):
    if stage not in (0,1,2):raise ValueError('Estágio fora dos limites')
    im,d=_background(width,height,stage,scene)
    layout=scene['layout']
    if layout=='flow':_flow(d,scene,stage,width,height)
    elif layout=='browser':_browser(im,d,scene,stage,width,height,asset)
    elif layout in ('split','minimal'):_split(d,scene,stage,width,height)
    else:_hero(d,scene,stage,width,height)
    output.parent.mkdir(parents=True,exist_ok=True)
    im.save(output,compress_level=4)
    return output