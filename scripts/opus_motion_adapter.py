"""MoneyPrint: local MIT motion ports, based on vendored Opus Motion Library.

The 3 upstream TSX sources and MIT / third-party notices live in vendor/opus-motion.
The browser/Remotion implementation is NOT a core dependency (Remotion is not
OSI-open-source). These Pillow animations port the original choreography:
breaking-news-takeover, cause-effect-chain, board-camera. R$0, self-hosted.
All footage after 12s remains authentic ERPNext screenshots; no fake statistics.
"""
from __future__ import annotations

from functools import lru_cache
from math import sin, pi
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FPS=30
SIZE=(1920,1080)
NAVY=(13,21,34)
IVORY=(246,239,221)
INK=(37,45,57)
VIOLET=(111,91,165)
WHITE=(253,251,247)
BLUE=(80,151,189)
SAGE=(92,155,121)
AMBER=(233,171,74)
CORAL=(188,104,79)
MOTION_SEGMENTS=[
    {"id":"breaking-news-takeover","start":0,"end":3.3,
     "text":"O caos das planilhas","role":"editorial_alert"},
    {"id":"cause-effect-chain","start":3.3,"end":9.05,
     "text":"Dados separados → conferência manual → retrabalho → custo","role":"cause_explainer"},
    {"id":"board-camera","start":9.05,"end":12.0,
     "text":"Venda, estoque e financeiro conectados","role":"whiteboard_dolly"},
]

def smooth(x):
    x=max(0.0,min(1.0,float(x)))
    return x*x*(3-2*x)

def mix(a,b,k):
    return round(a+(b-a)*k)

def rgba_mix(a,b,k):
    return tuple(mix(x,y,k) for x,y in zip(a,b))

