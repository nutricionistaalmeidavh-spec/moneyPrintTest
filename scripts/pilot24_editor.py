"""MoneyPrint Pilot24: edit-driven demonstration using exclusively open-source tools.

Uses two unmodified canonical scene texts, Piper pt-BR, authentic GitHub +
README screenshots, Pillow motion scenes and FFmpeg. NO Talkcraft runtime,
generative image API, paid dependency or automatic publication.
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FPS=30
DURATION=24
INK=(37,49,67)
PAPER=(246,238,219)
VIOLET=(121,100,188)
BLUE=(126,169,189)
SAGE=(121,163,144)
RUST=(181,98,74)
WHITE=(255,251,244)
BEATS=[
    (0,3.30,"planilhas"),
    (3.30,6.35,"dados"),
    (6.35,9.05,"retrabalho"),
    (9.05,12.0,"integracao"),
    (12.0,15.66,"github"),
    (15.66,18.0,"interface"),
    (18.0,20.7,"modulos"),
    (20.7,24.0,"implantacao"),
]
ANCHORS=[
    {"word":"planilha","at":3.3,"method":"interpolated_between_measured_pt"},
    {"word":"vendas","at":15.66,"method":"measured_whisper_pt"},
    {"word":"estoque","at":16.8,"method":"measured_whisper_pt"},
]
CAPTURE_URL="https://github.com/frappe/erpnext"

def ease(t):
    t=max(0,min(1,t))
    return 1-(1-t)**3

def validate_plan():
    if len(BEATS)!=8 or BEATS[0][0]!=0 or BEATS[-1][1]!=DURATION:
        raise ValueError("Plano precisa ter oito batidas dentro de 24 s")
    for a,b in zip(BEATS,BEATS[1:]):
        if a[1]!=b[0] or a[1]-a[0]>=4:raise ValueError("Lacuna ou batida longa")
    return True

@lru_cache(maxsize=48)
def font(size,heavy=True):
    for n in ([f"/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if heavy else
              [f"/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]):
        if Path(n).is_file():return ImageFont.truetype(n,max(10,size))
    raise RuntimeError("Necessário instalar fonts-lato / fonts-dejavu-core")

class Stage:
    def __init__(self,w,h,t):
        self.w,self.h,self.t=w,h,t
        self.s=w/1920
        self.im=Image.new("RGB",(w,h),PAPER)
        self.d=ImageDraw.Draw(self.im)
        for y in range(80,h,max(12,round(38*self.s))):
            self.d.line((0,y,w,y),fill=(243,236,225))
    def p(self,x):return round(x*self.s)
    def box(self,x,y,w,h,color=WHITE,outline=None,r=24):
        self.d.rounded_rectangle((self.p(x),self.p(y),self.p(x+w),self.p(y+h)),
            radius=max(1,self.p(r)),fill=color,outline=outline,width=max(1,self.p(2)))
    def tx(self,x,y,msg,size=32,color=INK,heavy=True):
        self.d.text((self.p(x),self.p(y)),msg,font=font(self.p(size),heavy),fill=color)
    def line(self,x,y,xx,yy,color=VIOLET,width=7):
        self.d.line((self.p(x),self.p(y),self.p(xx),self.p(yy)),
            fill=color,width=max(1,self.p(width)))
    def circ(self,x,y,r,color):
        self.d.ellipse((self.p(x-r),self.p(y-r),self.p(x+r),self.p(y+r)),fill=color)
    def screenshot(self,source,rect,zoom=1,contain=False):
        x,y,w,h=rect; width,height=self.p(w),self.p(h)
        scaling=(min if contain else max)(width/source.width,height/source.height)*zoom
        rw,rh=round(source.width*scaling),round(source.height*scaling)
        frame=source.resize((max(1,rw),max(1,rh)),Image.Resampling.BICUBIC)
        if contain:
            panel=Image.new("RGB",(width,height),(27,33,43))
            panel.paste(frame,((width-rw)//2,(height-rh)//2))
        else:
            ox=(rw-width)//2;oy=(rh-height)//2
            panel=frame.crop((ox,oy,ox+width,oy+height))
        self.im.paste(panel,(self.p(x),self.p(y)))
    def browser(self,source,rect,zoom=1,caption="",contain=False):
        x,y,w,h=rect
        self.box(x-12,y-48,w+24,h+60,WHITE,r=20)
        for i,color in enumerate((RUST,(216,183,112),SAGE)):
            self.circ(x+22+i*26,y-23,7,color)
        self.tx(x+104,y-44,caption[:80],18,(106,102,103))
        self.screenshot(source,rect,zoom=zoom,contain=contain)
    def badge(self,x,y,title,color=VIOLET):
        self.box(x,y,300,75,WHITE,r=18)
        self.box(x+13,y+14,14,46,color,r=4)
        self.tx(x+48,y+17,title,27,INK)

def frame_at(t,repo,app,w=1920,h=1080):
    i=next((k for k,(a,b,_) in enumerate(BEATS) if a<=t<b),7)
    a,b,_=BEATS[i]
    local=t-a
    s=Stage(w,h,t)
    if i==0:
        s.tx(100,147,"01 / O PROBLEMA",28,VIOLET)
        s.tx(106,233,"PLANILHAS",136,INK)
        s.tx(104,382,"PARA TUDO.",136,INK)
        s.tx(120,560,"Estoque, vendas e financeiro em arquivos separados.",31,INK,False)
        for k,(label,col) in enumerate((("ESTOQUE",SAGE),("VENDAS",BLUE),("FINANCEIRO",VIOLET))):
            v=ease((local-.18-k*.27)/.45)
            if v<=0:continue
            x=204+k*540;y=652+(1-v)*190
            s.box(x,y,394,256,WHITE,(215,207,197))
            s.box(x+20,y+20,348,55,col,r=9)
            s.tx(x+37,y+30,label,27,WHITE)
            for row in range(3):
                s.line(x+37,y+122+row*42,x+346,y+122+row*42,(219,216,213),2)
        s.tx(125,948,"MESMA EMPRESA  /  DADOS DESCONECTADOS",24,RUST)
    elif i==1:
        s.tx(112,140,"A DESORGANIZAÇÃO TEM UM CUSTO",28,VIOLET)
        s.tx(100,248,"DADOS QUE",128,INK)
        s.tx(100,405,"NÃO CONVERSAM.",123,RUST)
        for k,(name,col) in enumerate((("ESTOQUE",SAGE),("VENDAS",BLUE),("FINANCEIRO",VIOLET))):
            v=ease((local-k*.30)/.44)
            if v<=0:continue
            x=170+k*586; y=656+(1-v)*66
            s.box(x,y,424,230,WHITE,(216,208,199),r=25)
            s.circ(x+70,y+77,29,col)
            s.tx(x+123,y+53,name,30)
            s.tx(x+45,y+145,"DADO ISOLADO",26,RUST)
            if k<2 and local>1.2+k*.29:
                s.line(x+430,y+105,x+550,y+105,RUST,5)
                s.tx(x+465,y+70,"×",48,RUST)
    elif i==2:
        s.tx(100,150,"FALTA DE INTEGRAÇÃO",30,RUST)
        s.tx(100,278,"RE",196,RUST)
        s.tx(109,486,"TRABALHO",203,INK)
        for k,name in enumerate(("CONFERIR PEDIDO","REVISAR PLANILHA","FECHAR CONTAS")):
            v=ease((local-.20-k*.33)/.47)
            if v<=0:continue
            x=150+k*550;y=783+(1-v)*80
            s.box(x,y,498,110,WHITE,(214,207,198),r=20)
            s.circ(x+58,y+54,26,RUST)
            s.tx(x+53,y+29,"!",40,WHITE)
            s.tx(x+105,y+37,name,27)
        s.tx(130,950,"O TRABALHO MANUAL TAMBÉM CUSTA TEMPO.",25,RUST)
    elif i==3:
        s.tx(108,145,"A VIRADA",29,VIOLET)
        s.tx(100,246,"E SE TUDO CONVERSASSE?",94,INK)
        s.tx(111,385,"Dados conectados, sem trocar de planilha.",34,INK,False)
        for k,(label,col) in enumerate((("VENDA",BLUE),("ESTOQUE",SAGE),("FINANCEIRO",VIOLET))):
            v=ease((local-.20-k*.39)/.50)
            if v<=0:continue
            x=184+k*573;y=559+(1-v)*70
            s.box(x,y,390,243,WHITE,(214,206,198),r=30)
            s.box(x+28,y+30,72,70,col,r=21)
            s.tx(x+128,y+39,label,32)
            s.tx(x+40,y+156,"INFORMAÇÃO ÚNICA",22,INK,False)
            if k<2 and local>1.1+k*.38:
                s.line(x+401,y+120,x+559,y+120,VIOLET,9)
                s.tx(x+521,y+80,">",44,VIOLET)
        s.badge(813,881,"FLUXO INTEGRADO",SAGE)
    elif i==4:
        s.im.paste((24,31,43),(0,0,w,h))
        s.browser(repo,(535,98,1240,893),1+.09*ease(local/(b-a)),
                  "FONTE: CAPTURA REAL · GITHUB / FRAPPE / ERPNEXT")
        s.box(62,181,518,670,PAPER,r=0)
        s.tx(99,235,"EXEMPLO REAL",30,VIOLET)
        s.tx(96,335,"ERP",110)
        s.tx(96,460,"NEXT",110)
        s.tx(104,628,"CÓDIGO",36)
        s.tx(104,682,"ABERTO.",36)
        s.tx(104,789,"REPOSITÓRIO VERIFICÁVEL",20,INK)
    elif i==5:
        s.im.paste((24,31,43),(0,0,w,h))
        s.browser(app,(68,106,1780,893),1+.12*ease(local/(b-a)),
                  "INTERFACE AUTÊNTICA · SCREENSHOT DO README",True)
        s.box(115,758,680,148,PAPER,r=24)
        s.tx(146,783,"TÁ NA APLICAÇÃO.",48)
        s.tx(146,852,"NÃO É MOCKUP.",30,VIOLET)
    elif i==6:
        s.tx(110,136,"UMA PLATAFORMA, VÁRIAS FUNÇÕES",28,VIOLET)
        s.tx(106,260,"TUDO NO MESMO",103)
        s.tx(110,388,"ECOSSISTEMA.",103,VIOLET)
        for k,(name,col) in enumerate((("VENDAS",BLUE),("COMPRAS",VIOLET),("ESTOQUE",SAGE),("CONTÁBIL",RUST))):
            v=ease((local-k*.25)/.40)
            if v<=0:continue
            x=158+k*452;y=625+(1-v)*70
            s.box(x,y,378,240,WHITE,(215,208,199))
            s.circ(x+92,y+92,42,col)
            s.tx(x+39,y+173,name,32)
            if k<3 and local>.9+k*.27:s.line(x+391,y+113,x+442,y+113,VIOLET,8)
        s.tx(138,941,"FLUXO DIDÁTICO, NÃO UMA SIMULAÇÃO DE INTERFACE.",23,INK)
    else:
        s.im.paste((24,31,43),(0,0,w,h))
        s.browser(app,(630,95,1180,905),1+.07*ease(local/(b-a)),
                  "ERPNext · CAPTURA AUTÊNTICA",True)
        s.box(58,145,696,743,PAPER,r=0)
        s.tx(98,205,"ALERTA",29,VIOLET)
        s.tx(99,305,"NÃO É",92)
        s.tx(99,411,"INSTALAR",86)
        s.tx(99,515,"E PRONTO.",85,RUST)
        for k,(label,col) in enumerate((("IMPLANTAÇÃO",VIOLET),("CONFIGURAÇÃO",BLUE))):
            if ease((local-.4-k*.48)/.4)>0:s.badge(99,699+k*91,label,col)
    dark=i in (4,5,7)
    fg=(224,219,210) if dark else (107,104,104)
    track=(115,119,125) if dark else (222,214,201)
    s.box(90,1044,1740,7,track,r=3)
    s.box(90,1044,1740*(t/DURATION),7,SAGE if dark else VIOLET,r=3)
    s.tx(94,1008,"MONEYPRINT  /  PILOTO 24s",20,fg)
    s.tx(1658,1008,f"{t:04.1f}s / 24s",20,fg)
    return s.im

def ffprobe_duration(path):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())

def create_voice(project,model,output):
    from scripts.studio_render import build_plan
    plan=build_plan(project)
    selected=plan["scenes"][2:4]
    if [s["id"] for s in selected]!=["scene-003","scene-004"]:
        raise ValueError("Projeto canônico não corresponde às duas cenas selecionadas")
    clips=[]
    for k,scene in enumerate(selected,1):
        raw=output/f"raw_{k}.wav"
        subprocess.run(["piper","--model",str(model),"--output_file",str(raw)],
                       input=scene["text"],text=True,capture_output=True,check=True)
        source_dur=ffprobe_duration(raw)
        rate=max(.8,source_dur/11.88)
        if rate>2.0:raise ValueError("Texto excede 12 segundos, rever roteiro")
        clip=output/f"voice_{k}.wav"
        subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),
            "-af",f"atempo={rate:.6f},apad,atrim=0:12,aresample=48000",
            "-ar","48000","-ac","1","-c:a","pcm_s16le",str(clip)],check=True)
        clips.append(clip)
    return clips

def capture_proofs(output):
    from scripts.repo_stills import capture_repo_stills
    records=capture_repo_stills([CAPTURE_URL],output)
    if not records or not records[0]:raise RuntimeError("GitHub inacessível")
    sources=[Path(path) for path in records[0]]
    top=next((x for x in sources if x.name=="top.png"),None)
    app=next((x for x in sources if x.name=="app_real.png"),None)
    if not top or not app:
        raise RuntimeError("Não há prova de app publicada no README; não fabricar UI")
    return top,app

def render(project,output,model,width=1920,height=1080):
    validate_plan()
    from scripts.studio_render import build_plan
    plan=build_plan(project)
    if plan["fps"]!=FPS or [s["id"] for s in plan["scenes"][2:4]]!=["scene-003","scene-004"]:
        raise ValueError("Projeto inesperado")
    output.mkdir(parents=True,exist_ok=True)
    clips=create_voice(project,model,output)
    capture_root=output/"capture"
    repo_file,app_file=capture_proofs(capture_root)
    repo=Image.open(repo_file).convert("RGB")
    app=Image.open(app_file).convert("RGB")
    audio=output/"narracao_piper.wav"
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(clips[0]),"-i",str(clips[1]),
        "-filter_complex","[0:a][1:a]concat=n=2:v=0:a=1[a]",
        "-map","[a]","-ar","48000","-c:a","pcm_s16le",str(audio)],check=True)
    video=output/"moneyprint_piloto_24s.mp4"
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pixel_format","rgb24",
         "-video_size",f"{width}x{height}","-framerate",str(FPS),"-i","pipe:0",
         "-i",str(audio),"-map","0:v","-map","1:a","-t",str(DURATION),
         "-c:v","libx264","-crf","19","-preset","veryfast","-pix_fmt","yuv420p",
         "-c:a","aac","-b:a","160k","-movflags","+faststart",str(video)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
        try:
            for frame in range(FPS*DURATION):
                image=frame_at(frame/FPS,repo,app,width,height)
                proc.stdin.write(image.tobytes())
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError("Falha ao produzir MP4")
        finally:
            if proc.poll() is None:proc.kill()
    if abs(ffprobe_duration(video)-DURATION)>.1:
        raise RuntimeError("A duração final diverge da timeline")
    sheet=Image.new("RGB",(1280,1440),PAPER)
    for i,(start,end,_) in enumerate(BEATS):
        shot=frame_at((start+end)/2,repo,app,640,360)
        sheet.paste(shot,((i%2)*640,(i//2)*360))
    sheet.save(output/"qa_8_cortes.jpg",quality=88)
    report={"engine":"moneyprint_pilot24_ffmpeg_pillow","fps":FPS,
        "duration":DURATION,"frames":FPS*DURATION,"beat_count":len(BEATS),
        "timeline":BEATS,"anchors":ANCHORS,
        "note":"Piper regenerado: os timestamps da execução anterior são referência, não nova medição ASR",
        "github_source":CAPTURE_URL,"real_app_capture":str(app_file),
        "talkcraft_dependency":False,"paid_dependencies":[],
        "autopublish":False,"human_approval_required":True}
    (output/"pilot24_diagnostico.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return video

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--project",type=Path,required=True)
    parser.add_argument("--voice-model",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    project=json.loads(args.project.read_text(encoding="utf-8"))
    result=render(project,args.out,args.voice_model)
    print("PILOTO 24s GERADO:",result)

if __name__=="__main__":main()