@lru_cache(maxsize=32)
def font(size=30,heavy=True):
    files=([
       "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if heavy else [
       "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
       "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    for f in files:
        if Path(f).is_file():return ImageFont.truetype(f,int(size))
    return ImageFont.load_default()

def get_motion_name(t):
    return next((segment["id"] for segment in MOTION_SEGMENTS
                 if segment["start"]<=t<segment["end"]),None)

def text(d,x,y,label,size=40,fill=WHITE,bold=True,anchor=None):
    d.text((round(x),round(y)),label,font=font(size,bold),fill=fill,anchor=anchor)

def rect(d,box,color,rad=0,outline=None,width=2):
    coords=tuple(round(v) for v in box)
    if rad:d.rounded_rectangle(coords,radius=rad,fill=color,outline=outline,width=width)
    else:d.rectangle(coords,fill=color,outline=outline,width=width)

def _hook(t):
    """Adapt Opus 'breaking-news-takeover': slam -> band -> headline -> ticker.

    Replaces a news bulletin with a clearly editorial warning, no fabricated
    real-world news and no LIVE or invented broadcaster.
    """
    im=Image.new("RGB",SIZE,NAVY); d=ImageDraw.Draw(im)
    for j in range(0,1920,36):
        d.polygon([(j,0),(j+12,0),(max(0,j-260),1080),(max(0,j-272),1080)],
                  fill=(17,26,42))
    slam=smooth(t/.42)
    collapse=smooth((t-0.70)/.57)
    accent=rgba_mix(VIOLET,(110,68,160),.5+.25*sin(t*3))
    panelheight=mix(1080,160,collapse)
    left=mix(-1920,0,slam)
    rect(d,(left,0,1920,panelheight),accent)
    if t<1.32:
        scale=1+.06*(1-smooth((t-.24)/.52))
        f=int(184*scale*(1-.63*collapse))
        text(d,mix(460,75,collapse),mix(386,52,collapse),
             "ATENÇÃO",f,WHITE)
    else:
        text(d,87,38,"ATENÇÃO",68,WHITE)
    if t>1.12:
        progress=smooth((t-1.13)/.38)
        rect(d,(92,258,108,660),rgba_mix(NAVY,AMBER,progress))
        fg=rgba_mix(NAVY,WHITE,progress)
        text(d,144,270,"O CAOS DAS",125,fg)
        text(d,144,414,"PLANILHAS",148,fg)
        text(d,148,611,"Informações desencontradas",43,
             rgba_mix(NAVY,(203,215,229),progress),False)
    if t>2.05:
        k=smooth((t-2.05)/.25)
        rect(d,(0,940,1920,1080),(241,236,224))
        rect(d,(0,940,mix(0,215,k),1080),VIOLET)
        text(d,30,968,"GESTÃO",40,WHITE)
        subtitle="ESTOQUE    •    VENDAS    •    FINANCEIRO"
        text(d,300,969,subtitle,41,INK)
    return im

def _chain(t):
    """Adapt 'cause-effect-chain': serpentine cards, progressive glowing arrow."""
    u=t-3.3
    im=Image.new("RGB",SIZE,NAVY); d=ImageDraw.Draw(im)
    # Original chain concept: each outcome becomes the cause of the next.
    text(d,118,99,"QUANDO OS DADOS NÃO CONVERSAM",64,IVORY)
    text(d,121,189,"Uma pequena falha provoca outras.",34,(166,183,204),False)
    labels=[("ARQUIVOS","SEPARADOS"),("CONFERÊNCIA","MANUAL"),
            ("RETRABALHO","CONSTANTE"),("CUSTO","MAIOR")]
    colors=[BLUE,VIOLET,AMBER,CORAL]
    points=[(114,340),(575,340),(1036,340),(1497,340)]
    # Long connector baseline behind boxes, with moving light pulse.
    for i in range(3):
        x1=points[i][0]+327; x2=points[i+1][0]-22; y=592
        d.line((x1,y,x2,y),fill=(64,77,96),width=10)
        alpha=smooth((u-i*1.10-1.00)/.56)
        if alpha>0:
            xlast=mix(x1,x2,alpha)
            d.line((x1,y,xlast,y),fill=colors[i+1],width=11)
            if alpha<1:
                d.ellipse((xlast-16,y-16,xlast+16,y+16),fill=WHITE)
            if alpha>=.82:
                d.polygon([(x2,y-20),(x2+22,y),(x2,y+20)],fill=colors[i+1])
    for i,((a,b),(x,y),color) in enumerate(zip(labels,points,colors)):
        start=.08+i*1.10
        phase=smooth((u-start)/.43)
        if phase==0:continue
        cy=y+round((1-phase)*88)
        glow=rgba_mix((27,35,50),color,.26+phase*.20)
        d.rounded_rectangle((x+3,cy+8,x+329,cy+390),radius=36,fill=(30,40,56))
        rect(d,(x,cy,x+322,cy+370),rgba_mix((24,33,49),(238,234,223),phase),32)
        rect(d,(x,cy,x+322,cy+18),color,8)
        rect(d,(x+28,cy+36,x+89,cy+99),color,18)
        text(d,x+46,cy+45,str(i+1),40,WHITE)
        text(d,x+28,cy+155,a,33,INK)
        text(d,x+28,cy+207,b,34,INK)
        d.line((x+28,cy+289,x+284,cy+289),fill=color,width=9)
        d.line((x+28,cy+314,x+182,cy+314),fill=(181,186,190),width=5)
        if i==3 and u>4.25:
            r=80+65*smooth((u-4.25)/.7)
            d.ellipse((x+161-r,cy+185-r,x+161+r,cy+185+r),
                      outline=CORAL,width=6)
    if u>4.8:
        p=smooth((u-4.80)/.60)
        text(d,674,893,"O retrabalho custa caro.",55,rgba_mix(NAVY,IVORY,p))
    return im

@lru_cache(maxsize=2)
def _board_image():
    """Create an original editable whiteboard, animated by an Opus dolly path."""
    w,h=4500,2600
    img=Image.new("RGB",(w,h),(210,203,193)); d=ImageDraw.Draw(img)
    d.rounded_rectangle((360,260,4170,2300),radius=62,fill=(155,154,148))
    d.rounded_rectangle((405,300,4120,2260),radius=28,fill=IVORY,
                         outline=(118,120,124),width=20)
    text(d,780,400,"UM PROCESSO, TRÊS ÁREAS CONECTADAS",105,INK)
    zones=[(560,"VENDAS",BLUE,"bars"),(1790,"ESTOQUE",SAGE,"shelves"),
           (3020,"FINANCEIRO",VIOLET,"finance")]
    for x,title,color,kind in zones:
        y=745
        d.rounded_rectangle((x,y,x+995,y+1240),radius=45,fill=WHITE,
                             outline=(214,204,186),width=8)
        d.rounded_rectangle((x+26,y+25,x+969,y+150),radius=22,fill=color)
        text(d,x+92,y+47,title,65,WHITE)
        # Each zone uses the hand-drawn doodle vocabulary of board-camera:
        # bars/cycle/gear/wave rather than generic static flat labels.
        if kind=="bars":
            d.line((x+150,y+890,x+820,y+890),fill=INK,width=14)
            d.line((x+150,y+350,x+150,y+890),fill=INK,width=14)
            for k,ht in enumerate([160,295,425,370]):
                box=(x+220+k*141,y+880-ht,x+306+k*141,y+880)
                rect(d,box,color,18)
            text(d,x+155,y+1005,"PEDIDOS",61,INK)
        elif kind=="shelves":
            for j in range(3):
                yy=y+405+j*180
                d.line((x+140,yy+135,x+845,yy+135),fill=INK,width=16)
                for k in range(3):
                    rect(d,(x+180+k*215,yy+20,x+340+k*215,yy+128),
                         rgba_mix(SAGE,(217,236,217),.35+.1*k),18)
            text(d,x+168,y+1050,"PRODUTOS",58,INK)
        else:
            d.line((x+125,y+906,x+850,y+906),fill=INK,width=13)
            pairs=[(x+150,y+770),(x+300,y+665),(x+440,y+730),(x+610,y+475),(x+806,y+395)]
            d.line(pairs,fill=color,width=24,joint="curve")
            for px,py in pairs:d.ellipse((px-19,py-19,px+19,py+19),fill=color)
            text(d,x+162,y+1031,"RESULTADOS",57,INK)
    for x1,x2 in [(1555,1790),(2785,3020)]:
        y=1440
        d.line((x1+12,y,x2-45,y),fill=VIOLET,width=32)
        d.polygon([(x2-55,y-34),(x2-2,y),(x2-55,y+34)],fill=VIOLET)
    # Visible board tray in the closing pullback, as the reference motion.
    rect(d,(1620,2253,2900,2292),(139,143,146),10)
    for i,color in enumerate((VIOLET,BLUE,SAGE,AMBER)):
        rect(d,(2080+i*100,2270,2156+i*100,2295),color,8)
    return img

def _board(t):
    """Adapt 'board-camera': kinetic pan across original illustrated regions."""
    u=t-9.05
    base=_board_image()
    # Two short dollies, then a wide pullback revealing the whole board.
    if u<.80:
        z=1.27; cx=mix(1110,2000,smooth(u/.80))
    elif u<1.65:
        z=1.27; cx=mix(2000,3460,smooth((u-.8)/.85))
    else:
        p=smooth((u-1.65)/1.20)
        z=1.27+(.49-1.27)*p
        cx=mix(3460,2260,p)
    cy=mix(1260,1280,smooth((u-1.65)/1.20))
    sw=1920/z;sh=1080/z
    # crop, resize, then subtle film matte: no artificial black fill.
    bb=(round(cx-sw/2),round(cy-sh/2),round(cx+sw/2),round(cy+sh/2))
    image=base.crop(bb)
    return image.resize(SIZE,Image.Resampling.BICUBIC)

def motion_frame(t,width=1920,height=1080):
    motion=get_motion_name(t)
    if motion=="breaking-news-takeover":
        im=_hook(t)
    elif motion=="cause-effect-chain":
        im=_chain(t)
    elif motion=="board-camera":
        im=_board(t)
    else:
        raise ValueError("Não usar os motions sobre a demonstração real")
    if (width,height)!=SIZE:
        im=im.resize((width,height),Image.Resampling.BICUBIC)
    return im
